#!/usr/bin/env python3
import os
import re
import json
import fitz  # PyMuPDF
from collections import Counter
from pathlib import Path
import statistics

# --- Configuration ---
INPUT_DIR = Path("sample_dataset/pdfs")
OUTPUT_DIR = Path("sample_dataset/outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# --- Patterns ---
HEADING_PATTERNS = [
    r'^(Chapter|Section|Part)\s+[IVX\d]+',
    r'^[IVX]+\.\s+',
    r'^[A-Z][A-Z\s]{3,}$',    # All-caps headings
    r'^\d+\.\s+[A-Z]',       # Numbered headings
]
FORM_FIELD_PATTERNS = [r'^\d+\.$', r'^S\.No$', r'^Date$', r'^Rs\.?$']
SIGNATURE_KEYWORDS = ['signature','date','signed','authorized','stamp','seal']

# --- Utility Functions ---
def clean_text(text: str) -> str:
    """Normalize whitespace"""
    return re.sub(r'\s+', ' ', text.strip())

def strip_serial(text: str) -> str:
    """Remove leading serial numbering"""
    return re.sub(r'^\d+[\.|\)]\s*', '', text)

def is_form_field(text: str) -> bool:
    """Exclude generic form labels"""
    for pat in FORM_FIELD_PATTERNS:
        if re.match(pat, text.strip(), re.IGNORECASE):
            return True
    return False

def is_signature_area(text: str) -> bool:
    """Exclude signature/legal area"""
    low = text.lower()
    return any(kw in low for kw in SIGNATURE_KEYWORDS)

# --- Font Detection ---
def detect_fonts(doc):
    """
    Determine title font (largest on page1) and body font (most common)
    """
    sizes, title_font = [], 0.0
    # page 1 spans
    for block in doc[0].get_text('dict')['blocks']:
        for line in block.get('lines', []):
            for span in line.get('spans', []):
                txt = span['text'].strip()
                sz = span['size']
                if txt and sz > title_font:
                    title_font = sz
    # all spans for body
    for page in doc:
        for block in page.get_text('dict')['blocks']:
            for line in block.get('lines', []):
                for span in line.get('spans', []):
                    if span['text'].strip():
                        sizes.append(round(span['size'], 1))
    body_font = Counter(sizes).most_common(1)[0][0] if sizes else title_font * 0.6
    return title_font, body_font

# --- Heading Classifier ---
def classify_heading(text, size, tfont, bfont):
    txt = clean_text(text)
    # filters
    if not txt or is_form_field(txt) or is_signature_area(txt):
        return False, None
    # H1: very large text
    if size >= tfont * 0.9:
        return True, 'H1'
    # H2: regex patterns or moderately large
    for pat in HEADING_PATTERNS:
        if re.match(pat, txt):
            return True, 'H2'
    if size >= bfont * 1.3:
        return True, 'H2'
    # H3: simple numbered items
    if re.match(r'^\d+\.?\s+', txt):
        return True, 'H3'
    return False, None

# --- Extraction ---
def extract_structure(pdf_path):
    doc = fitz.open(str(pdf_path))
    tfont, bfont = detect_fonts(doc)
    result = {'title': '', 'outline': []}
    seen = set()

    for page_no, page in enumerate(doc, start=1):
        for block in page.get_text('dict')['blocks']:
            for line in block.get('lines', []):
                text = ''.join(span['text'] for span in line.get('spans', [])).strip()
                if not text:
                    continue
                size = max((span['size'] for span in line.get('spans', [])), default=bfont)
                is_h, level = classify_heading(text, size, tfont, bfont)
                if not is_h:
                    continue
                clean = clean_text(strip_serial(text))
                key = (level, clean.lower(), page_no)
                if key in seen:
                    continue
                seen.add(key)
                if level == 'H1' and not result['title']:
                    result['title'] = clean
                else:
                    result['outline'].append({'level': level, 'text': clean, 'page': page_no})

    if not result['title']:
        result['title'] = Path(pdf_path).stem
    doc.close()
    return result

# --- Main ---
def main():
    for pdf in INPUT_DIR.glob('*.pdf'):
        print(f"Processing {pdf.name}...")
        try:
            data = extract_structure(pdf)
            out_file = OUTPUT_DIR / f"{pdf.stem}.json"
            with open(out_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"Saved: {out_file.name} (Title: {data['title']}, Headings: {len(data['outline'])})")
        except Exception as e:
            print(f"Error processing {pdf.name}: {e}")

if __name__ == '__main__':
    main()
