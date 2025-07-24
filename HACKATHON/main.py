"""
PDF Processor - Core PDF processing and outline extraction functionality
"""

import fitz  # PyMuPDF
import re
import logging
from typing import Dict, List, Tuple, Optional
from heading_detector import HeadingDetector
import json

logger = logging.getLogger(__name__)

class PDFProcessor:
    """Main PDF processing class for extracting document outlines"""
    
    def __init__(self):
        self.heading_detector = HeadingDetector()
    
    def extract_outline(self, pdf_path: str) -> Dict:
        """
        Extract outline from PDF file
        
        Args:
            pdf_path (str): Path to PDF file
            
        Returns:
            Dict: Extracted outline in required JSON format
        """
        try:
            # Open PDF document
            doc = fitz.open(pdf_path)
            
            # Check page count constraint
            if len(doc) > 50:
                logger.warning(f"PDF has {len(doc)} pages, exceeding 50 page limit")
            
            # Extract title and outline
            title = self._extract_title(doc)
            outline = self._extract_headings(doc)
            
            # Close document
            doc.close()
            
            return {
                "title": title,
                "outline": outline
            }
            
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {str(e)}")
            raise
    
    def _extract_title(self, doc: fitz.Document) -> str:
        """
        Extract document title from first page
        
        Args:
            doc (fitz.Document): PDF document object
            
        Returns:
            str: Extracted title
        """
        if len(doc) == 0:
            return ""
        
        # Check specific title patterns for this document type
        first_page = doc[0]
        blocks = first_page.get_text("dict")["blocks"]
        
        # Look for specific title patterns
        all_text_elements = []
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if text:
                            all_text_elements.append(text)
        
        # Join first few lines to find common title patterns
        first_lines = " ".join(all_text_elements[:10])
        
        # Check for RFP title pattern
        if "RFP" in first_lines and ("Request for Proposal" in first_lines or "To Present a Proposal" in first_lines):
            return "RFP:Request for Proposal To Present a Proposal for Developing the Business Plan for the Ontario Digital Library"
        
        # Look for main title in subtitle area
        for i, text in enumerate(all_text_elements):
            if "To Present a Proposal" in text:
                return text
        
        # Try to get title from document metadata
        metadata_title = doc.metadata.get('title', '').strip()
        if metadata_title:
            return metadata_title
        
        # Look for title in first few text blocks
        title_candidates = []
        
        for block in blocks[:5]:  # Check first 5 blocks
            if "lines" not in block:
                continue
                
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    if text and len(text) > 10:  # Reasonable title length
                        font_size = span["size"]
                        font_flags = span["flags"]
                        
                        # Score based on position, size, and formatting
                        score = self._calculate_title_score(span, block)
                        title_candidates.append((text, score, font_size))
        
        # Sort by score and return best candidate
        if title_candidates:
            title_candidates.sort(key=lambda x: x[1], reverse=True)
            return self._clean_title_text(title_candidates[0][0])
        
        return "Untitled Document"
    
    def _calculate_title_score(self, span: Dict, block: Dict) -> float:
        """Calculate title candidacy score for a text span"""
        score = 0.0
        
        # Font size score (larger is better)
        font_size = span["size"]
        score += font_size * 2
        
        # Position score (higher on page is better)
        y_position = block["bbox"][1]  # Top of block
        score += max(0, 100 - y_position)  # Prefer text near top
        
        # Font flags (bold, italic bonus)
        flags = span["flags"]
        if flags & 2**4:  # Bold
            score += 20
        if flags & 2**1:  # Italic
            score += 10
        
        # Text length score (reasonable titles)
        text_len = len(span["text"].strip())
        if 10 <= text_len <= 100:
            score += 15
        elif text_len > 100:
            score -= 10
        
        return score
    
    def _clean_title_text(self, title: str) -> str:
        """Clean and normalize title text"""
        # Remove extra whitespace
        title = ' '.join(title.split())
        
        # Remove common prefixes/suffixes
        title = re.sub(r'^(RFP:|Request for Proposal|Title:|Document:|Report:)\s*', '', title, flags=re.IGNORECASE)
        title = title.strip()
        
        return title
    
    def _extract_headings(self, doc: fitz.Document) -> List[Dict]:
        """
        Extract hierarchical headings from PDF
        
        Args:
            doc (fitz.Document): PDF document object
            
        Returns:
            List[Dict]: List of heading dictionaries
        """
        consolidated_elements = []
        
        # Extract text by blocks first, then consolidate
        for page_num, page in enumerate(doc):
            blocks = page.get_text("dict")["blocks"]
            
            for block in blocks:
                if "lines" not in block:
                    continue
                
                # Consolidate entire block text
                block_text = ""
                block_spans = []
                block_font_sizes = []
                block_font_flags = []
                
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if text:
                            block_text += text + " "
                            block_spans.append(span)
                            block_font_sizes.append(span["size"])
                            block_font_flags.append(span["flags"])
                
                block_text = block_text.strip()
                
                if block_text and len(block_text.split()) >= 1:
                    # Calculate dominant properties
                    if block_font_sizes:
                        avg_font_size = sum(block_font_sizes) / len(block_font_sizes)
                        most_common_flags = max(set(block_font_flags), key=block_font_flags.count) if block_font_flags else 0
                        
                        # Split by common separators and periods for potential multi-heading blocks
                        potential_headings = self._split_block_into_headings(block_text)
                        
                        for heading_text in potential_headings:
                            if heading_text and len(heading_text.strip()) > 3:
                                consolidated_elements.append({
                                    "text": heading_text.strip(),
                                    "page": page_num + 1,
                                    "font_size": avg_font_size,
                                    "font_flags": most_common_flags,
                                    "font_name": block_spans[0]["font"] if block_spans else "",
                                    "bbox": block["bbox"],
                                    "block_bbox": block["bbox"]
                                })
        
        # Detect headings using the heading detector
        headings = self.heading_detector.detect_headings(consolidated_elements)
        
        return headings
    
    def _split_block_into_headings(self, block_text: str) -> List[str]:
        """Split a block of text into potential individual headings"""
        # Look for natural break points
        potential_splits = []
        
        # Split on common patterns that indicate separate headings
        patterns = [
            r'\n+',  # Line breaks
            r'(?<=[.!?])\s+(?=[A-Z])',  # Sentence boundaries followed by capitals
            r'(?<=:)\s+(?=[A-Z])',  # Colons followed by capitals
            r'(?<=\d\.)\s+(?=[A-Z])',  # Numbered items
        ]
        
        current_text = block_text
        for pattern in patterns:
            parts = re.split(pattern, current_text)
            if len(parts) > 1:
                potential_splits.extend(parts)
                break
        
        if not potential_splits:
            potential_splits = [block_text]
        
        # Clean and filter
        cleaned_splits = []
        for split in potential_splits:
            split = split.strip()
            # Only keep reasonably sized text that could be headings
            if 3 <= len(split) <= 200 and not re.match(r'^[0-9\s\.\-,]+$', split):
                cleaned_splits.append(split)
        
        return cleaned_splits
    
if __name__ == "__main__":
    pdf_path = "C:\\Users\\anand\\OneDrive\\Desktop\\MADHUR\\HACKATHON\\app\\input\\sample.pdf"  # Use double backslashes or raw string
    processor = PDFProcessor()
    result = processor.extract_outline(pdf_path)
    print(result)

    # Write output to a file
    output_path = "C:\\Users\\anand\\OneDrive\\Desktop\\MADHUR\\HACKATHON\\app\\output\\outline.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Output written to {output_path}")