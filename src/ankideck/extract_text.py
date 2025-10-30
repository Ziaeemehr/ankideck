# Replacing file contents with a clean, serial OCR script
import sys
import os
import pytesseract
from tqdm import tqdm
from pdf2image import convert_from_path


def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_text.py <pdf_path> [output_text_path] [lang]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if len(sys.argv) >= 3:
        output_text_path = sys.argv[2]
    else:
        name = os.path.basename(pdf_path).rsplit('.', 1)[0]
        output_text_path = f"{name}_text.txt"

    lang = sys.argv[3] if len(sys.argv) >= 4 else "fra"

    try:
        images = convert_from_path(pdf_path)
        text_parts = []
        for img in tqdm(images, desc="OCR pages", unit="page", total=len(images)):
            text_parts.append(pytesseract.image_to_string(img, lang=lang))

        text = "\n\n".join(text_parts)
        with open(output_text_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Text extraction complete. Saved to {output_text_path}.")
    except Exception as e:
        print("OCR failed:", e)
        sys.exit(2)


if __name__ == "__main__":
    main()