https://quran.com/2:240/tafsirs/en-tafisr-ibn-kathir

2:240 represents the surah and the ayah number. 

there are 114 ayah in quran so we will count from 1-114 for ayah number

go in 1 surah
start count with 1 and increase the number until you recieve 404. if you reach 404 try again and make sure it is not occur for problem. then move with the next surah. it means the last ayah is ended.

for example: 
- 1:7 last ayah of first surah(Fatihah), 
- 1:8 returns 404
- skip the surah then go with 2:1

## Usage

Run the scraper from the repository root to download Ibn Kathir tafsir data:

```
python quran_scraper/scrape_ibn_kathir.py --rate 1.0
```

Key options:

- `--resume` continues from `checkpoints/quran_tafsir.json` if the job stopped midway.
- `--start-surah` / `--end-surah` limit the scrape range (defaults cover all 114 surahs).
- `--slug` can target another tafsir slug exposed by Quran.com if needed later.
- `--out-dir` and `--raw-dir` override the default `data/quran` and `html/quran` destinations.
- Each JSONL row now includes `text_arabic_simple` and `text_arabic_uthmani`, populated from the page's hidden Arabic verse block when the API payload does not provide it. Reduce `--rate` if you notice throttling; each ayah may trigger both an API and HTML request.
 
