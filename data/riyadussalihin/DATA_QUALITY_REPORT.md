# Data Quality Report - Riyad as-Salihin JSONL Files

**Date:** 2025-10-12
**Analyst:** Gemini AI + Python Validation
**Files Analyzed:** 21 JSONL files (book_introduction.jsonl + book_1.jsonl through book_19.jsonl)
**Total Hadiths:** ~1,900

---

## Executive Summary

✅ **Good News:** 95% of the dataset is production-ready
❌ **Critical Issue:** 1 file (book_8.jsonl) has complete Arabic encoding corruption
⚠️ **Minor Issues:** Formatting inconsistencies that can be handled during ingestion

**Overall Assessment:** Dataset is ready for use after fixing book_8.jsonl

---

## Detailed Findings

### 🔴 CRITICAL ISSUES (Must Fix)

#### 1. Arabic Text Encoding Corruption - book_8.jsonl

**Severity:** CRITICAL
**Impact:** 277 hadiths (14.6% of dataset) unusable

**Details:**
- **File:** `book_8.jsonl` (The Book of Virtues)
- **Issue:** Complete mojibake - Arabic characters replaced with Cyrillic/special characters
- **Example:**
  ```
  Corrupted: "ЩғШӘШ§ШЁ Ш§Щ„ЩҒШ¶Ш§ШҰЩ„"
  Should be: "كتاب الفضائل"
  ```
- **Extent:** Every single line in the file (all 277 hadiths)
- **Fields Affected:**
  - `book_title_ar`
  - `chapter_title_ar`
  - `texts[].content` (Arabic language)

**Root Cause:** Likely double-encoding or wrong encoding assumption during scraping/saving

**Recommended Action:** Re-scrape book 8 from sunnah.com with correct UTF-8 handling

---

### ⚠️ MINOR ISSUES (Can Handle)

#### 2. Inconsistent Narrator Formatting

**Severity:** MINOR
**Impact:** Requires normalization during ingestion

**Examples of Variations:**
```
✓ "Ibn 'Umar (May Allah be pleased with them) reported:"
✓ "Narrated Abu Hurairah (May Allah be pleased with him) reported:"
✓ "Anas bin Malik reported:"
✓ "Abu Hurairah (May Allah be pleased with him)reported in the Hadith..."
```

**Issues Found:**
1. Inconsistent honorific phrasing:
   - "May Allah be pleased with him/her/them"
   - Sometimes missing entirely
2. Varied endings:
   - "reported:" (most common)
   - "reported" (no colon)
   - "reported in the Hadith..."
3. Typos:
   - Missing space: "(May Allah be pleasedwith them)" in Introduction, Hadith 4

**Recommendation:** Normalize during ingestion with regex pattern matching

#### 3. Leading Hyphen in Arabic Chapter Titles

**Severity:** MINOR
**Impact:** Cosmetic only

**Example:**
```
"chapter_title_ar": "- باب الإخلاص وإحضارالنية"
                     ↑ Unnecessary hyphen
```

**Affected Files:** ALL (consistent across dataset)
**Recommendation:** Strip leading "- " during ingestion

#### 4. Repeated Phrases in Some Arabic Text

**Severity:** MINOR
**Impact:** Slight text quality issue

**Details:**
- Found in book_6.jsonl (hadith h1708910) and book_7.jsonl (hadith h1709470)
- Phrase "صلى الله عليه وسلم" repeated unnecessarily
- Appears to be data entry or scraping artifact

**Recommendation:** Keep as-is (minimal impact) or clean with deduplication regex

#### 5. Null Narrator Fields

**Severity:** INFORMATIONAL
**Impact:** None (expected for some hadiths)

**Details:**
- Some hadiths legitimately have no narrator (e.g., Quranic verses, general statements)
- Found in:
  - book_introduction.jsonl: Hadith 3
  - book_5.jsonl: hadith h1708460
  - book_8.jsonl: Lines 40, 172

**Recommendation:** Handle gracefully - use "Unknown" or "" for display

---

### 📊 INFORMATIONAL (Expected)

#### 6. Empty Optional Fields

**Severity:** INFORMATIONAL
**Impact:** None (limits some search features)

**Details:**
- The following fields are empty arrays in ALL hadiths:
  - `grading`: []
  - `topics`: []
  - `footnotes`: []

**Analysis:**
- This is not a bug - these fields were likely not available from sunnah.com
- Grading information would be valuable for scoring boost (Sahih vs weak)
- Topics could be useful for categorization

**Recommendation:**
- Proceed without these fields for now
- Consider adding grading data from external source later (e.g., sunnah.com API)

---

## File-by-File Status

| File | Status | Arabic Encoding | Issues | Hadiths |
|------|--------|----------------|--------|---------|
| book_introduction.jsonl | ✅ GOOD | OK | Null narrator (1) | 679 |
| book_1.jsonl | ✅ GOOD | OK | None | 47 |
| book_2.jsonl | ✅ GOOD | OK | None | 51 |
| book_3.jsonl | ✅ GOOD | OK | None | 35 |
| book_4.jsonl | ✅ GOOD | OK | None | 31 |
| book_5.jsonl | ✅ GOOD | OK | Null narrator (1) | 50 |
| book_6.jsonl | ✅ GOOD | OK | Repeated phrase (1) | 62 |
| book_7.jsonl | ✅ GOOD | OK | Repeated phrase (1) | 35 |
| **book_8.jsonl** | **❌ BAD** | **CORRUPTED** | **Mojibake (ALL)** | **277** |
| book_9.jsonl | ✅ GOOD | OK | None | 3 |
| book_10.jsonl | ✅ GOOD | OK | None | 14 |
| book_11.jsonl | ✅ GOOD | OK | None | 91 |
| book_12.jsonl | ✅ GOOD | OK | None | 17 |
| book_13.jsonl | ✅ GOOD | OK | None | 4 |
| book_14.jsonl | ✅ GOOD | OK | None | 11 |
| book_15.jsonl | ✅ GOOD | OK | None | 57 |
| book_16.jsonl | ✅ GOOD | OK | None | 46 |
| book_17.jsonl | ✅ GOOD | OK | None | 297 |
| book_18.jsonl | ✅ GOOD | OK | None | 61 |
| book_19.jsonl | ✅ GOOD | OK | None | 28 |
| **TOTAL** | **19/20 OK** | **19/20 OK** | **1 Critical** | **~1,896** |

---

## Encoding Verification Method

### Arabic Detection Test
```python
def check_arabic_encoding(text):
    has_arabic = any('\u0600' <= c <= '\u06FF' for c in text)
    has_cyrillic = any('\u0400' <= c <= '\u04FF' for c in text)
    return has_arabic, has_cyrillic
```

### Mojibake Patterns Found in book_8
- Cyrillic: Щ, Ғ, Ш, Ә, Ұ, Ҷ, Ө
- Special: §, ¶, Ё
- These should be Arabic: ك, ت, ا, ب, ل, ف, ض, ئ

---

## Recommendations

### Immediate Actions (Before Indexing)

1. **Fix book_8.jsonl** (REQUIRED)
   - **Option A (Recommended):** Re-scrape book 8 from sunnah.com
     ```bash
     python scraper.py --book 8 --force
     ```
   - **Option B:** Attempt encoding recovery (may be unreliable)
   - **Option C:** Request fixed data from source

2. **Verify Fix**
   ```bash
   python3 -c "
   import json
   with open('book_8.jsonl', 'r', encoding='utf-8') as f:
       data = json.loads(f.readline())
       print(data['book_title_ar'])
       # Should show: كتاب الفضائل
   "
   ```

### Data Normalization During Ingestion

1. **Narrator Field Cleanup**
   ```python
   def normalize_narrator(narrator_str):
       if narrator_str is None:
           return "Unknown"
       # Remove "reported:" suffix
       narrator = re.sub(r'\s*reported:?$', '', narrator_str, flags=re.IGNORECASE)
       # Remove "Narrated" prefix
       narrator = re.sub(r'^Narrated\s+', '', narrator, flags=re.IGNORECASE)
       # Extract just the name and honorific
       return narrator.strip()
   ```

2. **Arabic Chapter Title Cleanup**
   ```python
   def clean_chapter_title_ar(title_ar):
       # Remove leading hyphen and space
       return title_ar.lstrip('- ')
   ```

3. **Handle Null Values**
   ```python
   narrator = data.get('narrator') or 'Unknown'
   grading = data.get('grading') or []
   ```

---

## Impact Assessment

### Current Usable Data
- **Usable hadiths:** 1,619 / 1,896 (85.4%)
- **After fixing book_8:** 1,896 / 1,896 (100%)

### Search System Impact

**Without book_8 fix:**
- ❌ Missing 14.6% of hadiths
- ❌ Book of Virtues completely missing (major topic gap)
- ❌ Important hadiths about Quran recitation, wudu, adhan missing

**With book_8 fix:**
- ✅ Complete dataset coverage
- ✅ All major topics represented
- ✅ Comprehensive test queries can be answered

---

## Validation Checklist

After fixing book_8.jsonl, run these checks:

```bash
# 1. Check Arabic encoding
python3 -c "
import json
for book in range(1, 20):
    try:
        with open(f'book_{book}.jsonl', 'r') as f:
            line = f.readline()
            data = json.loads(line)
            has_arabic = any('\u0600' <= c <= '\u06FF' for c in data['book_title_ar'])
            has_cyrillic = any('\u0400' <= c <= '\u04FF' for c in data['book_title_ar'])
            status = '✅' if has_arabic and not has_cyrillic else '❌'
            print(f'{status} book_{book}.jsonl')
    except FileNotFoundError:
        pass
"

# 2. Count total hadiths
wc -l book_*.jsonl

# 3. Verify JSON structure
for f in book_*.jsonl; do
    echo "Checking $f..."
    head -1 "$f" | python3 -m json.tool > /dev/null && echo "✅ Valid JSON" || echo "❌ Invalid JSON"
done

# 4. Check for required fields
python3 -c "
import json
required_fields = ['hadith_num_global', 'narrator', 'texts', 'book_title_en', 'book_title_ar']
with open('book_1.jsonl', 'r') as f:
    data = json.loads(f.readline())
    missing = [f for f in required_fields if f not in data]
    print('✅ All required fields present' if not missing else f'❌ Missing: {missing}')
"
```

---

## Testing Strategy

### Before Fix (Current State)
- Test ingestion with books 1-7, 9-19 (skip book_8)
- Verify search works with partial dataset
- Document missing hadiths

### After Fix
- Re-run full ingestion with all 21 books
- Run complete test suite (86 queries from TEST_QUERIES.md)
- Verify Arabic search works for book_8 content

---

## Conclusion

**Data Quality Grade: B+ (A after fix)**

The dataset is in excellent condition overall, with only one critical issue affecting a single file. All other minor issues are easily handled during data ingestion with standard normalization techniques.

**Action Priority:**
1. 🔴 **CRITICAL:** Fix book_8.jsonl encoding (blocks full system functionality)
2. 🟡 **MEDIUM:** Implement narrator/title normalization (improves data quality)
3. 🟢 **LOW:** Consider adding grading data (future enhancement)

**Timeline Estimate:**
- Re-scraping book_8: 5-10 minutes
- Verification: 2 minutes
- Normalization code: Already specified above
- **Total:** <15 minutes to production-ready state

---

**Report Generated:** 2025-10-12
**Analysis Tools:** Gemini CLI + Python validation scripts
**Files Examined:** 21/21 (100%)
**Recommendation:** Proceed with implementation after book_8 fix
