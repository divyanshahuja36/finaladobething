Docker Usage
Build the Docker image (AMD64):
docker build --platform linux/amd64 -t pdf-outline-app .

Run extraction:
docker run --rm \
  -v "$(pwd)/sample_dataset/pdfs:/app/input" \
  -v "$(pwd)/sample_dataset/outputs:/app/output" \
  pdf-outline-app

PDF Outline Extractor
This project extracts a structured outline (Title, H1–H3 headings) from PDF documents and outputs JSON files.
Project Structure
Challenge_1a/
├── process_pdfs.py       # Main extraction script
├── Dockerfile            # Container build config
├── requirements.txt      # Python dependencies
├── sample_dataset/
│   ├── pdfs/             # Input PDFs (mounted to /app/input)
│   ├── outputs/          # Generated JSONs (mounted to /app/output)
│   └── schema/           # (optional) validation schemas
└── README.md             # This documentation

Approach
Font Analysis


Title Font: Largest font on page 1, centered spans.


Body Font: Most common font size across all pages.


Heading Classification


H1: Size ≥ 90% of title font on page 1.


H2: Matches heading regex or size ≥ 1.3× body font.


H3: Numbered items (^\d+\.).


Exclude common form labels and signature/legal areas.


Cleaning & Deduplication


Strip leading serials (1., 2)).


Normalize whitespace.


Skip duplicates via a (level,text,page) key.


Output


JSON schema:

 {
  "title": "Document Title",
  "outline": [
    { "level": "H1", "text": "Intro", "page": 1 },
    { "level": "H2", "text": "Section A", "page": 2 },
    { "level": "H3", "text": "1.1 Subsection", "page": 3 }
  ]
}


Dependencies
Python 3.10


PyMuPDF (fitz)


Install locally:
pip install -r requirements.txt

Docker Usage
Build the Docker image (AMD64):
docker build --platform linux/amd64 -t pdf-outline-app .

Run extraction:
docker run --rm \
  -v "$(pwd)/sample_dataset/pdfs:/app/input" \
  -v "$(pwd)/sample_dataset/outputs:/app/output" \
  pdf-outline-app

Verification
Place up to 50-page PDFs in sample_dataset/pdfs/.


After running, JSON files appear in sample_dataset/outputs/.



