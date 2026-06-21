#!/usr/bin/env python3
"""
Split a PDF into chapters based on a JSON configuration file.

The JSON config should contain:
- pdf: path to the PDF file
- output_dir: directory to save chapter PDFs
- chapters: list of dictionaries with 'name' and 'start' page numbers

Example usage:
    split_pdf chapters.json
"""

import json
import sys
from pathlib import Path
from pypdf import PdfReader, PdfWriter


def load_config(config_path):
    """Load and validate the JSON configuration file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file '{config_path}' not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{config_path}': {e}")
        sys.exit(1)
    
    # Validate required fields
    required_fields = ['pdf', 'output_dir', 'chapters']
    for field in required_fields:
        if field not in config:
            print(f"Error: Missing required field '{field}' in config file.")
            sys.exit(1)
    
    if not config['chapters']:
        print("Error: 'chapters' list is empty.")
        sys.exit(1)
    
    for i, chapter in enumerate(config['chapters']):
        if 'name' not in chapter or 'start' not in chapter:
            print(f"Error: Chapter {i} missing 'name' or 'start' field.")
            sys.exit(1)
    
    return config


def split_pdf(config_path):
    """Split a PDF file into chapters based on the configuration."""
    config = load_config(config_path)
    
    pdf_path = config['pdf']
    output_dir = Path(config['output_dir'])
    chapters = config['chapters']
    
    # Check if PDF exists
    if not Path(pdf_path).exists():
        print(f"Error: PDF file '{pdf_path}' not found.")
        sys.exit(1)
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load the PDF
    try:
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        print(f"PDF has {total_pages} pages")
    except Exception as e:
        print(f"Error reading PDF: {e}")
        sys.exit(1)
    
    # Sort chapters by start page to ensure correct processing
    chapters_sorted = sorted(chapters, key=lambda x: x['start'])
    
    # Process each chapter
    for i, chapter in enumerate(chapters_sorted):
        name = chapter['name']
        start = chapter['start']
        
        # Determine end page
        if i < len(chapters_sorted) - 1:
            end = chapters_sorted[i + 1]['start'] - 1
        else:
            end = total_pages
        
        # Validate page range
        if start < 1 or start > total_pages:
            print(f"Warning: Chapter '{name}' start page {start} is out of range. Skipping.")
            continue
        
        if end > total_pages:
            end = total_pages
        
        # Create a new PDF for this chapter
        writer = PdfWriter()
        
        # Add pages (pypdf uses 0-based indexing internally)
        for page_num in range(start - 1, end):
            writer.add_page(reader.pages[page_num])
        
        # Save the chapter PDF
        output_path = output_dir / f"{name}.pdf"
        try:
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            print(f"Created {output_path} (pages {start}-{end})")
        except Exception as e:
            print(f"Error writing {output_path}: {e}")
            continue
    
    print(f"\nSuccessfully split PDF into {len(chapters_sorted)} chapters in '{output_dir}'")


def main():
    """Main entry point for the split_pdf command."""
    if len(sys.argv) != 2:
        print("Usage: split_pdf <config.json>")
        print("\nExample config.json:")
        print("""{
  "pdf": "book.pdf",
  "output_dir": "chapters",
  "chapters": [
    {"name": "01_CHAPTER_ONE", "start": 1},
    {"name": "02_CHAPTER_TWO", "start": 10},
    {"name": "03_CHAPTER_THREE", "start": 20}
  ]
}""")
        sys.exit(1)
    
    config_path = sys.argv[1]
    split_pdf(config_path)


if __name__ == '__main__':
    main()
