import fitz  # PyMuPDF
import os
import json
import re
from collections import defaultdict, Counter
from typing import List, Dict, Tuple, Set
import statistics

class EnhancedOutlineExtractor:
    def __init__(self):
        # Enhanced heading patterns - more comprehensive regex
        self.heading_patterns = [
            r'^\d+\.\s+.+',  # 1. Title
            r'^\d+\.\d+\s+.+',  # 1.1 Subtitle  
            r'^\d+\.\d+\.\d+\s+.+',  # 1.1.1 Sub-subtitle
            r'^[IVX]+\.\s+.+',  # I. Roman numerals
            r'^[A-Z]\.\s+.+',  # A. Letter numbering
            r'^Chapter\s+\d+',  # Chapter 1
            r'^Section\s+\d+',  # Section 1
            r'^Part\s+[IVX\d]+',  # Part I/1
            r'^\d+\s+[A-Z][a-z]',  # 1 Introduction
            r'^[A-Z][A-Z\s]{10,}$',  # ALL CAPS headings
        ]
        
        # Common heading keywords that indicate structure
        self.heading_keywords = {
            'introduction', 'conclusion', 'abstract', 'summary', 'overview',
            'background', 'methodology', 'results', 'discussion', 'references',
            'appendix', 'chapter', 'section', 'part', 'table of contents',
            'executive summary', 'acknowledgments', 'bibliography'
        }

    def extract_text_features(self, page) -> List[Dict]:
        """Extract text with comprehensive features for classification"""
        blocks = page.get_text("dict")["blocks"]
        text_elements = []
        
        for block_idx, block in enumerate(blocks):
            if "lines" not in block:
                continue
                
            for line_idx, line in enumerate(block["lines"]):
                if not line["spans"]:
                    continue
                    
                # Combine text from all spans in the line
                text_parts = []
                font_sizes = []
                font_flags = []
                colors = []
                
                for span in line["spans"]:
                    text_parts.append(span["text"])
                    font_sizes.append(span["size"])
                    font_flags.append(span["flags"])
                    colors.append(span.get("color", 0))
                
                text = " ".join(text_parts).strip()
                if len(text) < 3:  # Skip very short text
                    continue
                
                # Calculate features
                avg_font_size = statistics.mean(font_sizes)
                max_font_size = max(font_sizes)
                is_bold = any(flag & 2**4 for flag in font_flags)  # Bold flag
                is_italic = any(flag & 2**1 for flag in font_flags)  # Italic flag
                
                # Position features
                bbox = line["bbox"]
                y_position = bbox[1]  # Top y coordinate
                x_position = bbox[0]  # Left x coordinate
                line_height = bbox[3] - bbox[1]
                line_width = bbox[2] - bbox[0]
                
                text_elements.append({
                    'text': text,
                    'font_size': avg_font_size,
                    'max_font_size': max_font_size,
                    'is_bold': is_bold,
                    'is_italic': is_italic,
                    'y_position': y_position,
                    'x_position': x_position,
                    'line_height': line_height,
                    'line_width': line_width,
                    'block_idx': block_idx,
                    'line_idx': line_idx,
                    'color': colors[0] if colors else 0
                })
        
        return text_elements

    def calculate_font_statistics(self, text_elements: List[Dict]) -> Dict:
        """Calculate document-wide font statistics for better classification"""
        font_sizes = [elem['font_size'] for elem in text_elements]
        
        if not font_sizes:
            return {'body_size': 12, 'heading_threshold': 14}
        
        # Find the most common font size (likely body text)
        size_counter = Counter(font_sizes)
        body_size = size_counter.most_common(1)[0][0]
        
        # Calculate thresholds
        avg_size = statistics.mean(font_sizes)
        std_size = statistics.stdev(font_sizes) if len(font_sizes) > 1 else 2
        
        return {
            'body_size': body_size,
            'avg_size': avg_size,
            'std_size': std_size,
            'heading_threshold': body_size + std_size,
            'large_heading_threshold': body_size + 2 * std_size
        }

    def is_likely_heading(self, text: str, element: Dict, font_stats: Dict) -> Tuple[bool, float]:
        """Determine if text is likely a heading with confidence score"""
        confidence = 0.0
        
        # Font size analysis
        if element['font_size'] > font_stats['large_heading_threshold']:
            confidence += 0.4
        elif element['font_size'] > font_stats['heading_threshold']:
            confidence += 0.25
        elif element['font_size'] > font_stats['body_size']:
            confidence += 0.1
        
        # Bold text gets higher confidence
        if element['is_bold']:
            confidence += 0.3
        
        # Pattern matching
        text_lower = text.lower().strip()
        for pattern in self.heading_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                confidence += 0.35
                break
        
        # Keyword matching
        for keyword in self.heading_keywords:
            if keyword in text_lower:
                confidence += 0.2
                break
        
        # Position-based features
        # Left-aligned text is more likely to be headings
        if element['x_position'] < 100:  # Assuming left margin
            confidence += 0.1
        
        # Short lines are more likely to be headings
        if len(text.split()) <= 8:
            confidence += 0.1
        
        # All caps short text
        if text.isupper() and len(text.split()) <= 6:
            confidence += 0.2
        
        # Penalize very long text (likely paragraphs)
        if len(text.split()) > 15:
            confidence -= 0.2
        
        # Filter out common non-heading patterns
        if any(pattern in text_lower for pattern in ['page', 'figure', 'table', 'source:', 'note:']):
            confidence -= 0.3
        
        return confidence > 0.4, confidence

    def determine_heading_level(self, element: Dict, font_stats: Dict, confidence: float) -> str:
        """Determine heading level based on font size and other features"""
        font_size = element['font_size']
        
        # Use font size relative to document statistics
        if font_size > font_stats['body_size'] + 2 * font_stats['std_size']:
            return "H1"
        elif font_size > font_stats['body_size'] + font_stats['std_size']:
            return "H2"
        else:
            return "H3"

    def post_process_outline(self, outline: List[Dict]) -> List[Dict]:
        """Post-process outline to remove duplicates and improve structure"""
        # Remove duplicates while preserving order
        seen = set()
        filtered_outline = []
        
        for item in outline:
            text_key = item['text'].lower().strip()
            if text_key not in seen and len(text_key) > 2:
                seen.add(text_key)
                filtered_outline.append(item)
        
        # Sort by page and then by position
        filtered_outline.sort(key=lambda x: (x['page'], x.get('y_position', 0)))
        
        # Limit to reasonable number of headings
        return filtered_outline[:50]  # Max 50 headings per document

    def extract_existing_outline(self, doc) -> List[Dict]:
        """Try to extract existing PDF outline/bookmarks first"""
        try:
            toc = doc.get_toc()
            if toc:
                outline = []
                for item in toc:
                    level, title, page = item
                    # Convert level to H1, H2, H3 format
                    if level <= 1:
                        level_str = "H1"
                    elif level <= 2:
                        level_str = "H2"
                    else:
                        level_str = "H3"
                    
                    outline.append({
                        "level": level_str,
                        "text": title.strip(),
                        "page": page
                    })
                return outline
        except:
            pass
        return []

    def process_pdf(self, file_path: str) -> Dict:
        """Main PDF processing function"""
        doc = fitz.open(file_path)
        
        # First try to extract existing outline
        existing_outline = self.extract_existing_outline(doc)
        if existing_outline:
            doc.close()
            return {
                "title": os.path.splitext(os.path.basename(file_path))[0],
                "outline": existing_outline
            }
        
        # If no existing outline, extract from text
        all_text_elements = []
        
        # Process each page
        for page_num in range(min(len(doc), 20)):  # Limit to first 20 pages for speed
            page = doc[page_num]
            text_elements = self.extract_text_features(page)
            
            # Add page number to each element
            for element in text_elements:
                element['page'] = page_num + 1
            
            all_text_elements.extend(text_elements)
        
        doc.close()
        
        if not all_text_elements:
            return {
                "title": os.path.splitext(os.path.basename(file_path))[0],
                "outline": []
            }
        
        # Calculate font statistics
        font_stats = self.calculate_font_statistics(all_text_elements)
        
        # Extract headings
        outline = []
        for element in all_text_elements:
            is_heading, confidence = self.is_likely_heading(element['text'], element, font_stats)
            
            if is_heading:
                level = self.determine_heading_level(element, font_stats, confidence)
                outline.append({
                    "level": level,
                    "text": element['text'],
                    "page": element['page'],
                    "confidence": confidence,
                    "y_position": element['y_position']
                })
        
        # Post-process outline
        final_outline = self.post_process_outline(outline)
        
        # Remove confidence and y_position from final output
        for item in final_outline:
            item.pop('confidence', None)
            item.pop('y_position', None)
        
        return {
            "title": os.path.splitext(os.path.basename(file_path))[0],
            "outline": final_outline
        }

def main():
    """Main function to process all PDFs"""
    input_dir = "input"  # Changed to match your Docker volume mount
    output_dir = "output"  # Changed to match your Docker volume mount
    os.makedirs(output_dir, exist_ok=True)
    
    extractor = EnhancedOutlineExtractor()
    
    print("🔍 Starting PDF outline extraction...")
    print(f"📂 Looking for PDFs in: {os.path.abspath(input_dir)}")
    
    if not os.path.exists(input_dir):
        print(f"❌ Input directory '{input_dir}' not found!")
        print(f"📋 Current working directory: {os.getcwd()}")
        print(f"📋 Directory contents: {os.listdir('.')}")
        return
    
    all_files = os.listdir(input_dir)
    print(f"📋 All files in input directory: {all_files}")
    
    pdf_files = [f for f in all_files if f.endswith(".pdf")]
    print(f"📄 Found {len(pdf_files)} PDF files: {pdf_files}")
    
    if not pdf_files:
        print(f"❌ No PDF files found in '{input_dir}'!")
        return
    
    for i, filename in enumerate(pdf_files, 1):
        print(f"📄 Processing ({i}/{len(pdf_files)}): {filename}")
        
        file_path = os.path.join(input_dir, filename)
        
        try:
            result = extractor.process_pdf(file_path)
            output_path = os.path.join(output_dir, f"{os.path.splitext(filename)[0]}.json")
            
            with open(output_path, "w", encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Extracted {len(result['outline'])} headings from {filename}")
            
        except Exception as e:
            print(f"❌ Error processing {filename}: {str(e)}")
            # Create empty outline for failed files
            result = {
                "title": os.path.splitext(filename)[0],
                "outline": []
            }
            output_path = os.path.join(output_dir, f"{os.path.splitext(filename)[0]}.json")
            with open(output_path, "w", encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
    
    print("🎉 PDF outline extraction completed!")

if __name__ == "__main__":
    main()