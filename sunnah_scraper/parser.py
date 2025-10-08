"""HTML parsing helpers for Sunnah.com Riyad as-Salihin pages."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin

from selectolax.parser import HTMLParser, Node

from .models import BookIndexEntry, GradingEntry, HadithRecord, HadithText, ReferenceEntry

LOGGER = logging.getLogger(__name__)


@dataclass
class ChapterContext:
    identifier: Optional[str]
    number_en: Optional[str]
    number_ar: Optional[str]
    title_en: Optional[str]
    title_ar: Optional[str]


def text_content(node: Optional[Node]) -> Optional[str]:
    if node is None:
        return None
    text = node.text(separator=" ", strip=True)
    if not text:
        return None
    return normalize_text(text)


def normalize_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = " ".join(value.split())
    if not normalized:
        return None
    return normalized


def parse_collection_index(
    html: str,
    collection_slug: str,
    collection_url: str,
) -> tuple[Optional[str], list[BookIndexEntry]]:
    tree = HTMLParser(html)
    collection_name = text_content(tree.css_first(".collection_info .colindextitle"))
    if collection_name:
        collection_name = normalize_text(collection_name)
    anchors = tree.css("a")
    entries: list[BookIndexEntry] = []
    seen: set[str] = set()
    for anchor in anchors:
        href = anchor.attributes.get("href")
        if not href:
            continue
        if not href.startswith(f"/{collection_slug}/"):
            continue
        parts = href.strip("/").split("/")
        if len(parts) != 2:
            continue
        _, book_id = parts
        if book_id in seen:
            continue
        title_en = text_content(anchor)
        if not title_en:
            continue
        title_en = normalize_text(title_en)
        url = urljoin(collection_url, href)
        entries.append(
            BookIndexEntry(
                book_id=book_id,
                source_url=url,
                book_number=None,
                book_title_en=title_en,
                book_title_ar=None,
                hadith_count=0,
            )
        )
        seen.add(book_id)
    if not entries:
        LOGGER.warning("No book links discovered for collection %s", collection_slug)
    return collection_name, entries


def parse_chapter_node(node: Node, *, fallback_anchor: Optional[str] = None) -> ChapterContext:
    identifier = fallback_anchor
    anchor = node.css_first("a[name]")
    if anchor is not None:
        identifier = anchor.attributes.get("name") or identifier
    if identifier is None:
        previous = node.prev
        while previous is not None:
            if previous.tag == "a" and "name" in previous.attributes:
                identifier = previous.attributes.get("name")
                break
            previous = previous.prev

    number_en = text_content(node.css_first(".echapno"))
    number_ar = text_content(node.css_first(".achapno"))

    title_en = text_content(node.css_first(".englishchapter"))
    if title_en and title_en.lower().startswith("chapter:"):
        title_en = title_en.split(":", 1)[1].strip() or title_en
        title_en = normalize_text(title_en)
    if not title_en:
        for candidate in [
            node.css_first(".english"),
            node.css_first(".chapter-title-english"),
            node.css_first(".english_chapter_name"),
            node.css_first(".chapter-title"),
        ]:
            title_en = text_content(candidate)
            if title_en:
                break

    title_ar = text_content(node.css_first(".arabicchapter"))
    if not title_ar:
        for candidate in [
            node.css_first(".arabic"),
            node.css_first(".chapter-title-arabic"),
            node.css_first(".arabic_chapter_name"),
            node.css_first("span[dir='rtl']"),
        ]:
            title_ar = text_content(candidate)
            if title_ar:
                break

    return ChapterContext(
        identifier=identifier,
        number_en=number_en,
        number_ar=number_ar,
        title_en=title_en,
        title_ar=title_ar,
    )


def parse_hadith_container(
    container: Node,
    *,
    collection_slug: str,
    collection_name: str,
    book_id: str,
    book_title_en: str,
    book_title_ar: Optional[str],
    chapter: ChapterContext,
    base_url: str,
) -> Optional[HadithRecord]:
    hadith_id = container.attributes.get("id")
    if hadith_id is None:
        anchor = container.css_first("a[name]")
        if anchor is not None:
            hadith_id = anchor.attributes.get("name")
    if hadith_id is None:
        LOGGER.debug("Skipping container without stable id")
        return None

    english_node = container.css_first(".english_hadith_full") or container.css_first(".english")
    arabic_node = container.css_first(".arabic_hadith_full") or container.css_first(".arabic")
    english_text = text_content(english_node)
    arabic_text = text_content(arabic_node)
    if not english_text or not arabic_text:
        LOGGER.debug("Hadith %s missing english/ar text; skipping", hadith_id)
        return None

    narrator = text_content(container.css_first(".hadith_narrated"))

    hadith_num_global = text_content(container.css_first(".hadith_number"))
    if not hadith_num_global:
        sticky = text_content(container.css_first(".hadith_reference_sticky"))
        if sticky:
            hadith_num_global = normalize_text(sticky)
    hadith_num_in_book = text_content(container.css_first(".hadith_reference .bookReference"))

    grading_entries: list[GradingEntry] = []
    for row in container.css(".hadith_grade, .hadith_rating"):
        scholar = text_content(row.css_first(".gradeby")) or text_content(row.css_first("strong"))
        grade = text_content(row.css_first(".grade"))
        note = text_content(row.css_first(".grader_comment"))
        if scholar or grade or note:
            grading_entries.append(GradingEntry(scholar=scholar or "Unknown", grade=grade, note=note))

    references: list[ReferenceEntry] = []
    for table in container.css("table.hadith_reference"):
        for row in table.css("tr"):
            cells = row.css("td")
            if len(cells) < 2:
                continue
            label = text_content(cells[0])
            value = text_content(cells[1])
            if value:
                value = value.lstrip(":").strip()
                value = normalize_text(value)
            if not label or not value:
                continue
            references.append(ReferenceEntry(label=label, value=value))
            lower_label = label.lower()
            if "in-book reference" in lower_label:
                hadith_num_in_book = hadith_num_in_book or value
            elif "reference" in lower_label and "in-book" not in lower_label:
                hadith_num_global = hadith_num_global or value

    topics = [text for text in (text_content(node) for node in container.css(".hadith_topics span")) if text]

    footnotes = [text for text in (text_content(node) for node in container.css(".footnote")) if text]

    source_url = f"{base_url}#{hadith_id}"

    return HadithRecord(
        collection_slug=collection_slug,
        collection_name=collection_name,
        book_id=book_id,
        book_title_en=book_title_en,
        book_title_ar=book_title_ar,
        chapter_id=chapter.identifier,
        chapter_number_en=chapter.number_en,
        chapter_number_ar=chapter.number_ar,
        chapter_title_en=chapter.title_en,
        chapter_title_ar=chapter.title_ar,
        hadith_id_site=hadith_id,
        hadith_num_global=hadith_num_global,
        hadith_num_in_book=hadith_num_in_book,
        texts=[
            HadithText(language="en", content=english_text),
            HadithText(language="ar", content=arabic_text),
        ],
        narrator=narrator,
        grading=grading_entries,
        references=references,
        topics=topics,
        footnotes=footnotes,
        source_url=source_url,
    )


def parse_book_page(
    html: str,
    *,
    collection_slug: str,
    collection_name: str,
    book_id: str,
    book_url: str,
    fallback_book_title_en: Optional[str] = None,
) -> tuple[str, Optional[str], Optional[str], list[HadithRecord]]:
    tree = HTMLParser(html)
    root = tree.body or tree

    book_title_en = None
    book_title_ar = None
    book_number = None

    book_info = root.css_first(".book_info .book_page_colindextitle")
    if book_info is not None:
        book_title_en = text_content(book_info.css_first(".book_page_english_name"))
        book_title_ar = text_content(book_info.css_first(".book_page_arabic_name"))
        book_number = text_content(book_info.css_first(".book_page_number"))

    if not book_title_en:
        crumbs = root.css_first(".crumbs")
        if crumbs is not None:
            crumb_text = text_content(crumbs)
            if crumb_text and "»" in crumb_text:
                parts = [part.strip() for part in crumb_text.split("»") if part.strip()]
                if parts:
                    book_title_en = normalize_text(parts[-1])

    if not book_title_en and fallback_book_title_en:
        book_title_en = normalize_text(fallback_book_title_en)

    book_title_en = book_title_en or fallback_book_title_en or ""
    book_title_en = normalize_text(book_title_en) or book_title_en

    all_hadith_container = root.css_first(".AllHadith")
    if all_hadith_container is None:
        LOGGER.warning("Could not find AllHadith container for book %s", book_id)
        return book_title_en, book_title_ar, book_number, []

    hadith_records: list[HadithRecord] = []
    chapter = ChapterContext(identifier=None, number_en=None, number_ar=None, title_en=None, title_ar=None)
    pending_anchor: Optional[str] = None

    node = all_hadith_container.child
    while node is not None:
        if node.tag == "a" and "name" in node.attributes:
            pending_anchor = node.attributes.get("name")
        elif node.tag == "div":
            classes = node.attributes.get("class", "") or ""
            class_tokens = set(classes.split())
            if "chapter" in class_tokens:
                chapter = parse_chapter_node(node, fallback_anchor=pending_anchor)
                pending_anchor = None
            elif "actualHadithContainer" in class_tokens:
                record = parse_hadith_container(
                    node,
                    collection_slug=collection_slug,
                    collection_name=collection_name,
                    book_id=book_id,
                    book_title_en=book_title_en,
                    book_title_ar=book_title_ar,
                    chapter=chapter,
                    base_url=book_url,
                )
                if record:
                    hadith_records.append(record)
        node = node.next

    if not hadith_records:
        LOGGER.warning("No hadith parsed for book %s", book_id)

    return book_title_en, book_title_ar, book_number, hadith_records
