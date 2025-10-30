#!/usr/bin/env python3
"""Scrape Ibn Kathir tafsir data from Quran.com API."""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any, Optional

import requests
from requests import Response
from selectolax.parser import HTMLParser

API_TEMPLATE = "https://api.qurancdn.com/api/qdc/tafsirs/{slug}/by_ayah/{surah}:{ayah}"
HTML_URL_TEMPLATE = "https://quran.com/{surah}:{ayah}/tafsirs/{slug}"
RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}
MAX_CONSECUTIVE_404 = 2
ARABIC_DIGIT_SUFFIX = re.compile(r"[\s\u0660-\u0669\u06F0-\u06F9\d]+$")

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape Quran tafsir content")
    parser.add_argument("--start-surah", type=int, default=1, help="First surah to scrape")
    parser.add_argument("--end-surah", type=int, default=114, help="Last surah to scrape")
    parser.add_argument("--start-ayah", type=int, default=1, help="First ayah when starting at start-surah")
    parser.add_argument("--slug", default="en-tafisr-ibn-kathir", help="Tafsir slug to request")
    parser.add_argument("--rate", type=float, default=1.0, help="Delay between requests in seconds")
    parser.add_argument("--max-retries", type=int, default=5, help="Retry attempts for transient errors")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint if available")
    parser.add_argument("--checkpoint", type=Path, default=None, help="Override checkpoint path")
    parser.add_argument("--out-dir", type=Path, default=None, help="Directory for normalized JSONL output")
    parser.add_argument("--raw-dir", type=Path, default=None, help="Directory for raw API payloads")
    return parser.parse_args()

def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]

def load_checkpoint(path: Path) -> Optional[tuple[int, int]]:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("surah"), data.get("ayah")

def save_checkpoint(path: Path, surah: int, ayah: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"surah": surah, "ayah": ayah, "timestamp": time.time()}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

def log_failure(path: Path, surah: int, ayah: int, status: str, detail: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "surah": surah,
        "ayah": ayah,
        "status": status,
        "detail": detail,
        "timestamp": time.time(),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

def extract_plain_text(html_text: str) -> str:
    parser = HTMLParser(html_text or "")
    text = parser.text(separator="\n")
    return text.strip()

def ensure_dirs(*paths: Path) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)

def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "QuranTafsirScraper/1.0 (Educational Purpose)",
            "Accept": "application/json, text/html;q=0.9",
        }
    )
    return session


def clean_arabic_text(text: str) -> str:
    if not text:
        return ""
    return ARABIC_DIGIT_SUFFIX.sub("", text).strip()


def derive_arabic_from_meta(meta: dict[str, Any]) -> dict[str, str]:
    simple = (
        meta.get("text_uthmani_simple")
        or meta.get("textUthmaniSimple")
        or meta.get("textSimple")
        or meta.get("text_clean")
    )
    uthmani = meta.get("text_uthmani") or meta.get("textUthmani")
    if not uthmani and simple:
        uthmani = simple
    if not simple and uthmani:
        simple = uthmani
    return {
        "text_arabic_simple": clean_arabic_text(simple or ""),
        "text_arabic_uthmani": clean_arabic_text(uthmani or ""),
    }


def extract_arabic_from_html(html: str) -> dict[str, str]:
    parser = HTMLParser(html or "")
    container = parser.css_first("div[class*='SeoTextForVerse_visuallyHidden__']")
    if not container:
        return {"text_arabic_simple": "", "text_arabic_uthmani": ""}
    lines = [clean_arabic_text(node.text()) for node in container.css("div") if node.text()]
    simple = lines[0] if lines else ""
    uthmani = lines[1] if len(lines) > 1 else simple
    return {
        "text_arabic_simple": simple,
        "text_arabic_uthmani": uthmani,
    }

def fetch_ayah(
    session: requests.Session,
    slug: str,
    surah: int,
    ayah: int,
    retries: int,
    failure_log: Path,
) -> tuple[Optional[dict[str, Any]], str]:
    url = API_TEMPLATE.format(slug=slug, surah=surah, ayah=ayah)
    for attempt in range(retries):
        try:
            response: Response = session.get(url, timeout=20)
        except requests.RequestException as exc:
            delay = min(2 ** attempt, 120)
            log_failure(failure_log, surah, ayah, "network-error", str(exc))
            time.sleep(delay)
            continue
        if response.status_code == 200:
            return response.json(), "ok"
        if response.status_code == 404:
            return None, "missing"
        if response.status_code in RETRYABLE_STATUS:
            delay = min(2 ** attempt, 120)
            time.sleep(delay)
            continue
        log_failure(
            failure_log,
            surah,
            ayah,
            f"status-{response.status_code}",
            response.text[:500],
        )
        return None, "error"
    log_failure(failure_log, surah, ayah, "max-retries", url)
    return None, "error"


def fetch_arabic_text(
    session: requests.Session,
    slug: str,
    surah: int,
    ayah: int,
    retries: int,
    failure_log: Path,
) -> dict[str, str]:
    url = HTML_URL_TEMPLATE.format(slug=slug, surah=surah, ayah=ayah)
    headers = {"Accept": "text/html,application/xhtml+xml"}
    for attempt in range(retries):
        try:
            response: Response = session.get(url, headers=headers, timeout=20)
        except requests.RequestException as exc:
            delay = min(2 ** attempt, 120)
            log_failure(failure_log, surah, ayah, "html-network-error", str(exc))
            time.sleep(delay)
            continue
        if response.status_code == 200:
            return extract_arabic_from_html(response.text)
        if response.status_code == 404:
            log_failure(failure_log, surah, ayah, "html-404", url)
            return {"text_arabic_simple": "", "text_arabic_uthmani": ""}
        if response.status_code in RETRYABLE_STATUS:
            delay = min(2 ** attempt, 120)
            time.sleep(delay)
            continue
        log_failure(
            failure_log,
            surah,
            ayah,
            f"html-status-{response.status_code}",
            response.text[:500],
        )
        return {"text_arabic_simple": "", "text_arabic_uthmani": ""}
    log_failure(failure_log, surah, ayah, "html-max-retries", url)
    return {"text_arabic_simple": "", "text_arabic_uthmani": ""}

def write_raw_payload(raw_dir: Path, surah: int, ayah: int, payload: dict[str, Any]) -> None:
    target_dir = raw_dir / f"{surah:03d}"
    target_dir.mkdir(parents=True, exist_ok=True)
    raw_path = target_dir / f"{surah:03d}_{ayah:03d}.json"
    raw_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

def write_normalized_record(out_dir: Path, surah: int, record: dict[str, Any]) -> None:
    jsonl_path = out_dir / f"surah_{surah:03d}.jsonl"
    with jsonl_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")

def build_record(surah: int, ayah: int, payload: dict[str, Any]) -> dict[str, Any]:
    tafsir = payload.get("tafsir", {})
    verse_key = f"{surah}:{ayah}"
    verses = tafsir.get("verses", {})
    verse_meta = verses.get(verse_key, {})
    text_html = tafsir.get("text", "")
    arabic_meta = derive_arabic_from_meta(verse_meta)
    return {
        "surah": surah,
        "ayah": ayah,
        "verse_key": verse_key,
        "resource_id": tafsir.get("resource_id"),
        "resource_name": tafsir.get("resource_name"),
        "language_id": tafsir.get("language_id"),
        "slug": tafsir.get("slug"),
        "translated_name": tafsir.get("translated_name"),
        "text_html": text_html,
        "text_plain": extract_plain_text(text_html),
        "verse_meta": verse_meta,
        "text_arabic_simple": arabic_meta["text_arabic_simple"],
        "text_arabic_uthmani": arabic_meta["text_arabic_uthmani"],
        "fetched_at": time.time(),
    }

def scrape(args: argparse.Namespace) -> None:
    root = repo_root()
    out_dir = args.out_dir if args.out_dir else root / "data" / "quran"
    raw_dir = args.raw_dir if args.raw_dir else root / "html" / "quran"
    checkpoint_path = (
        args.checkpoint if args.checkpoint else root / "checkpoints" / "quran_tafsir.json"
    )
    failure_log = root / "logs" / "quran" / "failed_requests.log"
    ensure_dirs(out_dir, raw_dir, checkpoint_path.parent, failure_log.parent)
    session = make_session()

    start_surah = max(1, args.start_surah)
    end_surah = min(114, args.end_surah)
    start_ayah = max(1, args.start_ayah)

    if start_surah > end_surah:
        raise ValueError("start-surah cannot exceed end-surah")

    if args.resume:
        checkpoint = load_checkpoint(checkpoint_path)
        if checkpoint:
            start_surah, start_ayah = checkpoint

    for surah in range(start_surah, end_surah + 1):
        misses = 0
        ayah = start_ayah if surah == start_surah else 1
        while True:
            payload, status = fetch_ayah(
                session, args.slug, surah, ayah, args.max_retries, failure_log
            )
            if status == "missing":
                misses += 1
                if misses >= MAX_CONSECUTIVE_404:
                    print(f"surah {surah:03d}: completed at ayah {ayah - 1 if ayah > 1 else 0}")
                    break
                time.sleep(args.rate)
                continue
            if status == "error":
                misses = 0
                ayah += 1
                time.sleep(args.rate)
                continue
            misses = 0
            record = build_record(surah, ayah, payload)
            if not record.get("text_arabic_uthmani"):
                html_arabic = fetch_arabic_text(
                    session, args.slug, surah, ayah, args.max_retries, failure_log
                )
                if html_arabic:
                    record.update(html_arabic)
            write_raw_payload(raw_dir, surah, ayah, payload)
            write_normalized_record(out_dir, surah, record)
            save_checkpoint(checkpoint_path, surah, ayah + 1)
            print(f"saved {record['verse_key']}")
            ayah += 1
            time.sleep(args.rate)
        start_ayah = 1
        if surah < end_surah:
            save_checkpoint(checkpoint_path, surah + 1, 1)


def main() -> None:
    args = parse_args()
    scrape(args)


if __name__ == "__main__":
    main()
