# AnkiDeck

A Python package providing tools to automate the process of creating Anki decks from PDF documents, particularly scanned PDFs. The workflow leverages OCR for text extraction, AI-powered flashcard generation, and automated voice addition via AnkiConnect.

## Quick Start

```bash
# Install the package
pip install -e .

# Extract text from a PDF
extract-text document.pdf

# Fix CSV formatting issues
fix-csv-commas flashcards.csv

# Import csv file into the Anki app

# Add TTS audio to Anki cards
add-tts-general "My French Deck"
```

**Note**: If the commands are not found, you may need to add Python's bin directory to your PATH:
```bash
export PATH="$PATH:/Library/Frameworks/Python.framework/Versions/3.8/bin"
```

## Features

- **OCR Text Extraction**: Extract text from scanned PDFs using Tesseract OCR.
- **Flashcard Generation**: Generate 2-column flashcards using GPT tools.
- **CSV Handling**: Store and fix formatting issues in CSV files for Anki import.
- **Automated TTS**: Add text-to-speech audio to Anki cards using Google TTS and AnkiConnect.
- **Anki Integration**: Seamless import and modification of decks in Anki.

## Workflow

1. **Extract Text**: Use OCR to extract text from PDFs (especially scanned ones).
2. **Chunk Text**: Divide the extracted text into manageable chunks.
3. **Generate Flashcards**: Employ GPT tools to create 2-column flashcards (e.g., French-English pairs). Try our [Anki French Flashcard Generator](https://chatgpt.com/g/g-68fea7868714819183129c8dfac023ce-anki-french-flashcard-generator).
4. **Store in CSV**: Save the flashcards in a CSV file compatible with Anki.
5. **Import to Anki**: Import the CSV into Anki to create the deck.
6. **Add Voice**: Use AnkiDeck commands with AnkiConnect to automatically add TTS audio to cards.
7. **Share Decks**: Share completed decks on AnkiWeb.

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
extract-text document.pdf
fix-csv-commas input.csv output.csv
add-tts-general "My Deck"
```

### Direct Python Execution

You can also run the scripts directly:

```bash
python3 -m ankideck.extract_text document.pdf
python3 -m ankideck.fix_csv_commas input.csv output.csv
python3 -m ankideck.add_tts_general "My Deck"
```

### From Package Directory

If you prefer to run from the package directory:

```bash
cd src/ankideck
python3 extract_text.py document.pdf
python3 fix_csv_commas.py input.csv output.csv
python3 add_tts_general.py "My Deck"
```

### 1. Extract Text from PDF

Run the text extraction script on your PDF:

```bash
extract-text path/to/your/document.pdf [output.txt] [language]
```

- `path/to/your/document.pdf`: Path to the PDF file.
- `output.txt` (optional): Output text file path. Defaults to `document_text.txt`.
- `language` (optional): OCR language code (e.g., `fra` for French). Defaults to `fra`.

This will create a text file with extracted content.

### 2. Generate Flashcards

Divide the extracted text into chunks and use a GPT tool (e.g., ChatGPT or a custom script) to generate 2-column flashcards. Save them in CSV format with columns like "Front" and "Back".

**Recommended**: Try our [Anki French Flashcard Generator](https://chatgpt.com/g/g-68fea7868714819183129c8dfac023ce-anki-french-flashcard-generator) GPT for creating high-quality French flashcards.

### 3. Fix CSV Formatting (if needed)

If your CSV has formatting issues with commas:

```bash
fix-csv-commas input.csv [output.csv]
```

- Keeps the first comma as separator.
- Replaces other commas with semicolons.
- Appends a comma if no separator exists.

### 4. Import to Anki

- Open Anki.
- Go to File > Import.
- Select your CSV file.
- Choose the appropriate deck and field mapping.

### 5. Add Text-to-Speech

Run the TTS addition script:

```bash
add-tts-general <deck_name>
```

Configure the script variables at the top:
- `DECK_NAME`: Name of your Anki deck.
- `FRONT_FIELD`: Field containing the front text to convert to speech.
- `BACK_FIELD`: Field containing the back text to convert to speech.
- `LANG`: Language code for TTS (e.g., "fr" for French).
- Other settings as needed.

The script will add audio to both Front and Back fields of cards that don't already have it. For the Back field, it adds natural pauses between sentences.

### 6. Share on AnkiWeb

Once your deck is ready, sync and share via AnkiWeb.

## Package Overview

The `ankideck` package provides the following command-line tools:

- **`extract-text`**: Performs OCR on PDFs to extract text. Supports multiple languages.
- **`add-tts-general`**: Adds Google TTS audio to both Front and Back fields of Anki cards via AnkiConnect. Supports pauses in Back field audio. Caches audio files to avoid re-generation.
- **`fix-csv-commas`**: Fixes CSV formatting for proper Anki import, handling extra commas in flashcard content.

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
├── fix_csv_commas.py    # CSV formatting utilities
└── add_tts_general.py   # TTS addition functionality
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
- **CSV Import Problems**: Use `fix-csv-commas` to resolve formatting issues.

## Contributing

Contributions are welcome! Please fork the repository and submit pull requests for improvements.

For development:

1. Install in development mode: `pip install -e .`
2. Make your changes to the `src/ankideck/` package
3. Test your changes
4. Submit a pull request

## License

This project is licensed under the MIT License. See LICENSE file for details.