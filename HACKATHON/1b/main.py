
import json
import os
import re
import time
from typing import Dict, List, Tuple, Any
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import fitz  # PyMuPDF
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.stem import PorterStemmer
from collections import Counter
import warnings
warnings.filterwarnings('ignore')

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)

class PersonaDrivenDocumentAnalyzer:
    """
    Advanced document analyzer that processes multiple PDFs and ranks sections
    based on persona expertise and job requirements using hybrid scoring approach.
    """

    def __init__(self):
        """Initialize the analyzer with required models and utilities."""
        print("Initializing PersonaDrivenDocumentAnalyzer...")

        # Load sentence transformer model (lightweight, ~80MB)
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')

        # Initialize TF-IDF vectorizer
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            stop_words='english',
            lowercase=True
        )

        # Initialize NLTK components
        self.stemmer = PorterStemmer()
        self.stop_words = set(stopwords.words('english'))

        # Scoring weights
        self.weights = {
            'semantic': 0.4,
            'tfidf': 0.3,
            'keyword': 0.3
        }

        print("Initialization complete!")

    def extract_text_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract text content from PDF with section and page information.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dictionary containing extracted text, sections, and metadata
        """
        try:
            doc = fitz.open(pdf_path)
            sections = []
            full_text = ""

            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text()

                # Clean and process page text
                cleaned_text = self._clean_text(page_text)
                if len(cleaned_text.strip()) < 50:  # Skip pages with minimal content
                    continue

                full_text += cleaned_text + "\n\n"

                # Extract sections from page (simple heuristic)
                page_sections = self._extract_sections_from_page(cleaned_text, page_num + 1)
                sections.extend(page_sections)

            doc.close()

            # If no clear sections found, create sections from paragraphs
            if len(sections) < 3:
                sections = self._create_sections_from_text(full_text)

            return {
                'filename': os.path.basename(pdf_path),
                'full_text': full_text.strip(),
                'sections': sections,
                'total_pages': len(doc)
            }

        except Exception as e:
            print(f"Error processing {pdf_path}: {str(e)}")
            return {
                'filename': os.path.basename(pdf_path),
                'full_text': '',
                'sections': [],
                'total_pages': 0
            }

    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        # Remove excessive whitespace and special characters
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s.,;:!?()-]', '', text)
        text = re.sub(r'\n+', '\n', text)
        return text.strip()

    def _extract_sections_from_page(self, page_text: str, page_num: int) -> List[Dict]:
        """Extract logical sections from a page of text."""
        sections = []

        # Split by common section indicators
        potential_sections = re.split(r'\n(?=[A-Z][^\n]{10,100}\n)', page_text)

        for i, section_text in enumerate(potential_sections):
            if len(section_text.strip()) < 100:  # Skip very short sections
                continue

            # Extract title (first line or sentence)
            lines = section_text.strip().split('\n')
            title = lines[0] if lines else f"Section {len(sections) + 1}"

            sections.append({
                'title': title[:100],  # Limit title length
                'content': section_text.strip(),
                'page_number': page_num,
                'section_id': f"page_{page_num}_section_{i+1}"
            })

        return sections

    def _create_sections_from_text(self, full_text: str) -> List[Dict]:
        """Create sections from full text when no clear structure is found."""
        paragraphs = [p.strip() for p in full_text.split('\n\n') if len(p.strip()) > 100]
        sections = []

        # Group paragraphs into sections of reasonable size
        current_section = ""
        section_count = 1

        for para in paragraphs:
            if len(current_section) > 800:  # Start new section
                if current_section.strip():
                    sections.append({
                        'title': f"Section {section_count}",
                        'content': current_section.strip(),
                        'page_number': 1,
                        'section_id': f"section_{section_count}"
                    })
                    section_count += 1
                current_section = para
            else:
                current_section += "\n\n" + para

        # Add final section
        if current_section.strip():
            sections.append({
                'title': f"Section {section_count}",
                'content': current_section.strip(),
                'page_number': 1,
                'section_id': f"section_{section_count}"
            })

        return sections

    def extract_keywords(self, text: str, top_k: int = 10) -> List[str]:
        """Extract important keywords from text."""
        # Tokenize and clean
        words = word_tokenize(text.lower())
        words = [self.stemmer.stem(word) for word in words 
                if word.isalpha() and word not in self.stop_words and len(word) > 2]

        # Get most frequent words
        word_freq = Counter(words)
        return [word for word, _ in word_freq.most_common(top_k)]

    def compute_semantic_similarity(self, query: str, documents: List[str]) -> np.ndarray:
        """Compute semantic similarity using sentence transformers."""
        try:
            # Generate embeddings
            query_embedding = self.embedder.encode([query])
            doc_embeddings = self.embedder.encode(documents)

            # Compute cosine similarity
            similarities = cosine_similarity(query_embedding, doc_embeddings)[0]
            return similarities
        except Exception as e:
            print(f"Error in semantic similarity computation: {e}")
            return np.zeros(len(documents))

    def compute_tfidf_similarity(self, query: str, documents: List[str]) -> np.ndarray:
        """Compute TF-IDF based similarity scores."""
        try:
            # Fit TF-IDF on documents + query
            all_texts = documents + [query]
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(all_texts)

            # Get query vector (last row) and document vectors
            query_vector = tfidf_matrix[-1]
            doc_vectors = tfidf_matrix[:-1]

            # Compute similarities
            similarities = cosine_similarity(query_vector, doc_vectors)[0]
            return similarities
        except Exception as e:
            print(f"Error in TF-IDF similarity computation: {e}")
            return np.zeros(len(documents))

    def compute_keyword_overlap(self, query_keywords: List[str], documents: List[str]) -> np.ndarray:
        """Compute keyword overlap scores."""
        scores = []

        for doc in documents:
            doc_keywords = set(self.extract_keywords(doc, top_k=20))
            query_keyword_set = set(query_keywords)

            if len(query_keyword_set) == 0:
                scores.append(0.0)
            else:
                overlap = len(doc_keywords.intersection(query_keyword_set))
                score = overlap / len(query_keyword_set)
                scores.append(score)

        return np.array(scores)

    def analyze_documents(self, pdf_directory: str, persona: str, job_description: str) -> Dict[str, Any]:
        """
        Main analysis function that processes PDFs and returns ranked sections.

        Args:
            pdf_directory: Directory containing PDF files
            persona: Description of the user persona
            job_description: Description of the job/task requirements

        Returns:
            Dictionary containing analysis results
        """
        start_time = time.time()

        # Find PDF files
        pdf_files = list(Path(pdf_directory).glob("*.pdf"))
        if not pdf_files:
            return {"error": "No PDF files found in directory"}

        print(f"Processing {len(pdf_files)} PDF files...")

        # Extract text from all PDFs
        documents = []
        all_sections = []

        for pdf_path in pdf_files:
            doc_data = self.extract_text_from_pdf(str(pdf_path))
            documents.append(doc_data)

            # Add document context to sections
            for section in doc_data['sections']:
                section['document'] = doc_data['filename']
                all_sections.append(section)

        if not all_sections:
            return {"error": "No sections extracted from documents"}

        print(f"Extracted {len(all_sections)} sections from documents")

        # Create combined query from persona and job description
        combined_query = f"{persona} {job_description}"
        query_keywords = self.extract_keywords(combined_query)

        # Extract content for similarity computation
        section_contents = [section['content'] for section in all_sections]

        # Compute similarity scores
        print("Computing similarity scores...")

        semantic_scores = self.compute_semantic_similarity(combined_query, section_contents)
        tfidf_scores = self.compute_tfidf_similarity(combined_query, section_contents)
        keyword_scores = self.compute_keyword_overlap(query_keywords, section_contents)

        # Combine scores with weights
        final_scores = (
            self.weights['semantic'] * semantic_scores +
            self.weights['tfidf'] * tfidf_scores +
            self.weights['keyword'] * keyword_scores
        )

        # Rank sections
        ranked_indices = np.argsort(final_scores)[::-1]

        # Prepare results
        results = {
            "persona": persona,
            "job_description": job_description,
            "total_documents": len(documents),
            "total_sections": len(all_sections),
            "processing_time": time.time() - start_time,
            "ranked_sections": []
        }

        # Add top sections with subsection analysis
        for i, idx in enumerate(ranked_indices):
            section = all_sections[idx]
            score = final_scores[idx]

            # Determine importance rank
            if i < len(all_sections) * 0.2:  # Top 20%
                importance = "high"
            elif i < len(all_sections) * 0.5:  # Top 50%
                importance = "medium"
            else:
                importance = "low"

            # Extract subsections for high and medium importance sections
            subsections = []
            if importance in ["high", "medium"]:
                subsections = self.extract_subsections(section['content'], combined_query)

            section_result = {
                "rank": i + 1,
                "section_id": section['section_id'],
                "document": section['document'],
                "title": section['title'],
                "page_number": section['page_number'],
                "relevance_score": float(score),
                "importance": importance,
                "semantic_score": float(semantic_scores[idx]),
                "tfidf_score": float(tfidf_scores[idx]),
                "keyword_score": float(keyword_scores[idx]),
                "content_preview": section['content'][:200] + "..." if len(section['content']) > 200 else section['content'],
                "subsections": subsections
            }

            results["ranked_sections"].append(section_result)

        print(f"Analysis completed in {results['processing_time']:.2f} seconds")
        return results

    def extract_subsections(self, content: str, query: str, max_subsections: int = 5) -> List[Dict]:
        """Extract and rank subsections from section content."""
        # Split content into sentences
        sentences = sent_tokenize(content)

        if len(sentences) < 6:  # Not enough content for subsections
            return []

        # Group sentences into subsections (3-4 sentences each)
        subsections = []
        current_subsection = []

        for sentence in sentences:
            current_subsection.append(sentence)

            if len(current_subsection) >= 3:  # Create subsection
                subsection_text = " ".join(current_subsection)
                if len(subsection_text.strip()) > 50:  # Minimum length check
                    subsections.append(subsection_text)
                current_subsection = []

        # Add remaining sentences as final subsection
        if current_subsection:
            final_text = " ".join(current_subsection)
            if len(final_text.strip()) > 50:
                subsections.append(final_text)

        if not subsections:
            return []

        # Rank subsections by relevance
        subsection_scores = self.compute_semantic_similarity(query, subsections)
        ranked_subsection_indices = np.argsort(subsection_scores)[::-1]

        # Return top subsections
        result_subsections = []
        for i, idx in enumerate(ranked_subsection_indices[:max_subsections]):
            result_subsections.append({
                "subsection_id": f"sub_{i+1}",
                "content": subsections[idx],
                "relevance_score": float(subsection_scores[idx]),
                "rank": i + 1
            })

        return result_subsections

def main():
    """Main execution function."""
    # Initialize analyzer
    analyzer = PersonaDrivenDocumentAnalyzer()

    # Define input/output directories
    input_dir = "/app/input"
    output_dir = "/app/output"

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Read persona and job description from input files
    try:
        with open(os.path.join(input_dir, "persona.txt"), "r") as f:
            persona = f.read().strip()

        with open(os.path.join(input_dir, "job_description.txt"), "r") as f:
            job_description = f.read().strip()

    except FileNotFoundError as e:
        print(f"Error: Required input files not found - {e}")
        return

    # Process documents
    results = analyzer.analyze_documents(input_dir, persona, job_description)

    # Save results
    output_file = os.path.join(output_dir, "analysis_results.json")
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"Analysis complete! Results saved to {output_file}")

    # Print summary
    if "error" not in results:
        print(f"\nSummary:")
        print(f"- Processed {results['total_documents']} documents")
        print(f"- Analyzed {results['total_sections']} sections")
        print(f"- Processing time: {results['processing_time']:.2f} seconds")
        print(f"- Top 5 most relevant sections:")

        for i, section in enumerate(results['ranked_sections'][:5]):
            print(f"  {i+1}. {section['title']} (Score: {section['relevance_score']:.3f})")

if __name__ == "__main__":
    main()
