# Hadith Vector Search System - Technical Specification

**Based on Analysis of Appcircle Documentation Search (100% Win Rate Approach)**

## Executive Summary

This specification outlines the architecture for a hybrid hadith search system based on the proven "Exact-Term Prioritization" approach from the Appcircle documentation search, which achieved 100% win rate in benchmarks.

**Key Principles:**
1. **Hybrid Search**: Combine semantic similarity with exact term matching
2. **Multilingual Support**: Arabic + English cross-lingual search
3. **Metadata-Rich**: Leverage narrator, grading, book/chapter for boosting
4. **Query Classification**: Route different query types to optimal search strategies

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Query Input                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  Query Router                                │
│  ┌──────────────┬──────────────┬──────────────┬──────────┐ │
│  │ Reference    │  Narrator    │  Thematic    │  Hybrid  │ │
│  │ (Bukhari 42) │  (Abu Hur.)  │  (forgive.)  │ (mixed)  │ │
│  └──────────────┴──────────────┴──────────────┴──────────┘ │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
┌──────────────┐ ┌─────────────┐ ┌──────────────┐
│  SQLite FTS5 │ │  ChromaDB   │ │ Hybrid Scorer│
│  (Exact Ref) │ │  (Vectors)  │ │ (Combined)   │
└──────────────┘ └─────────────┘ └──────────────┘
        │              │              │
        └──────────────┼──────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Priority Score Calculation                      │
│  • Semantic Similarity (25%)                                 │
│  • Narrator Match Bonus (40%)                                │
│  • Arabic Term Matches (30%)                                 │
│  • English Term Matches (25%)                                │
│  • Term Coverage (30%)                                       │
│  • Grading Boost (15% Sahih, 10% Hasan)                     │
│  • Phrase Matching (30%)                                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  Ranked Results                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Data Model & Ingestion

### Hadith Document Structure

```python
@dataclass
class HadithDocument:
    """Canonical hadith document structure"""

    # IDs
    canonical_id: str  # "riyadussalihin:1:680"
    hadith_id_site: str  # "h1706760"
    hadith_num_global: str  # "Riyad as-Salihin 680"

    # Content (multilingual)
    text_arabic: str
    text_english: str
    combined_text: str  # Concatenated for embedding

    # Metadata
    narrator: str  # "Ibn 'Umar"
    narrator_arabic: str  # "ابن عمر"

    # Classification
    collection_slug: str  # "riyadussalihin"
    collection_name: str
    book_id: str
    book_title_en: str
    book_title_ar: str
    chapter_id: str
    chapter_title_en: str
    chapter_title_ar: str

    # Quality
    grading: List[str]  # ["Sahih", "Mutawatir"]

    # References
    references: List[Dict]
    source_url: str

    # Processing
    checksum: str
    scraped_at: datetime
```

### Ingestion Pipeline

```python
class HadithIngestionPipeline:
    """Load JSONL → Normalize → Store in ChromaDB + SQLite"""

    def load_jsonl_collection(self, collection_path: str) -> List[HadithDocument]:
        """Load all JSONL files from a collection directory"""
        pass

    def normalize_hadith(self, raw_json: dict) -> HadithDocument:
        """Convert raw JSONL to canonical HadithDocument"""
        pass

    def should_reindex(self, hadith: HadithDocument) -> bool:
        """Check if hadith needs reindexing based on checksum"""
        pass

    def ingest_to_vector_store(self, hadiths: List[HadithDocument]):
        """Embed and store in ChromaDB"""
        pass

    def ingest_to_fts_index(self, hadiths: List[HadithDocument]):
        """Store in SQLite FTS5 for exact lookups"""
        pass
```

---

## Phase 2: Vector Store Setup

### Embedding Model

**Use:** `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`

**Why:**
- Supports 50+ languages including Arabic and English
- 768-dimensional embeddings (vs 384 for MiniLM)
- Better cross-lingual semantic understanding
- Proven for multilingual retrieval tasks

**Alternative (if performance is critical):**
- `sentence-transformers/LaBSE` (smaller, faster, still multilingual)

### ChromaDB Configuration

```python
import chromadb
from chromadb.config import Settings

client = chromadb.PersistentClient(
    path="./vector_db/hadith_chroma",
    settings=Settings(
        anonymized_telemetry=False,
        allow_reset=True
    )
)

collection = client.get_or_create_collection(
    name="hadith_search",
    metadata={
        "hnsw:space": "cosine",
        "description": "Riyad as-Salihin hadith collection"
    }
)
```

### Document Storage Format

```python
# What gets stored in ChromaDB
collection.add(
    ids=[hadith.canonical_id],
    embeddings=[embedding_vector],  # 768-dim from multilingual model
    documents=[hadith.combined_text],  # AR + EN concatenated
    metadatas=[{
        'hadith_num': hadith.hadith_num_global,
        'narrator': hadith.narrator,
        'narrator_ar': hadith.narrator_arabic,
        'book_title': hadith.book_title_en,
        'chapter_title': hadith.chapter_title_en,
        'grading': ','.join(hadith.grading) if hadith.grading else '',
        'text_ar': hadith.text_arabic,
        'text_en': hadith.text_english,
        'url': hadith.source_url,
        'collection': hadith.collection_slug
    }]
)
```

---

## Phase 3: SQLite FTS5 Index

### Schema

```sql
-- Exact reference lookups
CREATE VIRTUAL TABLE hadith_fts USING fts5(
    canonical_id UNINDEXED,
    hadith_num,           -- "Riyad as-Salihin 680"
    text_english,         -- Full English text
    text_arabic,          -- Full Arabic text
    narrator,             -- "Abu Huraira"
    narrator_arabic,      -- "أبو هريرة"
    book_title,
    chapter_title,
    grading UNINDEXED,
    collection UNINDEXED,
    tokenize='porter unicode61'
);

-- Metadata lookup table
CREATE TABLE hadith_metadata (
    canonical_id TEXT PRIMARY KEY,
    hadith_num TEXT,
    narrator TEXT,
    book_id TEXT,
    chapter_id TEXT,
    grading TEXT,
    source_url TEXT,
    checksum TEXT,
    scraped_at TIMESTAMP
);

-- Indexes for fast filtering
CREATE INDEX idx_narrator ON hadith_metadata(narrator);
CREATE INDEX idx_grading ON hadith_metadata(grading);
CREATE INDEX idx_collection ON hadith_metadata(collection);
```

---

## Phase 4: Query Router

### Classification Logic

```python
class HadithQueryRouter:
    """Classify and route queries to optimal search strategy"""

    NARRATOR_NAMES = {
        'abu huraira', 'aisha', 'ibn umar', 'ibn abbas',
        'anas bin malik', 'abu said', 'jabir', 'umar',
        # Arabic versions
        'أبو هريرة', 'عائشة', 'ابن عمر'
    }

    def classify(self, query: str) -> str:
        """
        Returns: 'exact_reference' | 'narrator_focused' |
                 'contextual_arabic' | 'contextual_english' | 'hybrid'
        """
        query_lower = query.lower()

        # Exact reference patterns
        if re.match(r'(bukhari|muslim|riyadussalihin|tirmidhi)\s+\d+', query_lower):
            return 'exact_reference'

        # Pure Arabic query
        if self._is_arabic_query(query):
            return 'contextual_arabic'

        # Narrator-focused query
        if any(narrator in query_lower for narrator in self.NARRATOR_NAMES):
            return 'narrator_focused'

        # Thematic/topical query
        if query_lower.startswith(('hadith about', 'what is', 'ruling on', 'how to')):
            return 'contextual_english'

        # Default: hybrid approach
        return 'hybrid'

    def _is_arabic_query(self, query: str) -> bool:
        """Check if query is primarily Arabic script"""
        arabic_chars = sum(1 for c in query if '\u0600' <= c <= '\u06FF')
        total_chars = sum(1 for c in query if c.isalpha())
        return total_chars > 0 and (arabic_chars / total_chars) > 0.5
```

---

## Phase 5: Hybrid Scoring Algorithm

### Implementation (Based on Winning Approach)

```python
class HadithHybridScorer:
    """
    Exact-Term Prioritization approach adapted for hadith search
    Based on Appcircle's 100% win rate methodology
    """

    def calculate_priority_score(
        self,
        result: dict,
        query: str,
        user_terms: List[str],
        query_type: str
    ) -> float:
        """Calculate hybrid priority score for ranking"""

        # Base semantic similarity (from ChromaDB distance)
        semantic_score = 1 - result['distance']

        # Extract metadata
        metadata = result['metadata']
        text_en = metadata['text_en']
        text_ar = metadata['text_ar']
        narrator = metadata['narrator']
        grading = metadata['grading']

        # Separate Arabic and English terms
        arabic_terms = [t for t in user_terms if self._is_arabic(t)]
        english_terms = [t for t in user_terms if not self._is_arabic(t)]

        # ========================================
        # TERM MATCHING BONUSES
        # ========================================

        # 1. Narrator match bonus (highest priority)
        narrator_match_bonus = 0
        if any(term.lower() in narrator.lower() for term in english_terms + arabic_terms):
            narrator_match_bonus = 0.4

        # 2. Arabic term matching
        arabic_matches = sum(1 for term in arabic_terms if term in text_ar)
        arabic_term_bonus = (arabic_matches / len(arabic_terms)) * 0.3 if arabic_terms else 0

        # 3. English term matching
        english_matches = sum(1 for term in english_terms if term.lower() in text_en.lower())
        english_term_bonus = (english_matches / len(english_terms)) * 0.25 if english_terms else 0

        # 4. Overall coverage ratio
        total_matches = arabic_matches + english_matches
        coverage_ratio = total_matches / len(user_terms) if user_terms else 0
        coverage_bonus = coverage_ratio * 0.3

        # ========================================
        # QUALITY BONUSES
        # ========================================

        # 5. Grading boost (Sahih > Hasan > Da'if)
        grading_boost = 0
        if 'sahih' in grading.lower():
            grading_boost = 0.15
        elif 'hasan' in grading.lower():
            grading_boost = 0.10

        # 6. Phrase matching (exact query phrase in text)
        phrase_bonus = 0
        if len(user_terms) > 1:
            query_phrase = ' '.join(user_terms).lower()
            if (query_phrase in text_en.lower()) or (query_phrase in text_ar):
                phrase_bonus = 0.3

        # ========================================
        # FINAL PRIORITY SCORE
        # ========================================

        priority_score = (
            semantic_score * 0.25 +      # Semantic relevance
            narrator_match_bonus +       # Narrator priority
            arabic_term_bonus +          # Arabic term matches
            english_term_bonus +         # English term matches
            coverage_bonus +             # Overall coverage
            grading_boost +              # Authenticity quality
            phrase_bonus                 # Exact phrase match
        )

        return priority_score, {
            'semantic': semantic_score,
            'narrator_bonus': narrator_match_bonus,
            'arabic_bonus': arabic_term_bonus,
            'english_bonus': english_term_bonus,
            'coverage': coverage_ratio,
            'grading_boost': grading_boost,
            'phrase_bonus': phrase_bonus
        }

    def _is_arabic(self, text: str) -> bool:
        """Check if text contains Arabic characters"""
        return any('\u0600' <= c <= '\u06FF' for c in text)
```

---

## Phase 6: Search Interface

### Main Search API

```python
class HadithSearchEngine:
    """Main search interface with routing and hybrid scoring"""

    def __init__(self, vector_db_path: str, sqlite_db_path: str):
        self.vector_manager = HadithVectorManager(vector_db_path)
        self.fts_manager = HadithFTSManager(sqlite_db_path)
        self.router = HadithQueryRouter()
        self.scorer = HadithHybridScorer()

    def search(
        self,
        query: str,
        n_results: int = 5,
        filters: dict = None
    ) -> List[dict]:
        """
        Main search entry point

        Args:
            query: User's search query
            n_results: Number of results to return
            filters: Optional filters (collection, grading, etc.)

        Returns:
            List of ranked hadith results with scores and explanations
        """

        # 1. Classify query
        query_type = self.router.classify(query)

        # 2. Extract user terms
        user_terms = self._extract_user_terms(query)

        # 3. Route to appropriate search method
        if query_type == 'exact_reference':
            return self._exact_reference_search(query, filters)

        elif query_type == 'narrator_focused':
            return self._narrator_focused_search(query, user_terms, n_results, filters)

        else:  # contextual or hybrid
            return self._hybrid_search(query, user_terms, n_results, filters, query_type)

    def _hybrid_search(
        self,
        query: str,
        user_terms: List[str],
        n_results: int,
        filters: dict,
        query_type: str
    ) -> List[dict]:
        """Hybrid search with exact-term prioritization"""

        # Get more results for re-ranking
        raw_results = self.vector_manager.search(
            query,
            n_results=n_results * 4,
            where=filters
        )

        scored_results = []

        for result in raw_results:
            # Calculate priority score
            priority_score, breakdown = self.scorer.calculate_priority_score(
                result, query, user_terms, query_type
            )

            scored_results.append({
                'hadith_num': result['metadata']['hadith_num'],
                'text_ar': result['metadata']['text_ar'],
                'text_en': result['metadata']['text_en'],
                'narrator': result['metadata']['narrator'],
                'grading': result['metadata']['grading'],
                'url': result['metadata']['url'],
                'priority_score': priority_score,
                'score_breakdown': breakdown,
                'explanation': self._explain_ranking(breakdown, user_terms)
            })

        # Sort by priority score
        scored_results.sort(key=lambda x: x['priority_score'], reverse=True)

        return scored_results[:n_results]

    def _explain_ranking(self, breakdown: dict, user_terms: List[str]) -> str:
        """Generate human-readable ranking explanation"""
        if breakdown['phrase_bonus'] > 0:
            return f"🎯 Perfect: Contains your exact phrase"
        elif breakdown['narrator_bonus'] > 0:
            return f"⭐ Excellent: Matches narrator and {breakdown['coverage']*100:.0f}% of terms"
        elif breakdown['coverage'] >= 0.8:
            return f"✅ Good: Contains {breakdown['coverage']*100:.0f}% of your terms"
        elif breakdown['grading_boost'] > 0:
            return f"📚 Relevant: High-quality hadith with semantic match"
        else:
            return f"🔄 Semantic: Similar meaning, different wording"
```

---

## Benchmark & Evaluation

### Test Query Categories

1. **Exact References**
   - "Bukhari 1"
   - "Riyad as-Salihin 680"
   - "Muslim 5629"

2. **Narrator Queries**
   - "hadith from Abu Huraira"
   - "narrated by Aisha"
   - "أبو هريرة" (Arabic)

3. **Thematic Queries**
   - "hadith about forgiveness"
   - "what is the ruling on fasting"
   - "best practices for prayer"

4. **Arabic Queries**
   - "إنما الأعمال بالنيات"
   - "الحياء من الإيمان"

5. **Mixed Queries**
   - "Abu Huraira about charity"
   - "Sahih hadith on patience"

### Evaluation Metrics

```python
metrics = {
    'MRR': 'Mean Reciprocal Rank (for known-item searches)',
    'nDCG': 'Normalized Discounted Cumulative Gain',
    'Term Coverage': 'Percentage of user terms found',
    'Narrator Accuracy': 'Correct narrator filtering rate',
    'Grading Accuracy': 'Authenticity grade correctness',
    'Latency': 'p50, p95, p99 response times',
    'Cross-lingual Success': 'Arabic query → English result accuracy'
}
```

---

## Performance Targets

Based on Appcircle benchmarks, target:

- **Latency**: <50ms p95 for vector search + scoring
- **Accuracy**: >90% relevance for thematic queries
- **Term Preservation**: >70% average term coverage
- **Narrator Match**: 100% accuracy for narrator queries
- **Reference Lookup**: <5ms for exact hadith references

---

## Future Enhancements (Phase 2+)

1. **Query Understanding**
   - NLP-based intent detection
   - Query expansion with Islamic terminology
   - Transliteration handling

2. **Advanced Filtering**
   - Filter by book, chapter, narrator, grading
   - Date range filtering
   - Topic/theme taxonomy

3. **Personalization**
   - User preference for collections
   - Language preference
   - Grading strictness settings

4. **Analytics**
   - Query success tracking
   - Popular searches
   - Failed query analysis

---

## References

- Appcircle Search Implementation: `/Users/ozer/Documents/codes/appcircle-docusaurus/pipeline/`
- Benchmark Report: `Comprehensive_Benchmark_Report_With_Examples.md` (100% win rate)
- Winning Approach: `test_user_term_priority.py:175-243` (Exact-Term Prioritization)
- Query Router: `search_router.py:28-48`

---

**Next Steps:** Begin implementation with Phase 1 (Data Model & Ingestion)
