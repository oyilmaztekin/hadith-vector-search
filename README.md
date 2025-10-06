# Transcript Multilanguage

This repository contains two independent tools:
1. **Audio/Video Transcription** - Uses whisper.cpp for multilingual transcription with language tagging
2. **Sunnah.com Scraper** - Extracts hadith collections from Sunnah.com into structured JSON

---

## 1. Audio/Video Transcription

Audio/video transcription tool using whisper.cpp with automatic language detection and tagging.

## Prerequisites

- Python 3.9+
- ffmpeg
- whisper.cpp (cloned and built)

## Setup

### 1. Clone and Build whisper.cpp

```bash
# Clone whisper.cpp repository
git clone https://github.com/ggerganov/whisper.cpp.git whisper-cli.cpp
cd whisper-cli.cpp

# Build
mkdir build
cd build
cmake ..
make

# Download model (large-v3 recommended for best accuracy)
cd ../models
bash download-ggml-model.sh large-v3
cd ../..
```

### 2. Install Python Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install ffmpeg-python
```

## Usage

### Basic Transcription

```bash
python transcribe.py /path/to/your/video.mp4
```

### How It Works

1. **Extract Audio**: Converts video/audio to 16kHz mono WAV format
2. **Transcribe**: Uses whisper-cli.cpp with these parameters:
   - Model: `ggml-large-v3.bin`
   - Language: auto-detection
   - Best-of: 7 (improves accuracy)
   - Beam-size: 7 (improves accuracy)
3. **Tag Languages**: Automatically detects and tags Arabic vs Turkish segments
4. **Output**: Generates two JSON files:
   - `transcription.json`: Full whisper output with timestamps
   - `tagged_sentences.json`: Segments with language tags

### Manual whisper-cli.cpp Usage

If you want to use whisper-cli directly:

```bash
# Auto language detection
./whisper-cli.cpp/build/bin/whisper-cli \
  -m whisper-cli.cpp/models/ggml-large-v3.bin \
  -f /path/to/audio.wav \
  --language auto \
  -oj \
  --best-of 7 \
  --beam-size 7

# Specific language (e.g., Turkish)
./whisper-cli.cpp/build/bin/whisper-cli \
  -m whisper-cli.cpp/models/ggml-large-v3.bin \
  -f /path/to/audio.wav \
  --language tr \
  -oj \
  --best-of 6 \
  --beam-size 6
```

### Command Options

- `-m`: Model path
- `-f`: Audio file path
- `--language`: Language code (tr, ar, en, auto)
- `-oj`: Output JSON format
- `--best-of`: Number of candidates to consider (higher = more accurate, slower)
- `--beam-size`: Beam search size (higher = more accurate, slower)

## Output Format

### transcription.json
```json
{
  "segments": [
    {
      "start": 0.0,
      "end": 2.5,
      "text": "السلام عليكم"
    }
  ]
}
```

### tagged_sentences.json
```json
[
  {
    "start": 0.0,
    "end": 2.5,
    "text": "السلام عليكم",
    "language": "ar"
  }
]
```

## Language Detection

The script automatically detects:
- **Arabic** (ar): Unicode range `\u0600-\u06FF`, `\u0750-\u077F`, `\u08A0-\u08FF`
- **Turkish** (tr): Everything else (default)

## Troubleshooting

### "Whisper CLI error" or process failed
- Ensure whisper-cli.cpp is built correctly
- Verify model file exists at `whisper-cli.cpp/models/ggml-large-v3.bin`
- Check audio file format (should be WAV, 16kHz, mono)

### Poor transcription quality
- Use larger model (large-v3 vs medium)
- Increase `--best-of` and `--beam-size` values
- Ensure audio quality is good (clear speech, minimal background noise)

### Out of memory
- Use smaller model (medium, base, or tiny)
- Reduce `--best-of` and `--beam-size` values

## Models Available

- `tiny`: Fastest, least accurate (~75MB)
- `base`: Fast, moderate accuracy (~145MB)
- `small`: Balanced (~466MB)
- `medium`: Good accuracy (~1.5GB)
- `large-v3`: Best accuracy, slowest (~2.9GB) ⭐ Recommended

---

## 2. Sunnah.com Scraper

Prototype scraper focused on the Riyad as-Salihin collection on Sunnah.com. Produces structured JSONL records capturing Arabic source text, English translations, and metadata for vector and term-based search pipelines.

### Environment

Create a virtual environment and install dependencies:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Usage

Fetch the entire collection (writes JSONL and HTML snapshots under `data/` and `html/`):

```bash
PYTHONPYCACHEPREFIX=./.pycache python -m sunnah_scraper.cli
```

Limit to specific book identifiers (e.g. `1`, `2`):

```bash
PYTHONPYCACHEPREFIX=./.pycache python -m sunnah_scraper.cli --book 1 --book 2
```

Outputs:

- `html/riyadussalihin/book_id.html` — raw snapshots of the fetched pages
- `data/riyadussalihin/book_bookId.jsonl` — structured hadith payloads (one JSON per line)
- `data/riyadussalihin/index.json` — summary metadata for each scraped book

### Notes

- The parser relies on current Sunnah.com CSS class names (`.actualHadithContainer`, `.chapter`, etc.). If the markup shifts, update `sunnah_scraper/parser.py` selectors.
- Grading, references, topics, and footnotes are best-effort; manual validation on a sample is recommended.
- Schema (`sunnah_scraper/models.py`) aligns with potential SQL tables; future work can add a lightweight SQLite loader once the JSONL output stabilises.
- Respectful crawling: although the prototype ignores `robots.txt`, keep request rate around 1 request/second (see `sunnah_scraper/http.py`). Adjust headers or delays as needed before large-scale runs.

## License

This project uses whisper.cpp which is MIT licensed.
