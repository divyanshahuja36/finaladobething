import fitz  # PyMuPDF
import re
from collections import Counter

# --- Configuration Constants ---
# Ignore text within this pixel margin from the top/bottom of the page
HEADER_FOOTER_MARGIN = 50
# Chunks must have at least this many characters to be considered meaningful
MIN_PARAGRAPH_LENGTH = 40


def is_likely_heading(span: dict, body_font_size: float) -> bool:
    """
    Determines if a given text span is likely part of a heading.
    Heuristics: larger font size, bold weight, or all-caps.

    Args:
        span (dict): A span dictionary from PyMuPDF's get_text("dict").
        body_font_size (float): The most common font size in the document.

    Returns:
        bool: True if the span is likely a heading, False otherwise.
    """
    if not span['text'].strip():
        return False

    font_size = span['size']
    # In PyMuPDF, the bold flag is bit 4 of the font flags
    is_bold = span['flags'] & 2**4
    is_larger = font_size > body_font_size * 1.15
    is_all_caps = span['text'].isupper() and len(span['text']) > 4

    # A short line that is bold or significantly larger is very likely a heading
    if (is_bold or is_larger or is_all_caps) and len(span['text'].split()) < 12:
        # Extra check to avoid flagging list items that start with a bold word
        if not span['text'].strip().endswith('.'):
            return True

    return False


def clean_text(text: str) -> str:
    """
    Cleans up text by removing extra whitespace, line breaks, and common PDF artifacts.

    Args:
        text (str): The raw text to clean.

    Returns:
        str: The cleaned text.
    """
    # Attempt to de-hyphenate words broken across lines
    text = text.replace('-\n', '').replace('\n', ' ').strip()
    # Collapse multiple whitespace characters into a single space
    text = re.sub(r'\s+', ' ', text)
    return text


def parse_pdf_to_chunks(pdf_path: str, doc_filename: str) -> list[dict]:
    """
    Parses a PDF into structured chunks, with improved logic for identifying
    headings, merging paragraphs, and filtering out noise like headers/footers.

    Args:
        pdf_path (str): The file path to the PDF document.
        doc_filename (str): The name of the document for metadata.

    Returns:
        list[dict]: A list of structured text chunks.
    """
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"ERROR: Could not open or read {pdf_path}: {e}")
        return []

    # 1. Analyze font sizes to determine the most common (body) font size
    font_counts = Counter()
    for page in doc:
        for block in page.get_text("dict", flags=0)["blocks"]:
            if block["type"] == 0:  # Text block
                for line in block["lines"]:
                    for span in line["spans"]:
                        font_counts[round(span["size"])] += 1

    body_font_size = font_counts.most_common(1)[0][0] if font_counts else 10.0

    # 2. Process the document to extract structured chunks
    chunks = []
    # Default title until a heading is found
    current_section_title = "Introduction"
    current_paragraph_texts = []

    for page_num, page in enumerate(doc):
        page_height = page.rect.height
        blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT)["blocks"]

        # Keep track of the page number where the current paragraph started
        if page_num > 0 and current_paragraph_texts:
            paragraph_start_page = page_num
        else:
            paragraph_start_page = page_num + 1

        for block in blocks:
            if block["type"] != 0:  # Skip non-text blocks
                continue

            # Filter out headers and footers based on vertical position
            block_bbox = block["bbox"]
            if block_bbox[1] < HEADER_FOOTER_MARGIN or block_bbox[3] > page_height - HEADER_FOOTER_MARGIN:
                continue

            block_text = "".join(span["text"] for line in block.get(
                "lines", []) for span in line.get("spans", [])).strip()
            if not block_text or block_text.isdigit():
                continue

            # Check if the block is a heading using the first text span
            first_span = block.get("lines", [{}])[0].get("spans", [{}])[0]
            if first_span and is_likely_heading(first_span, body_font_size):
                # A heading is found. Finalize the previous paragraph and save it as a chunk.
                if current_paragraph_texts:
                    text_content = clean_text(
                        " ".join(current_paragraph_texts))
                    if len(text_content) >= MIN_PARAGRAPH_LENGTH:
                        chunks.append({
                            "document": doc_filename,
                            "page_number": paragraph_start_page,
                            "section_title": current_section_title,
                            "text": text_content
                        })

                # Start a new section with the found heading
                current_section_title = clean_text(block_text)
                current_paragraph_texts = []
                paragraph_start_page = page_num + 1
            else:
                # This is a content block, so append its text to the current paragraph
                current_paragraph_texts.append(block_text)

    # After the last page, save any remaining paragraph content
    if current_paragraph_texts:
        text_content = clean_text(" ".join(current_paragraph_texts))
        if len(text_content) >= MIN_PARAGRAPH_LENGTH:
            chunks.append({
                "document": doc_filename,
                "page_number": paragraph_start_page,
                "section_title": current_section_title,
                "text": text_content
            })

    print(f"INFO: Extracted {len(chunks)} chunks from {doc_filename}.")
    return chunks
