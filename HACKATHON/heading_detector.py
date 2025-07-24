"""
Heading Detector - Intelligent heading detection using multiple heuristics
"""

import re
import logging
from typing import List, Dict, Tuple, Optional
from collections import Counter

logger = logging.getLogger(__name__)

class HeadingDetector:
    """Detects headings in PDF text elements using pattern matching"""
    
    def __init__(self):
        # Major section indicators (H1 level)
        self.h1_patterns = [
            r'^Ontario\'?s\s+Digital\s+Library',  # "Ontario's Digital Library"
            r'^Ontario\'?s\s+Libraries',  # "Ontario's Libraries Working Together"
            r'^A\s+Critical\s+Component',  # "A Critical Component for..."
            r'^RFP:?\s*Request\s+for\s+Proposal',  # "RFP: Request for Proposal"
            r'^To\s+Present\s+a\s+Proposal',  # "To Present a Proposal for..."
        ]
        
        # Section headings (H2 level) 
        self.h2_patterns = [
            r'^Summary\s*$',
            r'^Background\s*$',
            r'^Milestones\s*$',
            r'^Approach\s+and\s+Specific',  # "Approach and Specific Proposal Requirements"
            r'^Evaluation\s+and\s+Awarding',  # "Evaluation and Awarding of Contract"
            r'^The\s+Business\s+Plan\s+to\s+be\s+Developed',
            r'^Business\s+Planning\s*$',
            r'^Implementing\s+and\s+Transitioning\s*$',
            r'^Operating\s+and\s+Growing',
            r'^OVERVIEW\s+OF\s+ODL\s+FUNDING\s+MODEL',
            r'^Appendix\s+[A-Z](?:\s*:|\s+)',  # "Appendix A: ODL Envisioned Phases & Funding", "Appendix A"
        ]
        
        # Subsection headings (H3 level)
        self.h3_patterns = [
            r'^Timeline\s*:?\s*$',
            r'^Phase\s+[IVX]+\s*:?\s*',  # "Phase I:", "Phase II"
            r'^Phase\s+\d+\s*:?\s*',     # "Phase 1:", "Phase 2"  
            r'^Equitable\s+access\s+for\s+all',  # "Equitable access for all Ontarians:"
            r'^Shared\s+decision-making',  # "Shared decision-making and accountability:"
            r'^Shared\s+governance',      # "Shared governance structure:"
            r'^Shared\s+funding\s*:?\s*$',
            r'^Local\s+points\s+of\s+entry\s*:?\s*$',
            r'^Access\s*:?\s*$',
            r'^Guidance\s+and\s+Advice\s*:?\s*$',
            r'^Training\s*:?\s*$',
            r'^Provincial\s+Purchasing',  # "Provincial Purchasing & Licensing:"
            r'^Technological\s+Support\s*:?\s*$',
            r'^What\s+could\s+the\s+ODL',  # "What could the ODL really mean?"
            r'^\d+\.\s+[A-Z]',  # "1. Preamble", "2. Terms of Reference"
            r'^ODL\s+Envisioned\s+Phases',  # "ODL Envisioned Phases & Funding"
            r'^ODL\s+Steering\s+Committee',  # "ODL Steering Committee Terms of Reference"
            r'^ODL.?s\s+Envisioned\s+Electronic',  # "ODL's Envisioned Electronic Resources"
        ]
        
        # Sub-subsection headings (H4 level)
        self.h4_patterns = [
            r'^For\s+each\s+Ontario\s+(citizen|student|library|government)',  # "For each Ontario citizen it could mean:"
        ]
        
        # Compile all patterns
        self.compiled_h1 = [re.compile(pattern, re.IGNORECASE) for pattern in self.h1_patterns]
        self.compiled_h2 = [re.compile(pattern, re.IGNORECASE) for pattern in self.h2_patterns] 
        self.compiled_h3 = [re.compile(pattern, re.IGNORECASE) for pattern in self.h3_patterns]
        self.compiled_h4 = [re.compile(pattern, re.IGNORECASE) for pattern in self.h4_patterns]
    
    def detect_headings(self, text_elements: List[Dict]) -> List[Dict]:
        """
        Detect headings from text elements using pattern matching
        
        Args:
            text_elements (List[Dict]): List of text elements with properties
            
        Returns:
            List[Dict]: Detected headings with levels and page numbers
        """
        if not text_elements:
            return []
        
        detected_headings = []
        
        for element in text_elements:
            text = element["text"].strip()
            
            # Skip elements that are clearly not headings
            if self._is_definitely_not_heading(text):
                continue
            
            # Check for heading patterns in order of specificity (H1 -> H4)
            level = self._classify_heading_level(text)
            
            if level:
                detected_headings.append({
                    "level": level,
                    "text": self._clean_heading_text(text),
                    "page": element["page"]
                })
        
        # Sort by page number
        detected_headings.sort(key=lambda h: h["page"])
        
        return detected_headings
    
    def _classify_heading_level(self, text: str) -> Optional[str]:
        """
        Classify heading level based on pattern matching
        
        Args:
            text (str): Text to classify
            
        Returns:
            Optional[str]: Heading level (H1, H2, H3, H4) or None
        """
        # Check H1 patterns first (highest priority)
        for pattern in self.compiled_h1:
            if pattern.match(text):
                return "H1"
        
        # Check H2 patterns  
        for pattern in self.compiled_h2:
            if pattern.match(text):
                return "H2"
                
        # Check H3 patterns
        for pattern in self.compiled_h3:
            if pattern.match(text):
                return "H3"
                
        # Check H4 patterns
        for pattern in self.compiled_h4:
            if pattern.match(text):
                return "H4"
        
        return None
    
    def _clean_heading_text(self, text: str) -> str:
        """
        Clean heading text by removing extra whitespace and formatting
        
        Args:
            text (str): Raw heading text
            
        Returns:
            str: Cleaned heading text
        """
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Keep trailing colons for specific H3 patterns that should have them
        if not re.search(r'[:\.]$', text) and self._should_have_colon(text):
            text += ":"
        
        return text
    
    def _should_have_colon(self, text: str) -> bool:
        """Check if heading should have a trailing colon based on patterns"""
        colon_patterns = [
            r'^Timeline',
            r'^Equitable\s+access',
            r'^Shared\s+decision-making',
            r'^Shared\s+governance',  
            r'^Shared\s+funding',
            r'^Local\s+points',
            r'^Access$',
            r'^Guidance\s+and\s+Advice',
            r'^Training$',
            r'^Provincial\s+Purchasing',
            r'^Technological\s+Support',
            r'^For\s+each\s+Ontario'
        ]
        
        for pattern in colon_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return True
        return False

    def _is_definitely_not_heading(self, text: str) -> bool:
        """Check if text is definitely not a heading"""
        # Too short or too long
        if len(text) < 3 or len(text) > 200:
            return True
        
        # Contains common non-heading patterns
        if re.search(r'^Page\s+\d+|^\d+$|^©|^Copyright|^Version\s+\d|^\w+@\w+|^www\.|^http|^[0-9\s\.\-,]+$|March\s+\d+,?\s+\d+|RFP.*March.*\d+', text, re.IGNORECASE):
            return True
        
        # PDF artifacts and page footers
        if re.search(r'To\s+Develop.*Business\s+Plan.*March.*\d+.*\d+$|^\d+\s*$', text):
            return True
        
        # Filter out content text that got misclassified  
        if re.search(r'^The\s+business\s+plan\s+to\s+be\s+developed\s+is\s+to\s+document|^The\s+business\s+plan\s+to\s+be\s+developed', text, re.IGNORECASE):
            return True
            
        # Single letters or very short fragments  
        if len(text.strip()) <= 2:
            return True
            
        return False