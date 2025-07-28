import json
import fitz  # PyMuPDF
from collections import Counter
import argparse
from pathlib import Path
import os
import re
import sys

class EnhancedHeadingExtractor:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
        self.text_elements = []
        self.headings = []
        
    def extract_all_text_with_spacing(self):
        """Extract text with detailed positioning and spacing information"""
        print("Extracting text with spacing analysis...")
        
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            page_height = page.rect.height
            page_width = page.rect.width
            blocks = page.get_text("dict")["blocks"]
            
            page_elements = []
            
            for block in blocks:
                if block.get("type") == 0:  # Text block
                    # Skip tables
                    if self.is_table_block(block):
                        continue
                        
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span.get("text", "").strip()
                            if text:
                                bbox = span.get("bbox", [0, 0, 0, 0])
                                page_elements.append({
                                    "text": text,
                                    "page": page_num + 1,
                                    "font_size": span.get("size", 12),
                                    "font_name": span.get("font", ""),
                                    "font_flags": span.get("flags", 0),
                                    "is_bold": bool(span.get("flags", 0) & 16),
                                    "is_italic": bool(span.get("flags", 0) & 2),
                                    "bbox": bbox,
                                    "x_position": bbox[0],
                                    "y_position": bbox[1],
                                    "width": bbox[2] - bbox[0],
                                    "height": bbox[3] - bbox[1],
                                    "page_width": page_width,
                                    "page_height": page_height
                                })
            
            # Sort by Y position to analyze spacing
            page_elements.sort(key=lambda x: x["y_position"])
            
            # Calculate spacing before and after each element
            for i, elem in enumerate(page_elements):
                # Spacing before
                if i > 0:
                    prev_elem = page_elements[i-1]
                    spacing_before = elem["y_position"] - prev_elem["bbox"][3]
                else:
                    spacing_before = elem["y_position"]  # Distance from top
                
                # Spacing after
                if i < len(page_elements) - 1:
                    next_elem = page_elements[i+1]
                    spacing_after = next_elem["y_position"] - elem["bbox"][3]
                else:
                    spacing_after = page_height - elem["bbox"][3]  # Distance to bottom
                
                elem["spacing_before"] = max(0, spacing_before)
                elem["spacing_after"] = max(0, spacing_after)
                elem["left_margin"] = elem["x_position"]
                elem["right_margin"] = page_width - elem["bbox"][2]
            
            self.text_elements.extend(page_elements)
        
        print(f"Extracted {len(self.text_elements)} text elements with spacing")
    
    def is_table_block(self, block):
        """Enhanced table detection"""
        if "lines" not in block:
            return False
            
        lines = block["lines"]
        if len(lines) < 2:
            return False
        
        # Check for tabular patterns
        short_spans = 0
        total_spans = 0
        x_positions = []
        
        for line in lines:
            if "spans" in line:
                for span in line["spans"]:
                    text = span.get("text", "").strip()
                    if text:
                        total_spans += 1
                        if len(text) < 15:  # Short text
                            short_spans += 1
                        x_positions.append(span.get("bbox", [0])[0])
        
        # If many short texts with consistent X positions, likely a table
        if total_spans > 4 and short_spans / total_spans > 0.7:
            # Check for column alignment
            x_positions.sort()
            if len(set([round(x/10)*10 for x in x_positions])) >= 3:  # Multiple columns
                return True
                
        return False
    
    def analyze_spacing_patterns(self):
        """Analyze spacing patterns to identify normal vs heading spacing"""
        if not self.text_elements:
            return {}
        
        spacings_before = [elem["spacing_before"] for elem in self.text_elements if elem["spacing_before"] > 0]
        spacings_after = [elem["spacing_after"] for elem in self.text_elements if elem["spacing_after"] > 0]
        
        # Calculate typical spacing
        avg_spacing_before = sum(spacings_before) / len(spacings_before) if spacings_before else 0
        avg_spacing_after = sum(spacings_after) / len(spacings_after) if spacings_after else 0
        
        # Sort to find typical ranges
        spacings_before.sort()
        spacings_after.sort()
        
        # Get percentiles
        def get_percentile(data, p):
            if not data:
                return 0
            idx = int(len(data) * p / 100)
            return data[min(idx, len(data)-1)]
        
        patterns = {
            "normal_spacing_before": get_percentile(spacings_before, 50),  # Median
            "large_spacing_before": get_percentile(spacings_before, 80),   # 80th percentile
            "normal_spacing_after": get_percentile(spacings_after, 50),
            "large_spacing_after": get_percentile(spacings_after, 80),
            "avg_spacing_before": avg_spacing_before,
            "avg_spacing_after": avg_spacing_after
        }
        
        print(f"Spacing patterns: {patterns}")
        return patterns
    
    def get_hierarchical_level_from_numbering(self, text):
        """Determine hierarchical level based on numbering pattern"""
        text = text.strip()
        
        # Pattern 1: Decimal numbering (1., 1.1, 1.1.1, etc.)
        decimal_match = re.match(r'^(\d+(?:\.\d+)*)\.\s+', text)
        if decimal_match:
            number_part = decimal_match.group(1)
            depth = number_part.count('.') + 1  # Count dots and add 1
            return min(depth, 3)  # Cap at H3
        
        # Pattern 2: Parenthetical numbering (1), (1.1), etc.
        paren_match = re.match(r'^\((\d+(?:\.\d+)*)\)\s+', text)
        if paren_match:
            number_part = paren_match.group(1)
            depth = number_part.count('.') + 1
            return min(depth + 1, 3)  # Offset by 1 level, cap at H3
        
        # Pattern 3: Letter numbering (A., B., etc.) - Level 1
        if re.match(r'^[A-Z]\.\s+', text):
            return 1
        
        # Pattern 4: Roman numerals (I., II., etc.) - Level 1  
        if re.match(r'^[IVX]+\.\s+', text):
            return 1
        
        # Pattern 5: Lowercase letters (a), b), etc.) - Level 3
        if re.match(r'^[a-z]\)\s+', text):
            return 3
        
        # Pattern 6: Simple numbering without explicit structure
        if re.match(r'^\d+\s+[A-Za-z]', text):  # "1 Introduction" (no dot)
            return 1
        
        return None
    
    def get_comprehensive_heading_score(self, elem, font_levels, spacing_patterns, body_size):
        """COMPREHENSIVE SCORING SYSTEM - Enhanced with all criteria"""
        score = 0
        reasons = []
        forced_level = None
        
        text = elem["text"].strip()
        
        # 1. HIERARCHICAL NUMBERING (HIGHEST PRIORITY - 35% weight)
        hierarchical_level = self.get_hierarchical_level_from_numbering(text)
        if hierarchical_level:
            score += 6  # High score for numbered headings
            forced_level = hierarchical_level  # Force this level regardless of font
            reasons.append(f"hierarchical_L{hierarchical_level}(6)")
        
        # 2. FONT SIZE ANALYSIS (25% weight)
        font_size = elem["font_size"]
        font_ratio = font_size / body_size
        
        if font_ratio >= 2.0:  # Very large font
            font_score = 4
            score += font_score
            reasons.append(f"very_large_font({font_score})")
        elif font_ratio >= 1.5:  # Large font
            font_score = 3
            score += font_score
            reasons.append(f"large_font({font_score})")
        elif font_ratio >= 1.3:  # Medium-large font
            font_score = 2
            score += font_score
            reasons.append(f"medium_font({font_score})")
        elif font_ratio >= 1.1:  # Slightly larger font
            font_score = 1
            score += font_score
            reasons.append(f"slightly_large_font({font_score})")
        
        # 3. BOLD FORMATTING (15% weight)
        if elem["is_bold"]:
            bold_score = 3
            score += bold_score
            reasons.append(f"bold({bold_score})")
        
        # 4. SPACING ANALYSIS (15% weight)
        # Spacing before
        if elem["spacing_before"] > spacing_patterns["large_spacing_before"]:
            score += 2
            reasons.append("large_spacing_before(2)")
        elif elem["spacing_before"] > spacing_patterns["normal_spacing_before"] * 1.5:
            score += 1
            reasons.append("medium_spacing_before(1)")
        
        # Spacing after
        if elem["spacing_after"] > spacing_patterns["large_spacing_after"]:
            score += 1
            reasons.append("large_spacing_after(1)")
        
        # 5. POSITION & ALIGNMENT (5% weight)
        # Centered text
        center_x = elem["x_position"] + elem["width"] / 2
        page_center = elem["page_width"] / 2
        if abs(center_x - page_center) < elem["page_width"] * 0.1:
            score += 1
            reasons.append("centered(1)")
        
        # Not heavily indented
        if elem["left_margin"] < elem["page_width"] * 0.2:
            score += 1
            reasons.append("good_alignment(1)")
        
        # 6. TEXT CHARACTERISTICS (5% weight)
        # All caps
        if text.isupper() and 5 < len(text) < 50:
            score += 2
            reasons.append("all_caps(2)")
        
        # Title case
        elif text.istitle() and len(text.split()) <= 8:
            score += 1
            reasons.append("title_case(1)")
        
        # Appropriate length for headings
        if 5 <= len(text) <= 100:
            score += 1
            reasons.append("good_length(1)")
        elif len(text) > 200:
            score -= 2  # Penalty for very long text
            reasons.append("too_long(-2)")
        
        # 7. CONTENT PATTERNS (bonus points)
        # Heading keywords
        heading_keywords = [
            'introduction', 'conclusion', 'summary', 'overview', 'background', 
            'methodology', 'results', 'discussion', 'chapter', 'section', 
            'appendix', 'references', 'bibliography', 'index', 'glossary',
            'pathway', 'options', 'programs', 'courses', 'requirements',
            'objectives', 'goals', 'scope', 'purpose', 'abstract'
        ]
        if any(keyword in text.lower() for keyword in heading_keywords):
            score += 2
            reasons.append("heading_keywords(2)")
        
        # Question format (often used for section headings)
        if text.endswith('?') and len(text.split()) <= 10:
            score += 1
            reasons.append("question_format(1)")
        
        # 8. FONT FAMILY ANALYSIS (bonus)
        font_name = elem.get("font_name", "").lower()
        if any(font_type in font_name for font_type in ['bold', 'black', 'heavy', 'semibold']):
            score += 1
            reasons.append("bold_font_family(1)")
        
        # 9. PAGE POSITION (bonus for page-level headings)
        if elem["page"] > 1 and elem["y_position"] < elem["page_height"] * 0.2:
            score += 1
            reasons.append("top_of_page(1)")
        
        return score, reasons, forced_level
    
    def is_just_number(self, text):
        """Check if text is just numbering without meaningful content"""
        clean_text = re.sub(r'[.\(\)\s\-]+', '', text).strip()
        
        if len(clean_text) <= 2:
            return True
        if clean_text.isdigit():
            return True
        if re.match(r'^[0-9\.]+$', clean_text):
            return True
        if re.match(r'^[A-Z]$', clean_text):
            return True
        if re.match(r'^[ivx]+$', clean_text.lower()):
            return True
            
        return False
    
    def combine_numbered_headings(self):
        """Combine numbered prefixes with their heading text"""
        combined_elements = []
        i = 0
        
        while i < len(self.text_elements):
            current = self.text_elements[i]
            text = current["text"].strip()
            
            # Check if looks like a numbering prefix
            if re.match(r'^(\d+\.?|\d+\.\d+\.?|\d+\.\d+\.\d+\.?|[A-Z]\.|\([0-9]+\)|[ivx]+\.?)$', text.strip(), re.IGNORECASE):
                # Look for next element
                if i + 1 < len(self.text_elements):
                    next_elem = self.text_elements[i + 1]
                    
                    # If on same page and close by
                    if (next_elem["page"] == current["page"] and 
                        abs(next_elem["y_position"] - current["y_position"]) < current["height"] * 2):
                        
                        # Combine the texts
                        combined_text = f"{text} {next_elem['text']}".strip()
                        
                        # Create combined element
                        combined_elem = current.copy()
                        combined_elem["text"] = combined_text
                        combined_elem["font_size"] = max(current["font_size"], next_elem["font_size"])
                        combined_elem["is_bold"] = current["is_bold"] or next_elem["is_bold"]
                        combined_elem["width"] = next_elem["bbox"][2] - current["bbox"][0]
                        
                        combined_elements.append(combined_elem)
                        i += 2  # Skip both elements
                        continue
            
            combined_elements.append(current)
            i += 1
        
        return combined_elements
    
    def extract_headings(self):
        """Main extraction method with comprehensive scoring + hierarchical priority"""
        try:
            # Extract text with spacing
            self.extract_all_text_with_spacing()
            
            if not self.text_elements:
                print("No text found")
                return []
            
            # Combine numbered headings
            print("Combining numbered headings...")
            self.text_elements = self.combine_numbered_headings()
            
            # Analyze spacing patterns
            spacing_patterns = self.analyze_spacing_patterns()
            
            # Get font size analysis
            font_sizes = [elem["font_size"] for elem in self.text_elements]
            font_counter = Counter(font_sizes)
            unique_sizes = sorted(font_counter.keys(), reverse=True)
            
            font_levels = {}
            for i, size in enumerate(unique_sizes[:6]):
                font_levels[size] = i + 1
            
            body_size = font_counter.most_common(1)[0][0]
            print(f"Font levels: {font_levels}")
            print(f"Body text size: {body_size}")
            
            # COMPREHENSIVE SCORING for all elements
            candidates = []
            for elem in self.text_elements:
                text = elem["text"].strip()
                
                # Basic filters
                if len(text) < 3 or len(text) > 300:
                    continue
                if self.is_just_number(text):
                    continue
                
                # Comprehensive scoring
                score, reasons, forced_level = self.get_comprehensive_heading_score(
                    elem, font_levels, spacing_patterns, body_size
                )
                
                # Dynamic threshold based on content
                min_threshold = 4
                if forced_level:  # Hierarchical numbering found
                    min_threshold = 3
                elif elem["is_bold"] and elem["font_size"] > body_size * 1.2:
                    min_threshold = 4
                elif elem["font_size"] > body_size * 1.5:
                    min_threshold = 3
                
                if score >= min_threshold:
                    # Determine final level
                    if forced_level:
                        level = forced_level
                    else:
                        # Use font size as primary, but adjust based on other factors
                        level = font_levels.get(elem["font_size"], 6)
                        
                        # Promote level based on comprehensive score
                        if score >= 10 and level > 1:
                            level = max(1, level - 1)
                        elif score >= 8 and level > 2:
                            level = max(2, level - 1)
                    
                    if level <= 3:  # Only H1, H2, H3
                        candidates.append({
                            "type": f"H{level}",
                            "text": text,
                            "page": elem["page"],
                            "score": score,
                            "reasons": reasons,
                            "font_size": elem["font_size"],
                            "hierarchical": bool(forced_level)
                        })
            
            # Sort by page, hierarchical priority, then score
            candidates.sort(key=lambda x: (x["page"], not x["hierarchical"], -x["score"]))
            
            # Remove duplicates
            seen = set()
            self.headings = []
            for candidate in candidates:
                key = (candidate["text"].lower().strip(), candidate["page"])
                if key not in seen:
                    seen.add(key)
                    self.headings.append({
                        "type": candidate["type"],
                        "text": candidate["text"],
                        "page": candidate["page"]
                    })
            
            print(f"Found {len(self.headings)} headings with comprehensive scoring")
            
            # Debug information
            hierarchical_count = len([c for c in candidates if c["hierarchical"]])
            print(f"  🔢 {hierarchical_count} hierarchical numbered headings")
            print(f"  📝 {len(candidates) - hierarchical_count} format-based headings")
            
            return self.headings
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def save_to_json(self, output_path):
        """Save results with FIXED title/outline duplication logic"""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Extract title from first page's main heading
            title = "Untitled Document"
            outline_headings = []
            
            # Find the main heading on page 1 to use as title
            page_1_headings = [h for h in self.headings if h["page"] == 1]
            
            if page_1_headings:
                # Use the first H1 on page 1 as title, or first heading if no H1
                h1_headings = [h for h in page_1_headings if h["type"] == "H1"]
                if h1_headings:
                    title = h1_headings[0]["text"]
                else:
                    title = page_1_headings[0]["text"]
            elif self.headings:
                # Fallback: use first H1 from any page
                for heading in self.headings:
                    if heading["type"] == "H1":
                        title = heading["text"]
                        break
            
            # Create outline - EXCLUDE the exact title match
            for heading in self.headings:
                # Skip if this heading text exactly matches the title
                if heading["text"].strip() == title.strip():
                    continue
                
                # Add to outline
                outline_headings.append({
                    "level": heading["type"],
                    "text": heading["text"],
                    "page": heading["page"]
                })
            
            # Final JSON structure
            output_data = {
                "title": title,
                "outline": outline_headings
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Saved to: {output_path}")
            print(f"📄 Title: {title}")
            print(f"📋 Outline entries: {len(outline_headings)}")
            
            # Check for duplication fix
            total_headings = len(self.headings)
            if len(outline_headings) < total_headings:
                print(f"🔧 Fixed duplication: {total_headings - len(outline_headings)} title match(es) removed from outline")
            
        except Exception as e:
            print(f"❌ Save error: {e}")
    
    def print_results(self):
        """Print comprehensive results"""
        print(f"\n" + "="*70)
        print(f"📄 Document: {Path(self.pdf_path).name}")
        print(f"📄 Pages: {len(self.doc)}")
        print(f"🔍 Method: Comprehensive Scoring + Hierarchical Priority")
        
        # Extract title
        title = "Untitled Document"
        if self.headings:
            page_1_headings = [h for h in self.headings if h["page"] == 1]
            if page_1_headings:
                h1_headings = [h for h in page_1_headings if h["type"] == "H1"]
                title = h1_headings[0]["text"] if h1_headings else page_1_headings[0]["text"]
            else:
                for heading in self.headings:
                    if heading["type"] == "H1":
                        title = heading["text"]
                        break
        
        print(f"📖 Document Title: {title}")
        
        if self.headings:
            # Count outline entries (excluding title)
            outline_count = len([h for h in self.headings if h["text"].strip() != title.strip()])
            print(f"📝 Outline Entries: {outline_count}")
            
            # Distribution
            h1_count = len([h for h in self.headings if h["type"] == "H1" and h["text"].strip() != title.strip()])
            h2_count = len([h for h in self.headings if h["type"] == "H2"])
            h3_count = len([h for h in self.headings if h["type"] == "H3"])
            
            print(f"📊 Distribution: H1({h1_count}), H2({h2_count}), H3({h3_count})")
            
            print(f"\n📋 Document Outline:")
            print("-" * 70)
            
            outline_counter = 1
            for heading in self.headings:
                # Skip title
                if heading["text"].strip() == title.strip():
                    continue
                
                indent = "  " * (int(heading["type"][1]) - 1)
                text_preview = heading["text"][:55] + "..." if len(heading["text"]) > 55 else heading["text"]
                
                # Mark hierarchical vs format-based
                hierarchical_mark = "🔢" if self.get_hierarchical_level_from_numbering(heading["text"]) else "📝"
                
                print(f"{outline_counter:2d}. {hierarchical_mark} {indent}{heading['type']}: {text_preview} (Page {heading['page']})")
                outline_counter += 1
        else:
            print("⚠️  No headings found")
        
        print("="*70)
        print("🔢 = Hierarchical numbered heading")
        print("📝 = Comprehensive scoring based heading")

def main():
    parser = argparse.ArgumentParser(description="Enhanced PDF Heading Extractor - Comprehensive Scoring + Hierarchical")
    parser.add_argument("pdf_path", help="Path to PDF file or directory")
    parser.add_argument("-o", "--output", help="Output JSON path or output directory (for batch)", default=None)
    
    args = parser.parse_args()
    input_path = Path(args.pdf_path)
    
    if not input_path.exists():
        print(f"❌ File or directory not found: {input_path}")
        return
    
    # If input is a directory, process all PDFs inside
    if input_path.is_dir():
        pdf_files = sorted(input_path.glob("*.pdf"))
        if not pdf_files:
            print(f"❌ No PDF files found in directory: {input_path}")
            return
        
        # Determine output directory
        if args.output:
            output_dir = Path(args.output)
        else:
            # Default: app/output if input is app/input
            if str(input_path).endswith("app/input"):
                output_dir = Path("app/output")
            else:
                output_dir = input_path.parent / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for pdf_file in pdf_files:
            print(f"\n=== Processing: {pdf_file.name} ===")
            output_json = output_dir / (pdf_file.stem + ".json")
            try:
                extractor = EnhancedHeadingExtractor(str(pdf_file))
                extractor.extract_headings()
                extractor.save_to_json(str(output_json))
                extractor.print_results()
            except Exception as e:
                print(f"❌ Failed to process {pdf_file}: {e}")
                import traceback
                traceback.print_exc()
    else:
        # Single file mode (original behavior)
        if args.output:
            output_path = args.output
        else:
            # Default output: same as input, .json extension, or app/output if input is app/input
            if str(input_path.parent).endswith("app/input"):
                output_path = str(Path("app/output") / (input_path.stem + ".json"))
            else:
                output_path = str(input_path.with_suffix(".json"))
        try:
            extractor = EnhancedHeadingExtractor(str(input_path))
            extractor.extract_headings()
            extractor.save_to_json(output_path)
            extractor.print_results()
        except Exception as e:
            print(f"❌ Failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
