# Hadith Search System - Test Query Collection

**Dataset:** Riyad as-Salihin (~1,900 hadiths across 21 books)
**Purpose:** Comprehensive test queries for benchmarking hybrid search system
**Generated:** Based on Gemini analysis of actual JSONL data

---

## Data Quality Notes

⚠️ **Encoding Issue Detected:**
- `book_8.jsonl` and `book_17.jsonl` have corrupted Arabic text (mojibake)
- Example: `ЩғШӘШ§ШЁ Ш§Щ„ЩҒШ¶Ш§ШҰЩ„` instead of proper Arabic
- **Action Required:** Re-scrape or fix encoding before indexing

---

## Query Categories Overview

| Category | Count | Purpose |
|----------|-------|---------|
| Exact References | 8 | Test SQLite FTS5 lookup speed |
| Narrator-Based | 10 | Test metadata filtering + boosting |
| English Thematic | 20 | Test semantic understanding |
| Arabic Thematic | 15 | Test multilingual embeddings |
| Keyword/Phrase | 15 | Test exact-term prioritization |
| Mixed Language | 10 | Test cross-lingual search |
| Edge Cases | 8 | Test handling of complex queries |
| **Total** | **86** | Comprehensive coverage |

---

## 1. Exact Reference Queries

**Purpose:** Test direct lookup via SQLite FTS5 (should be <5ms)

```
1.1  Riyad as-Salihin 1
1.2  Riyad as-Salihin 680
1.3  Book 1, Hadith 10
1.4  Introduction, Hadith 25
1.5  Find hadith 1511
1.6  Show me Riyad as-Salihin 993
1.7  hadith number 682
1.8  reference: Introduction 8
```

**Expected Behavior:**
- Router should classify as `exact_reference`
- Use FTS5 direct lookup, not vector search
- Return single exact match
- Response time: <5ms

---

## 2. Narrator-Based Queries

**Purpose:** Test narrator field matching with 40% score boost

```
2.1  Hadith narrated by Abu Hurairah
2.2  What did 'Aishah narrate about the Prophet's speech?
2.3  أحاديث رواها ابن مسعود
2.4  Find hadith from Mu'adh bin Jabal about the tongue
2.5  Narrations from Ibn 'Umar
2.6  Show me hadith from Anas bin Malik about water
2.7  Abu Hurairah about sins
2.8  Stories narrated by Fatimah
2.9  Hadith from Abdullah bin Amr
2.10 What did Ibn Abbas say about patience?
```

**Expected Behavior:**
- Router should classify as `narrator_focused`
- Apply 40% narrator_match_bonus for exact narrator matches
- Results should heavily favor specified narrator
- Arabic narrator names should match English equivalents

**Key Narrators in Dataset:**
- Abu Hurairah (أبو هريرة) - Most frequent
- 'Aishah (عائشة)
- Ibn 'Umar (ابن عمر)
- Anas bin Malik (أنس بن مالك)
- Ibn Mas'ud (ابن مسعود)

---

## 3. English Thematic Queries

**Purpose:** Test semantic understanding and hybrid scoring

### 3.1 Moral & Ethical Topics

```
3.1.1  hadith on the signs of a hypocrite
3.1.2  what is backbiting in Islam?
3.1.3  hadith about controlling your anger
3.1.4  how to avoid lying
3.1.5  hadith about speaking good or remaining silent
3.1.6  stories of repentance in hadith
3.1.7  hadith about not speaking ill of others
3.1.8  two-faced person in hadith
3.1.9  hadith on fulfilling promises
3.1.10 importance of modesty in Islam
```

### 3.2 Worship & Practice

```
3.2.1  virtues of reciting Surah Al-Ikhlas
3.2.2  hadith on what to say after hearing the Adhan
3.2.3  reward for performing Wudu' perfectly
3.2.4  hadith about reading Quran daily
3.2.5  benefits of Surah Al-Kahf on Friday
3.2.6  hadith about prayer times
3.2.7  virtues of fasting
3.2.8  hadith on night prayer
```

### 3.3 Character & Conduct

```
3.3.1  hadith about intention (niyyah)
3.3.2  hadith on patience during hardship
3.3.3  importance of being truthful
3.3.4  hadith about controlling the tongue
3.3.5  good manners in Islam
```

**Expected Behavior:**
- Router should classify as `contextual_english` or `hybrid`
- Use semantic search with term prioritization
- Apply coverage_bonus for term matches
- Return contextually relevant results even with different wording

---

## 4. Arabic Thematic Queries

**Purpose:** Test multilingual embeddings and Arabic term matching

### 4.1 Worship & Virtues

```
4.1.1  حديث عن فضل تلاوة القرآن
4.1.2  فضل الوضوء
4.1.3  فضل سورة الكهف
4.1.4  دعاء بعد الأذان
4.1.5  أجر الصلاة في المسجد
4.1.6  فضل قراءة سورة الإخلاص
```

### 4.2 Ethics & Prohibitions

```
4.2.1  أحاديث عن الصبر
4.2.2  تحريم الغيبة والنميمة
4.2.3  ما هو النفاق
4.2.4  حديث عن حفظ اللسان
4.2.5  عقوبة الكذب
4.2.6  تحريم الكذب
4.2.7  النهي عن الغضب
```

### 4.3 Intention & Sincerity

```
4.3.1  إنما الأعمال بالنيات
4.3.2  حديث عن الإخلاص
```

**Expected Behavior:**
- Router should classify as `contextual_arabic`
- Apply arabic_term_bonus (30%) for Arabic term matches
- Multilingual embeddings should find semantically related hadiths
- Should match both Arabic text and narrator names in Arabic

---

## 5. Keyword & Exact Phrase Queries

**Purpose:** Test exact-term prioritization and phrase matching (30% bonus)

### 5.1 Exact Phrases

```
5.1.1  "speak good or remain silent"
5.1.2  "deeds are considered by the intentions"
5.1.3  "shyness is a branch of faith"
5.1.4  "modesty is a part of Iman"
5.1.5  "religion is sincerity"
5.1.6  "actions are judged by intentions"
5.1.7  "the strong person is the one who controls himself"
5.1.8  "whoever believes in Allah and the Last Day"
```

### 5.2 Arabic Exact Phrases

```
5.2.1  "اتقوا الله واصبروا"
5.2.2  "الحياء من الإيمان"
5.2.3  "إنما الأعمال بالنيات"
5.2.4  "أفرى الفرى"
5.2.5  "الدين النصيحة"
5.2.6  "من كان يؤمن بالله واليوم الآخر"
```

### 5.3 Specific Terms

```
5.3.1  hadith mentioning "Al-Wasilah"
5.3.2  find hadith with "Dajjal"
5.3.3  hadith about "Al-Ghurr Al-Muhajjalun"
5.3.4  hadith mentioning Jibril
```

**Expected Behavior:**
- Should trigger phrase_bonus (0.3) when exact phrase found
- Term coverage should be 100% for exact phrase matches
- Priority score should be highest (>2.0)
- Explanation: "🎯 Perfect: Contains your exact phrase"

---

## 6. Mixed Language & Cross-Lingual Queries

**Purpose:** Test multilingual embeddings for cross-lingual retrieval

```
6.1  hadith about الصبر (patience)
6.2  what is النية in hadith?
6.3  Abu Hurairah عن الإيمان
6.4  English translation of "إنما الأعمال بالنيات"
6.5  hadith on الوضوء (wudu)
6.6  find hadith with phrase "Al-Ghurr Al-Muhajjalun" in Arabic
6.7  Ibn Umar about الحياء
6.8  virtues of قراءة القرآن
6.9  what is الغيبة والنميمة
6.10 hadith on الصدق (truthfulness)
```

**Expected Behavior:**
- Should match across languages (query in English, find Arabic hadith)
- Both arabic_term_bonus and english_term_bonus should apply
- Multilingual embeddings critical for success
- High coverage_ratio despite mixed languages

---

## 7. Complex & Compound Queries

**Purpose:** Test hybrid approach with multiple criteria

### 7.1 Narrator + Topic

```
7.1.1  Abu Hurairah about charity
7.1.2  'Aishah narrating about modesty
7.1.3  Ibn 'Umar on prayer
7.1.4  Anas bin Malik about water and purity
7.1.5  Ibn Mas'ud on reciting Quran
```

### 7.2 Topic + Quality Filter

```
7.2.1  Sahih hadith on patience
7.2.2  authentic hadith about repentance
7.2.3  weak hadith on virtues (should rank lower)
```

### 7.3 Book/Chapter Specific

```
7.3.1  hadith from Book of Good Manners about promises
7.3.2  prohibition in Book 17
7.3.3  virtues from the introduction
```

**Expected Behavior:**
- Should apply both narrator_bonus and topic matching
- grading_boost should favor Sahih (0.15) > Hasan (0.10)
- Multiple scoring components should combine effectively
- Explanation should mention multiple match factors

---

## 8. Edge Cases & Challenging Queries

**Purpose:** Test robustness and error handling

```
8.1  hadith about something not in the dataset
8.2  random gibberish query: asdfghjkl
8.3  very long query with many irrelevant terms: I want to find a hadith that talks about patience and how to be patient during difficult times when facing hardships and trials in life
8.4  single word: patience
8.5  special characters: hadith@#$%
8.6  numbers only: 12345
8.7  mixed scripts: حديثpatience模忍
8.8  empty query: ""
```

**Expected Behavior:**
- Should handle gracefully without errors
- Low-quality queries should return semantic matches with low scores
- Very specific queries should use term prioritization
- Empty/invalid queries should return helpful error messages

---

## 9. Story & Narrative Queries

**Purpose:** Test understanding of hadith narratives

```
9.1  story of the three men in the cave
9.2  hadith about the person who killed 99 people
9.3  story of the man who never did good except Tawheed
9.4  hadith about the prostitute who gave water to a dog
9.5  story of the man who gave charity secretly
```

**Expected Behavior:**
- Should match based on narrative elements, not just keywords
- Semantic similarity critical (story descriptions vary)
- May require higher n_results for retrieval before re-ranking

---

## 10. Question-Based Queries (How-To)

**Purpose:** Test natural language question understanding

```
10.1  How to attain patience in Islam?
10.2  What are the signs of a hypocrite?
10.3  When should I recite Surah Al-Kahf?
10.4  Why is intention important in Islam?
10.5  How to avoid backbiting?
10.6  What to say after the Adhan?
10.7  How to perform perfect wudu?
10.8  What breaks modesty?
10.9  How to control anger?
10.10 What are the rights of a guest?
```

**Expected Behavior:**
- Router should classify as `contextual`
- Extract key terms (patience, hypocrite, intention, etc.)
- Apply semantic matching for "how to" intent
- Results should be instructional/descriptive hadiths

---

## Benchmark Metrics to Track

For each query, measure:

### Performance Metrics
```python
{
    'query': str,
    'query_type': str,  # from router
    'response_time_ms': float,
    'vector_search_time': float,
    'scoring_time': float,
    'total_candidates': int,
    'results_returned': int
}
```

### Quality Metrics
```python
{
    'top_result': {
        'hadith_num': str,
        'priority_score': float,
        'semantic_score': float,
        'term_coverage': float,
        'narrator_match': bool,
        'grading': str,
        'explanation': str
    },
    'average_term_coverage': float,
    'perfect_matches': int,  # results with 100% term coverage
    'narrator_accuracy': bool  # for narrator queries
}
```

### Success Criteria
```python
targets = {
    'exact_reference': {
        'response_time': '<5ms',
        'accuracy': '100%'
    },
    'narrator_focused': {
        'narrator_accuracy': '100%',
        'term_coverage': '>80%'
    },
    'thematic': {
        'relevance': '>90%',
        'term_coverage': '>70%'
    },
    'phrase_match': {
        'exact_phrase_found': '100%',
        'priority_score': '>2.0'
    },
    'cross_lingual': {
        'success_rate': '>85%'
    }
}
```

---

## Usage Instructions

### Running Individual Queries

```bash
# Test exact reference
python hadith_search.py --query "Riyad as-Salihin 680"

# Test narrator search
python hadith_search.py --query "Abu Hurairah about patience"

# Test Arabic query
python hadith_search.py --query "حديث عن الصبر"
```

### Running Benchmark Suite

```bash
# Run all queries and generate report
python benchmark_search.py --queries TEST_QUERIES.md --output benchmark_results.json

# Run specific category
python benchmark_search.py --category "narrator_based" --verbose

# Compare approaches
python benchmark_search.py --compare-all --queries TEST_QUERIES.md
```

### Expected Output Format

```json
{
  "query": "Abu Hurairah about patience",
  "query_type": "narrator_focused",
  "response_time_ms": 12.5,
  "results": [
    {
      "rank": 1,
      "hadith_num": "Riyad as-Salihin 1",
      "narrator": "Abu Hurairah",
      "priority_score": 2.15,
      "score_breakdown": {
        "semantic": 0.82,
        "narrator_bonus": 0.40,
        "term_coverage": 0.67,
        "grading_boost": 0.15
      },
      "explanation": "⭐ Excellent: Matches narrator and 67% of terms",
      "text_preview": "Abu Hurairah reported: The Messenger of Allah said..."
    }
  ]
}
```

---

## Notes for Implementation

1. **Priority Areas:**
   - Exact reference queries MUST be fast (<5ms)
   - Narrator matching MUST be accurate (100%)
   - Arabic queries require multilingual embeddings

2. **Data Quality Fix Required:**
   - Re-scrape or fix encoding for book_8.jsonl and book_17.jsonl
   - Validate Arabic text before indexing

3. **Benchmark Goals:**
   - Match or exceed Appcircle's 100% win rate
   - Achieve >70% average term coverage
   - Maintain <50ms p95 latency for vector search

4. **Query Router Accuracy:**
   - Should correctly classify >95% of queries
   - Misclassification acceptable only for ambiguous edge cases

---

**Generated:** Based on Gemini analysis of Riyad as-Salihin JSONL files
**Last Updated:** 2025-10-12
**Total Queries:** 86 across 10 categories
