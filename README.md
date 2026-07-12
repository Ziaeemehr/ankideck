# AnkiDeck

A Python package providing tools to automate the process of creating Anki decks from PDF documents, particularly scanned PDFs. The workflow leverages OCR for text extraction, AI-powered flashcard generation, and automated voice addition via AnkiConnect.

## ⚠️ Important Warning

**ALWAYS backup your Anki decks before running any script that modifies them!**

To backup your Anki collection:
1. Open Anki
2. Go to **File > Export**
3. Select **"Anki Collection Package"** (*.colpkg)
4. Include all decks and save to a safe location

This is especially important before running the `add_tts` command, which modifies existing cards by adding audio fields, and the `import_to_anki` command, which creates new decks or may modify existing ones if they have the same name.

## Quick Start

```bash
# Install the package
pip install -e .

# Split a PDF into chapters by page numbers
split_pdf chapters.json

# Extract text from a PDF (for scanned PDFs)
extract_text document.pdf

# Fix CSV formatting issues
fix_format flashcards.csv

# Import CSV files to Anki as .apkg files
import_to_anki ./csv

# Add TTS audio to Anki cards (keep Anki open with AnkiConnect installed)
# Option 1: Both fields with gTTS (free)
add_tts "My French Deck"

# Option 2: Front with ElevenLabs, Back with gTTS (recommended)
add_tts "My French Deck" elevenlabs gtts
```

**Note**: If the commands are not found, you may need to add Python's bin directory to your PATH:
```bash
export PATH="$PATH:/Library/Frameworks/Python.framework/Versions/3.8/bin"
```

## Features

- **PDF Splitting**: Split large PDFs into chapters based on page numbers (works with scanned PDFs).
- **OCR Text Extraction**: Extract text from scanned PDFs using Tesseract OCR.
- **Flashcard Generation**: Generate 2-column flashcards using GPT tools.
- **CSV Handling**: Store and fix formatting issues in CSV files for Anki import.
- **Deck Import**: Convert CSV files to Anki deck packages (.apkg files).
- **Automated TTS**: Add text-to-speech audio to Anki cards using Google TTS and AnkiConnect.
- **Anki Integration**: Seamless import and modification of decks in Anki.

## Workflow

1. **(Optional) Split PDF**: If you have a large PDF, split it into chapters by page numbers.
2. **Extract Text**: Use OCR to extract text from PDFs (especially scanned ones).
3. **Chunk Text**: Divide the extracted text into manageable chunks.
4. **Generate Flashcards**: Employ GPT tools to create 2-column flashcards (e.g., French-English pairs). Try our [Anki French Flashcard Generator](https://chatgpt.com/g/g-68fea7868714819183129c8dfac023ce-anki-french-flashcard-generator).
5. **Store in CSV**: Save the flashcards in CSV file(s) compatible with Anki.
6. **Import to Anki**: Use `import_to_anki` to create .apkg file(s), then import into Anki.
7. **Add Voice**: Use `add_tts` command with AnkiConnect to automatically add TTS audio to cards.
8. **Share Decks**: Share completed decks on AnkiWeb.

## PDF → Hierarchical Anki Deck (Excel-based)

For building a single `.apkg` with one subdeck per chapter (e.g. a textbook), the recommended workflow uses Excel instead of CSV:

1. Extract vocab/phrases per chapter into an `.xlsx` file (columns like `French`, `English`, `Persian`, `Example`).
2. Read each chapter's xlsx with `read_cards_excel(...)` from `ankideck.reader`.
3. Generate/cache TTS audio with `make_tts(...)` from `ankideck.tts`.
4. Build one `genanki.Deck` per chapter (named `f"{PARENT}::{title}"`) and bundle them into a single `genanki.Package` → one `.apkg`.

Other input formats (CSV, Excel, etc.) are supported the same way — just point the appropriate reader at your file and follow the same card → deck → package steps.

See [PDF_TO_ANKI_PIPELINE.md](PDF_TO_ANKI_PIPELINE.md) for the full step-by-step pipeline (chapter detection, page rendering, xlsx extraction conventions, deck-ordering tips, etc.).

## Prerequisites

- Python 3.8+
- [Anki](https://apps.ankiweb.net/) with [AnkiConnect](https://ankiweb.net/shared/info/2055492159) plugin installed and running.
- Tesseract OCR installed (`brew install tesseract` on macOS, or equivalent for your OS).
- Access to GPT tools (e.g., OpenAI API for flashcard generation).

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd AnkiDecks_develop
   ```

2. Install the package and its dependencies:
   ```bash
   pip install -e .
   ```

3. Ensure AnkiConnect is running in Anki (default port 8765).

## Usage

### Command Line (Recommended)

After installation, use the console scripts from anywhere:

```bash
split_pdf chapters.json
extract_text document.pdf       # [Optional]
fix_format input.csv output.csv # [Optional]
import_to_anki ./csv
add_tts "My Deck"
```

### Direct Python Execution

You can also run the scripts directly:

```bash
python3 -m ankideck.extract_text document.pdf
python3 -m ankideck.fix_format input.csv output.csv
python3 -m ankideck.add_tts "My Deck"
```

### From Package Directory

If you prefer to run from the package directory:

```bash
cd src/ankideck
python3 extract_text.py document.pdf
python3 fix_format.py input.csv output.csv
python3 add_tts.py "My Deck"
```

### 1. Split PDF into Chapters (Optional)

If you have a large PDF (like a textbook) that you want to split into separate chapter files based on page numbers:

```bash
split_pdf chapters.json
```

Create a JSON configuration file (e.g., `chapters.json`) with this format:

```json
{
  "pdf": "book.pdf",
  "output_dir": "chapters",
  "chapters": [
    {"name": "01_CHAPTER_ONE", "start": 8},
    {"name": "02_CHAPTER_TWO", "start": 14},
    {"name": "03_CHAPTER_THREE", "start": 18}
  ]
}
```

- `pdf`: Path to your PDF file
- `output_dir`: Directory where chapter PDFs will be saved
- `chapters`: List of chapters with names and starting page numbers
- The script automatically calculates end pages based on the next chapter's start

**Note**: Works with both regular and scanned PDFs. No text reading required - purely page-based splitting.

### 2. Extract Text from PDF

Run the text extraction script on your PDF:

```bash
extract_text path/to/your/document.pdf [output.txt] [language]
```

- `path/to/your/document.pdf`: Path to the PDF file.
- `output.txt` (optional): Output text file path. Defaults to `document_text.txt`.
- `language` (optional): OCR language code (e.g., `fra` for French). Defaults to `fra`.

This will create a text file with extracted content.

### 3. Generate Flashcards

Divide the extracted text into chunks and use a GPT tool (e.g., ChatGPT or a custom script) to generate 2-column flashcards. Save them in CSV format with columns like "Front" and "Back".

**Recommended**: Try our [Anki French Flashcard Generator](https://chatgpt.com/g/g-68fea7868714819183129c8dfac023ce-anki-french-flashcard-generator) GPT for creating high-quality French flashcards.

### 4. Fix CSV Formatting (if needed)

If your CSV has formatting issues with delimiters:

```bash
fix_format input.csv [output.csv]
```

- By default, keeps the first comma as separator and replaces others with semicolons.
- Supports flexible delimiter handling with `--find` and `--replace` options.
- Appends a delimiter if no separator exists to ensure proper column structure.

### 5. Import CSV to Anki (Two Options)

#### Option A: Generate .apkg file (Recommended)

Create an Anki package file from your CSV files:

```bash
import_to_anki <csv_folder_path> [output_file.apkg]
```

**Examples:**
```bash
# Create anki_deck.apkg from all CSV files in ./csv folder
import_to_anki ./csv

# Create custom_deck.apkg from CSV files
import_to_anki ./csv my_french_deck.apkg
```

**Features:**
- Processes all CSV files in the specified folder
- Each CSV file becomes a separate deck
- CSV files should be tab-separated with "Front" and "Back" columns (or just two columns)
- Creates a single .apkg file that you can import directly into Anki
- No need to have Anki running

**To import the .apkg file:**
1. Open Anki
2. Go to File > Import
3. Select the generated .apkg file

#### Option B: Manual CSV Import

- Open Anki.
- Go to File > Import.
- Select your CSV file.
- Choose the appropriate deck and field mapping.

### 6. Add Text-to-Speech

> **⚠️ WARNING**: Before running `add_tts`, backup your Anki collection! Go to **File > Export > Anki Collection Package** in Anki. This command modifies existing cards by adding audio fields.

Add high-quality audio to your Anki cards using Google TTS (gTTS) or ElevenLabs:

#### Basic Usage

```bash
add_tts <deck_name> [front_engine] [back_engine] [elevenlabs_api_key_file]
```

**Arguments:**
- `deck_name` (required): Name of your Anki deck
- `front_engine` (optional): `gtts` or `elevenlabs` (default: `gtts`)
- `back_engine` (optional): `gtts`, `elevenlabs`, or `none` (default: `gtts`)
- `elevenlabs_api_key_file` (optional): Path to ElevenLabs API key file

#### TTS Engine Options

**gTTS (Google Text-to-Speech)**
- ✅ Free and unlimited
- ✅ Good quality for most purposes
- ✅ Automatically handles mixed text (skips Farsi/Persian text naturally)
- ⚠️ Requires internet connection

**ElevenLabs**
- ✅ Premium voice quality
- ✅ More natural intonation
- ✅ Automatically filters out Farsi/Persian text before generation
- ⚠️ Requires API key and credits (paid service)
- 💡 Best for important/front-facing content

#### Common Use Cases

**1. Both fields with gTTS (most economical):**
```bash
add_tts "My French Deck"
```

**2. Front with ElevenLabs, Back with gTTS (recommended - best quality/cost balance):**
```bash
add_tts "My French Deck" elevenlabs gtts
```
This is ideal when you want high-quality audio for the main content (Front) but save costs on explanations (Back).

**3. Only Front field with ElevenLabs:**
```bash
add_tts "My French Deck" elevenlabs none
```

**4. Both fields with ElevenLabs (highest quality):**
```bash
add_tts "My French Deck" elevenlabs elevenlabs
```

**5. Custom ElevenLabs API key path:**
```bash
add_tts "My French Deck" elevenlabs gtts "/path/to/your/api_key.txt"
```

#### Features

- ✅ Adds audio to Front and Back fields separately
- ✅ Automatically skips cards that already have audio
- ✅ Adds natural pauses between sentences in Back field
- ✅ Caches generated audio to avoid regeneration
- ✅ Automatically removes Farsi/Persian text when using ElevenLabs
- ✅ Progress bar shows generation status
- ✅ Independent engine selection for Front and Back fields

#### Setup for ElevenLabs

1. Sign up at [ElevenLabs](https://elevenlabs.io/)
2. Get your API key from the dashboard
3. Save it to a text file (e.g., `~/elevenlabs_api_key.txt`)
4. Use the path as the 4th argument or place it at the default location:
   `/Users/tng/Projects/Language/FR/Anki_decks/elevenlabs_api_key.txt`

#### Notes

- Ensure Anki is running with AnkiConnect enabled
- The script processes cards that don't already have `[sound:]` tags
- For Back fields, sentences are automatically split and paused for better comprehension
- Cached audio files are stored in `tts_cache_{deck_name}/` directory

### 6. Share on AnkiWeb

Once your deck is ready, sync and share via AnkiWeb.

## Complete Example Workflow

Here's a complete example of processing a French textbook:

```bash
# 1. Split the PDF textbook into chapters (optional)
# First, create a chapters.json file with your chapter definitions
split_pdf chapters.json
# Output: Creates separate PDF files in the 'chapters' folder

# 2. Extract text from each chapter (for scanned PDFs)
extract_text chapters/01_PRESENTATIONS_ET_USAGES.pdf chapter01.txt fra

# 3. Use ChatGPT to generate flashcards from the text
# Copy chapter01.txt content and use the Anki French Flashcard Generator
# Save the output as chapter01.csv in the 'csv' folder

# 4. Fix CSV formatting if needed
fix_format csv/chapter01.csv csv/chapter01_fixed.csv

# 5. Import all CSV files to create Anki deck package
import_to_anki ./csv french_textbook.apkg

# 6. Import the .apkg file into Anki (manually)
# Open Anki > File > Import > Select french_textbook.apkg

# 7. Add TTS audio to your cards (requires Anki to be running)
add_tts "chapter01" elevenlabs gtts
```

## Package Overview

The `ankideck` package provides the following command-line tools:

- **`split_pdf`**: Splits large PDFs into chapters based on page numbers. Works with scanned PDFs.
- **`extract_text`**: Performs OCR on PDFs to extract text. Supports multiple languages.
- **`fix_format`**: Fixes CSV formatting for proper Anki import, handling delimiter issues in flashcard content with flexible character replacement options.
- **`import_to_anki`**: Converts CSV files into Anki deck packages (.apkg files). Processes all CSV files in a folder and creates individual decks.
- **`add_tts`**: Adds TTS audio to Anki cards using Google TTS (free) or ElevenLabs (premium). Supports independent engine selection for Front and Back fields, automatic Farsi text filtering for ElevenLabs, natural pauses in Back field audio, and audio caching to avoid re-generation.

## Resources

- **[Anki French Flashcard Generator](https://chatgpt.com/g/g-68fea7868714819183129c8dfac023ce-anki-french-flashcard-generator)**: Custom GPT for generating high-quality French flashcards from text
- **[Anki](https://apps.ankiweb.net/)**: Free flashcard software
- **[AnkiConnect](https://ankiweb.net/shared/info/2055492159)**: Anki plugin for external integrations
- **[Tesseract OCR](https://github.com/tesseract-ocr/tesseract)**: OCR engine for text extraction

## Development

The package is structured as follows:

```
src/ankideck/
├── __init__.py          # Package initialization
├── extract_text.py      # OCR text extraction
├── fix_format.py        # CSV formatting utilities
└── add_tts.py           # TTS addition functionality
```

To extend the package:

1. Add new modules to `src/ankideck/`
2. Update `pyproject.toml` to include new console scripts if needed
3. Add tests and documentation

## Configuration

- Update script variables as needed (e.g., deck names, languages).
- Ensure AnkiConnect is accessible at `http://localhost:8765`.
- For GPT flashcard generation, integrate with your preferred AI tool.

## Troubleshooting

- **OCR Issues**: Ensure Tesseract is installed and the correct language pack is available.
- **AnkiConnect Errors**: Verify Anki is running with AnkiConnect enabled.
- **TTS Failures**: Check internet connection for Google TTS.
- **CSV Import Problems**: Use `fix_format` to resolve delimiter formatting issues.

## Contributing

Contributions are welcome! Please fork the repository and submit pull requests for improvements.

For development:

1. Install in development mode: `pip install -e .`
2. Make your changes to the `src/ankideck/` package
3. Test your changes
4. Submit a pull request

## License

This project is licensed under the MIT License. See LICENSE file for details.