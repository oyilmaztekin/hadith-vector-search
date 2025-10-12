# Quran.com Tafsir Scraper Plan

## 1. URL Structure
- Base pattern: `https://quran.com/{surah}:{ayah}/tafsirs/en-tafisr-ibn-kathir`
- Surah range: 1 → 114
- Ayah iteration: start at 1 for each surah, increment until receiving a 404 twice (to filter transient errors)

## 2. Response Inspection
- Direct page HTML only exposes partial metadata inside `__NEXT_DATA__` and omits tafsir text for many surahs.
- Quran.com exposes a public JSON API that returns tafsir content per ayah:
  - Endpoint: `https://api.qurancdn.com/api/qdc/tafsirs/{tafsir_slug}/by_ayah/{surah}:{ayah}`
  - Example: `/api/qdc/tafsirs/en-tafisr-ibn-kathir/by_ayah/1:1`
  - Response (200 OK) includes:
    - `tafsir.resource_id`, `resource_name`, `language_id`, `slug`, `translated_name`
    - `tafsir.verses` dictionary keyed by `"{surah}:{ayah}"`
    - `tafsir.text` – HTML string with the tafsir content for the requested ayah
- The API consistently returns data for all surahs/ayahs; no need to rely on partially populated `__NEXT_DATA__`.

## 3. Extraction Targets
- **Primary fields:**
  - `surah` (chapter number)
  - `ayah` (verse number)
  - `resource_name` (e.g., Ibn Kathir)
  - `resource_id` (numerical identifier)
  - `language_id` (should be 38 for English)
  - `translated_name.name` / `.language_name`
  - `text` (HTML content → store HTML + plain-text variant)
- **Optional contextual fields:**
  - `chapter.translatedName` and `chapter.transliteratedName`
  - Verse metadata from `tafsir['verses']` (contains `verseKey`, `verseId`, `chapterId`)
  - Slug (`tafsirIdOrSlug`) for consistency if other tafsir sources are scraped later

## 4. Parsing Considerations
- The HTML is well-formed; use `BeautifulSoup`/`selectolax` to derive plain text while keeping the original HTML.
- Handle headings (`<h1>`, `<h2>`) that denote sections within the tafsir.
- Some tafsir entries contain extended introductions spanning multiple ayat—ensure the loop does not assume short content.
- UTF-8 content with Arabic phrases; preserve HTML entities/diacritics.

## 5. Control Flow Outline
1. For each surah `1..114`:
   - Initialize `ayah = 1`.
   - For each ayah:
     - Request `https://api.qurancdn.com/api/qdc/tafsirs/en-tafisr-ibn-kathir/by_ayah/{surah}:{ayah}`.
     - If HTTP status 200:
       - Parse JSON payload (`tafsir` object).
       - Extract tafsir record and metadata.
       - Persist structured output (e.g., JSONL per surah) and optionally store raw JSON snapshot.
       - Increment `ayah` and continue.
     - If HTTP status 404:
       - Retry once; on a second 404, treat as end of surah (some tafsir resources skip verses).
     - Handle 429/500 with exponential backoff and limited retries.

## 6. Storage
- Suggested layout:
  - `html/quran/{surah}/{surah}_{ayah}.html` – raw response for reproducibility.
  - `data/quran/surah_{surah}.jsonl` – normalized tafsir records (one per ayah).
- Record checksum to detect content changes on re-scrape.

## 7. Next Steps
- Build a prototype fetcher for `surah=1, ayah=1` to validate parsing logic and schema.
- Implement looping logic with retry/termination handling.
- Add command-line interface similar to `sunnah_scraper` with `--surah` and `--range` filters.
- Consider rate limiting (1 req/sec) to avoid overloading Quran.com.
