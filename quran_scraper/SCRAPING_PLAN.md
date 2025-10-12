# Quran.com Tafsir Scraping Plan

Comprehensive plan for scraping Quranic verses with Ibn Kathir tafsir (English) from quran.com.

## Table of Contents
1. [Overview](#overview)
2. [URL Structure](#url-structure)
3. [Page Structure Analysis](#page-structure-analysis)
4. [Scraping Algorithm](#scraping-algorithm)
5. [Data Schema](#data-schema)
6. [Implementation Steps](#implementation-steps)
7. [Error Handling](#error-handling)
8. [Technical Specifications](#technical-specifications)

---

## Overview

**Goal**: Extract all 6,236 ayahs (verses) from the Quran with their corresponding Ibn Kathir tafsir commentary.

**Source**: https://quran.com/{surah}:{ayah}/tafsirs/en-tafisr-ibn-kathir

**Scope**:
- 114 surahs (chapters)
- Variable number of ayahs per surah (discovered dynamically)
- Ibn Kathir tafsir (English translation)

---

## URL Structure

### Pattern
```
https://quran.com/{surah_number}:{ayah_number}/tafsirs/{tafsir_source}
```

### Examples
- First ayah: `https://quran.com/1:1/tafsirs/en-tafisr-ibn-kathir`
- Last ayah: `https://quran.com/114:6/tafsirs/en-tafisr-ibn-kathir`
- Invalid (404): `https://quran.com/1:8/tafsirs/en-tafisr-ibn-kathir`

### Tafsir Source Options
- `en-tafisr-ibn-kathir` (Primary target)
- `ar-tafseer-al-qurtubi` (Optional: Arabic)
- `ar-tafseer-al-tabari` (Optional: Arabic)
- More available in dropdown

---

## Page Structure Analysis

### IMPORTANT: Dynamic CSS Classes

⚠️ **CSS class names use CSS Modules with dynamic hashes**. Patterns to match:

- Arabic text: `SeoTextForVerse_visuallyHidden__*` (where `*` is a hash like `IYmKh`)
- Tafsir text: `TafsirText_xl__*`, `TafsirText_md__*`, `TafsirText_lg__*` (responsive variants)
- Verse group message: `TafsirMessage_tafsirMessage__*`

**Selector Strategy**: Use **attribute selectors with `contains`** or **starts-with** patterns:
```python
# Instead of exact class match:
soup.find(class_='SeoTextForVerse_visuallyHidden__IYmKh')

# Use partial match:
soup.find(class_=lambda x: x and 'SeoTextForVerse_visuallyHidden' in x)
# OR regex:
soup.find('div', class_=re.compile(r'SeoTextForVerse_visuallyHidden__\w+'))
```

### 1. Ayah Content Elements

#### Arabic Text
- **Class Pattern**: `SeoTextForVerse_visuallyHidden__*` (dynamic hash)
- **Format**: Plain text, Uthmani script
- **Location**: Hidden div (SEO purposes)
- **Extraction**: Use partial class name matching

#### English Translation
- **Location**: Visible on page, separate from Arabic
- **Format**: Plain text
- **Note**: May need different selector than word-by-word objects

#### Transliteration
- **Availability**: May not be in tafsir page (check if needed)

### 2. Tafsir Content Structure

#### Main Tafsir Text
- **Class Pattern**: `TafsirText_xl__*`, `TafsirText_md__*`, `TafsirText_lg__*`
- **Format**: **Plain text only** (no HTML needed)
- **Extraction**: Use partial class matching for any TafsirText variant
- **Example**:
  ```python
  tafsir_div = soup.find('div', class_=re.compile(r'TafsirText_(xl|md|lg)__\w+'))
  tafsir_text = tafsir_div.get_text(strip=True)
  ```

#### References
- Hadith citations (e.g., "Imam Ahmad recorded...", "Muslim narrated...")
- Chain of narrators
- Verse cross-references (e.g., "2:255", "3:1-2")

#### Tafsir Resource ID
- Ibn Kathir ID: `169`
- Stored in JSON metadata

### 3. Word-by-Word Data

Each word object contains:
```json
{
  "id": 1,
  "position": 1,
  "audioUrl": "wbw/001_001_001.mp3",
  "verseKey": "1:1",
  "verseId": 1,
  "location": "juz:1,page:1,hizb:1,rub:1",
  "textUthmani": "بِسْمِ",
  "translation": {
    "text": "In (the) name",
    "languageName": "english"
  },
  "transliteration": {
    "text": "bis'mi",
    "languageName": "english"
  }
}
```

### 4. Hidden Metadata

#### Build Info
```javascript
window.__BUILD_INFO__ = {
  "buildDate": "2025-10-04T18:28:47",
  "version": "25.10.0418",
  "environment": "production"
}
```

#### Chapter Metadata
- Surah name (Arabic & transliterated)
- Revelation place (Meccan/Medinan)
- Verse count
- Chronological order

---

## Scraping Algorithm

### Verse Grouping Discovery

**Critical Finding**: Ibn Kathir tafsir groups multiple verses together!

Examples:
- `8:9` → "You are reading a tafsir for the group of verses **8:9 to 8:10**" (2 verses)
- `8:11` → "You are reading a tafsir for the group of verses **8:11 to 8:14**" (4 verses)
- `2:1` → Single verse (no grouping message)

**Implication**: We can **skip grouped verses** to avoid duplicate scraping!

### Optimized Algorithm with Verse Grouping

```python
import re

def extract_verse_range(soup):
    """
    Extract verse range from TafsirMessage if present.
    Returns: (start_ayah, end_ayah) or (current_ayah, current_ayah) if single verse
    """
    # Find the message div: TafsirMessage_tafsirMessage__*
    message_div = soup.find('div', class_=re.compile(r'TafsirMessage_tafsirMessage__\w+'))

    if message_div:
        # Pattern: "You are reading a tafsir for the group of verses 8:9 to 8:10"
        text = message_div.get_text()
        match = re.search(r'(\d+):(\d+)\s+to\s+(\d+):(\d+)', text)
        if match:
            start_surah, start_ayah, end_surah, end_ayah = match.groups()
            return (int(start_ayah), int(end_ayah))

    # No grouping, single verse
    return None

def discover_and_scrape():
    for surah_num in range(1, 115):  # 114 surahs
        ayah_num = 1

        while True:
            url = f"https://quran.com/{surah_num}:{ayah_num}/tafsirs/en-tafisr-ibn-kathir"
            response = fetch_with_retry(url)

            if response.status_code == 404:
                # Verify end of surah
                retry_response = fetch_with_retry(url)
                if retry_response.status_code == 404:
                    logger.info(f"Surah {surah_num} ended at ayah {ayah_num - 1}")
                    break

            elif response.status_code == 200:
                soup = BeautifulSoup(response.text, 'lxml')

                # Extract data
                data = extract_ayah_data(soup, surah_num, ayah_num)
                save_data(data)

                # Check for verse grouping
                verse_range = extract_verse_range(soup)

                if verse_range:
                    start_ayah, end_ayah = verse_range
                    logger.info(f"Found grouped verses: {surah_num}:{start_ayah}-{end_ayah}")

                    # Store the same tafsir for all verses in the group
                    for grouped_ayah in range(start_ayah, end_ayah + 1):
                        if grouped_ayah != ayah_num:  # Don't duplicate current
                            data_copy = data.copy()
                            data_copy['ayah_num'] = grouped_ayah
                            data_copy['verse_key'] = f"{surah_num}:{grouped_ayah}"
                            data_copy['is_grouped'] = True
                            data_copy['group_range'] = f"{start_ayah}-{end_ayah}"
                            save_data(data_copy)

                    # Jump to next verse after the group
                    ayah_num = end_ayah + 1
                else:
                    # Single verse, move to next
                    ayah_num += 1
            else:
                # Handle other errors
                handle_error(response)
                ayah_num += 1  # Try next verse
```

### Key Features
1. **Verse Grouping Detection**: Parse `TafsirMessage_tafsirMessage__*` div
2. **Smart Jumping**: Skip already-grouped verses (e.g., 8:9→8:10, jump to 8:11)
3. **Duplicate Tafsir Storage**: Save same tafsir for all verses in group
4. **Dynamic Discovery**: No hardcoded ayah counts
5. **404 Verification**: Double-check to avoid false positives
6. **Optimized Scraping**: Significantly fewer requests!

---

## Data Schema

### AyahRecord Structure (Updated)

```json
{
  "surah_num": 8,
  "ayah_num": 9,
  "verse_key": "8:9",

  "arabic_text": "إِذْ تَسْتَغِيثُونَ رَبَّكُمْ فَاسْتَجَابَ لَكُمْ",
  "english_translation": "[Remember] when you asked help of your Lord, and He answered you...",

  "tafsir": {
    "source": "en-tafisr-ibn-kathir",
    "text": "Allah reminds the believers of the Battle of Badr..."
  },

  "verse_grouping": {
    "is_grouped": true,
    "group_range": "8:9-8:10",
    "group_start": 9,
    "group_end": 10
  },

  "metadata": {
    "surah_name_ar": "الأنفال",
    "surah_name_en": "Al-Anfal",
    "revelation_place": "Medinan"
  },

  "source_url": "https://quran.com/8:9/tafsirs/en-tafisr-ibn-kathir",
  "scraped_at": "2025-10-09T22:00:00Z",
  "checksum": "sha256:abc123..."
}
```

### Simplified Schema (No HTML, No Word-by-Word)

**Key Changes**:
1. ✅ **Arabic text only** (from `SeoTextForVerse_visuallyHidden__*`)
2. ✅ **Plain text tafsir** (from `TafsirText_xl__*`, no HTML)
3. ✅ **Verse grouping metadata** (is_grouped, group_range)
4. ❌ **No word-by-word data** (not needed)
5. ❌ **No transliteration** (not on tafsir page)
6. ❌ **No HTML content** (plain text only)
```

### Output Files

```
data/
├── quran/
│   ├── surah_001.jsonl    # Al-Fatihah (7 ayahs)
│   ├── surah_002.jsonl    # Al-Baqarah (286 ayahs)
│   ├── ...
│   ├── surah_114.jsonl    # An-Nas (6 ayahs)
│   └── index.json         # Metadata for all surahs
│
html/
└── quran/
    ├── 001_001.html       # Raw HTML snapshots
    ├── 001_002.html
    └── ...
```

### Index File Structure

```json
{
  "collection": "quran_tafsir_ibn_kathir",
  "total_surahs": 114,
  "total_ayahs": 6236,
  "last_updated": "2025-10-09T21:45:00Z",
  "surahs": [
    {
      "number": 1,
      "name_ar": "الفاتحة",
      "name_en": "Al-Fatihah",
      "transliteration": "Al-Faatiha",
      "ayah_count": 7,
      "revelation_place": "Meccan",
      "chronological_order": 5
    }
  ]
}
```

---

## Implementation Steps

### Phase 1: Setup & Infrastructure

1. **Project Structure**
   ```
   quran_scraper/
   ├── __init__.py
   ├── cli.py              # Main entry point
   ├── scraper.py          # Core scraping logic
   ├── parser.py           # HTML parsing
   ├── models.py           # Data models (Pydantic)
   ├── http.py             # HTTP client with retry logic
   └── storage.py          # File I/O operations
   ```

2. **Dependencies**
   ```
   beautifulsoup4>=4.12.0
   requests>=2.31.0
   tenacity>=8.2.0         # Retry logic
   pydantic>=2.0.0         # Data validation
   lxml>=4.9.0             # Fast HTML parsing
   ```

3. **Configuration**
   - Base URL
   - Rate limiting (1 req/sec)
   - Retry settings (3 attempts, exponential backoff)
   - Output directories

### Phase 2: Core Development

1. **HTTP Client** (`http.py`)
   - Session management
   - Rate limiting (1 request/second)
   - Retry logic with exponential backoff
   - User-Agent headers
   - Timeout handling

2. **HTML Parser** (`parser.py`)
   - Extract Arabic text (CSS: `.textUthmani`)
   - Extract translation
   - Extract transliteration
   - Extract tafsir HTML
   - Clean and structure data
   - Handle word-by-word breakdown

3. **Data Models** (`models.py`)
   - Pydantic models for validation
   - JSON serialization
   - Checksum calculation (SHA-256)

4. **Storage Manager** (`storage.py`)
   - JSONL writer
   - HTML snapshot saver
   - Index file updater
   - Checkpoint/resume logic

5. **Scraper Core** (`scraper.py`)
   - Discovery algorithm
   - 404 detection and verification
   - Progress tracking
   - Error recovery

### Phase 3: CLI & Execution

1. **CLI Interface** (`cli.py`)
   ```bash
   # Scrape all surahs
   python -m quran_scraper.cli

   # Scrape specific surahs
   python -m quran_scraper.cli --surah 1 --surah 2

   # Resume from checkpoint
   python -m quran_scraper.cli --resume

   # Specify tafsir source
   python -m quran_scraper.cli --tafsir en-tafisr-ibn-kathir
   ```

2. **Progress Logging**
   - Real-time progress bar
   - Success/error counts
   - ETA calculation
   - Checkpoint saving

### Phase 4: Testing & Validation

1. **Unit Tests**
   - Parser tests with saved HTML fixtures
   - Model validation tests
   - URL generation tests

2. **Integration Tests**
   - End-to-end scraping (surah 114 - shortest)
   - 404 detection verification
   - Resume functionality

3. **Validation**
   - Verify ayah counts match known totals
   - Check data completeness
   - Validate JSON structure

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Extract and save data |
| 404 | Not Found | Verify twice, then mark end of surah |
| 403 | Forbidden | Check headers, add delay, retry |
| 429 | Rate Limited | Exponential backoff (30s, 60s, 120s) |
| 500 | Server Error | Retry 3x with backoff, then skip |
| Timeout | Request timeout | Retry 3x, then skip |

### Error Recovery Strategies

1. **Transient Errors** (500, 503, timeout)
   - Retry with exponential backoff
   - Max 3 attempts
   - Log and continue

2. **Rate Limiting** (429, 403)
   - Increase delay between requests
   - Wait 60 seconds before retry
   - Respect server limits

3. **Persistent Failures**
   - Save to failed_requests.log
   - Continue with next ayah
   - Manual review later

4. **Checkpoint System**
   - Save progress every 10 ayahs
   - Store: `checkpoint.json`
   ```json
   {
     "last_surah": 2,
     "last_ayah": 150,
     "timestamp": "2025-10-09T21:45:00Z"
   }
   ```
   - Resume from checkpoint on restart

---

## Technical Specifications

### Rate Limiting
- **Base Rate**: 1 request/second
- **Burst Protection**: No concurrent requests
- **Politeness**: User-Agent header identifying scraper
- **Respect robots.txt**: Check before scraping

### Headers
```python
headers = {
    'User-Agent': 'QuranTafsirScraper/1.0 (Educational Purpose)',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive'
}
```

### Performance Estimates
- **Total ayahs**: 6,236
- **Rate**: 1 req/sec
- **Base time**: ~104 minutes (1.7 hours)
- **With retries**: ~2-3 hours
- **Daily limit**: 86,400 requests (way under limit)

### Storage Requirements
- **HTML snapshots**: ~50KB average × 6,236 = ~310MB
- **JSONL data**: ~10KB average × 6,236 = ~62MB
- **Total**: ~400MB (with overhead)

### CSS Selectors Reference (Updated with Dynamic Classes)

| Data | Selector Pattern | Extraction Method | Notes |
|------|------------------|-------------------|-------|
| Arabic text | `SeoTextForVerse_visuallyHidden__*` | `re.compile(r'SeoTextForVerse_visuallyHidden__\w+')` | Dynamic hash, plain text |
| Tafsir text | `TafsirText_xl__*` or `TafsirText_md__*` | `re.compile(r'TafsirText_(xl\|md\|lg)__\w+')` | Responsive variants, plain text only |
| Verse grouping | `TafsirMessage_tafsirMessage__*` | `re.compile(r'TafsirMessage_tafsirMessage__\w+')` | Parse "X:Y to X:Z" pattern |
| English translation | TBD (inspect page) | Class or data attribute | May need testing |

**Important**: All selectors must use **regex patterns** or **lambda functions** to handle dynamic hashes!

---

## Validation Checklist

### Pre-Scrape
- [ ] Check robots.txt compliance
- [ ] Test single ayah extraction
- [ ] Verify 404 detection works
- [ ] Test resume functionality

### Post-Scrape
- [ ] Total ayahs = 6,236
- [ ] All surahs present (1-114)
- [ ] No duplicate entries
- [ ] All JSON files valid
- [ ] Sample manual verification (10 random ayahs)

### Known Edge Cases
1. **Surah 1 (Al-Fatihah)**: 7 ayahs
2. **Surah 2 (Al-Baqarah)**: 286 ayahs (longest)
3. **Surah 103-114**: Very short surahs
4. **Special characters**: Arabic diacritics, HTML entities

---

## Next Steps

1. **Discuss & Approve**: Review this plan
2. **Setup Project**: Create directory structure
3. **Implement Core**: Build HTTP client and parser
4. **Test**: Validate on single surah
5. **Full Scrape**: Run on all 114 surahs
6. **Validate**: Check data completeness
7. **Document**: Update README with results

---

## Questions for Discussion

1. **Word-by-word data**: Include detailed word breakdown or just full text?
2. **Multiple tafsirs**: Add other tafsir sources later?
3. **Languages**: Include Arabic/Urdu tafsirs?
4. **Storage**: JSONL sufficient or prefer database?
5. **Audio**: Download word-by-word audio files?
6. **Resume logic**: Auto-resume on failure or manual?
7. **Validation**: How strict should data validation be?

---

**Last Updated**: 2025-10-09
**Status**: Planning Phase
**Next Action**: Review and approve plan
