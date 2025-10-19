# Hadith Data Structure

This document outlines the structure of the JSON objects found in the `book_1.jsonl` file. Each line in the file is a self-contained JSON object representing a single hadith.

## Fields

- `collection_slug` (string): A unique identifier for the hadith collection.
  - Example: `"riyadussalihin"`
- `collection_name` (string): The name of the hadith collection in both Arabic and English.
  - Example: `"رياض الصالحين Riyad as-Salihin"`
- `book_id` (string): The identifier for the book within the collection.
  - Example: `"1"`
- `book_title_en` (string): The English title of the book.
  - Example: `"The Book of Good Manners"`
- `book_title_ar` (string): The Arabic title of the book.
  - Example: `"كتاب الأدب"`
- `chapter_id` (string): A unique identifier for the chapter.
  - Example: `"C84.00"`
- `chapter_number_en` (string): The chapter number in English.
  - Example: `"(84)"`
- `chapter_number_ar` (string): The chapter number in Arabic.
  - Example: `"(84)"`
- `chapter_title_en` (string): The English title of the chapter.
  - Example: `"Exaltation of Modesty"`
- `chapter_title_ar` (string): The Arabic title of the chapter.
  - Example: `"-باب الحياء وفضله والحث على التخلق به"`
- `hadith_id_site` (string): A unique identifier for the hadith on the source website.
  - Example: `"h1706760"`
- `hadith_num_global` (string): The global hadith number in the collection.
  - Example: `"Riyad as-Salihin 680"`
- `hadith_num_in_book` (string): The hadith number within the book.
  - Example: `"Book 1, Hadith 1"`
- `texts` (array of objects): An array containing the hadith text in different languages.
  - `language` (string): The language of the text (e.g., "en", "ar").
  - `content` (string): The hadith text.
- `narrator` (string): The narrator of the hadith.
  - Example: `"Ibn 'Umar (May Allah be pleased with them) reported:"`
- `grading` (array): An array containing grading information for the hadith (can be empty).
- `references` (array of objects): An array of reference information.
  - `label` (string): The type of reference (e.g., "Reference", "In-book reference").
  - `value` (string): The reference value.
- `topics` (array): An array of topics related to the hadith (can be empty).
- `footnotes` (array): An array of footnotes for the hadith (can be empty).
- `source_url` (string): The URL of the hadith on the original website.
  - Example: `"https://sunnah.com/riyadussalihin/1#h1706760"`
- `scraped_at` (string): The timestamp (UTC) when the hadith was scraped.
  - Example: `"2025-10-08T18:04:11.520659Z"`
- `checksum` (string): A SHA256 checksum of the hadith data.
  - Example: `"5890d21b341fc0c1b2052b513e4efd6f5a1d0c436695235dbeb23b8e1bd1a1ce"`

## Example

```json
{"collection_slug":"riyadussalihin","collection_name":"رياض الصالحين Riyad as-Salihin","book_id":"1","book_title_en":"The Book of Good Manners","book_title_ar":"كتاب الأدب","chapter_id":"C84.00","chapter_number_en":"(84)","chapter_number_ar":"(84)","chapter_title_en":"Exaltation of Modesty","chapter_title_ar":"-باب الحياء وفضله والحث على التخلق به","hadith_id_site":"h1706760","hadith_num_global":"Riyad as-Salihin 680","hadith_num_in_book":"Book 1, Hadith 1","texts":[{"language":"en","content":"Ibn 'Umar (May Allah be pleased with them) reported: Messenger of Allah (ﷺ) passed by a man of the Ansar who was admonishing his brother regarding shyness. Messenger of Allah (ﷺ) said, "Leave him alone, for modesty is a part of Iman." [Al-Bukhari and Muslim] ."},{"language":"ar","content":"وعن ابن عمر رضي الله عنهما أن رسول الله صلى الله عليه وسلم مر على رجل من الأنصار وهو يعظ أخاه في الحياء، فقال رسول الله صلى الله عليه وسلم‏:‏ "دعه فإن الحياء من الإيمان" ‏(‏‏(‏متفق عليه‏)‏‏)‏ ‏.‏"}],"narrator":"Ibn 'Umar (May Allah be pleased with them) reported:","grading":[],"references":[{"label":"Reference","value":"Riyad as-Salihin 680"},{"label":"In-book reference","value":"Book 1, Hadith 1"}],"topics":[],"footnotes":[],"source_url":"https://sunnah.com/riyadussalihin/1#h1706760","scraped_at":"2025-10-08T18:04:11.520659Z","checksum":"5890d21b341fc0c1b2052b513e4efd6f5a1d0c436695235dbeb23b8e1bd1a1ce"}
```
