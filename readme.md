# Adobe India Hackathon: Connecting the Dots Challenge

This repository contains the solutions for Round 1A and Round 1B of the Adobe India Hackathon, focusing on intelligent PDF processing.

## Project Overview

The "Connecting the Dots" Challenge aims to transform traditional PDF reading into an intelligent, interactive experience. This solution addresses two key aspects: extracting structured outlines from PDFs and performing persona-driven content analysis on document collections.

## Project Structure

The repository is organized as follows:

.
├── Dockerfile                      # Dockerfile for Round 1A solution (outline extraction)
├── HACKATHON/
│   ├── 1a/
│   │   ├── main.py                 # Python script for Round 1A solution
│   │   └── requirements.txt        # Python dependencies for Round 1A
│   └── 1b/
│       ├── Dockerfile              # Dockerfile for Round 1B solution (persona-driven analysis)
│       ├── main.py                 # Python script for Round 1B solution
│       ├── Collection 1/           # Sample input for Test Case 1 (PDFs and challenge1b_input.json)
│       │   ├── PDFs/
│       │   └── challenge1b_input.json
│       ├── Collection 2/           # Sample input for Test Case 2
│       │   ├── PDFs/
│       │   └── challenge1b_input.json
│       └── Collection 3/           # Sample input for Test Case 3
│           ├── PDFs/
│           └── challenge1b_input.json
├── app/                            # Local directory for Docker volume mounts during runtime
│   ├── input/                      # Input PDFs (and persona.txt/job_description.txt for R1B)
│   └── output/                     # Output JSON files
└── problem statement.pdf           # Original problem statement document

## Round 1A: Understand Your Document (Outline Extraction)

This round focuses on extracting a structured outline from PDF documents.

### Mission
The mission is to build an intelligent system that can extract a structured outline (Title, H1, H2, and H3 headings with their page numbers) from raw PDF documents and output it in a clean, hierarchical JSON format.

### Solution Requirements
* **Input:** The solution accepts a PDF file (up to 50 pages).
* **Extraction:** It extracts the document Title, and Headings (H1, H2, H3) including their level, text, and page number.
* **Output:** It generates a valid JSON file in the specified hierarchical format.

### Constraints
* **Architecture:** Compatible with AMD64 architecture.
* **GPU:** No GPU dependencies are allowed.
* **Model Size:** If any models are used, their total size should not exceed 200MB.
* **Connectivity:** The solution must work offline, meaning no network or internet calls during execution.
* **Execution Time:** The processing time should be $\le$ 10 seconds for a 50-page PDF.
* **Runtime Environment:** The solution is expected to run on a system with 8 CPUs and 16 GB RAM configurations.

### Approach (`HACKATHON/1a/main.py`)
The `EnhancedHeadingExtractor` class in `HACKATHON/1a/main.py` implements a comprehensive heuristic-based approach to identify headings:

1.  **Detailed Text Extraction:** Utilizes `PyMuPDF` (`fitz`) to extract text blocks along with their layout properties such as font size, bold status, and precise `(x, y)` coordinates and dimensions. It also incorporates a heuristic to intelligently skip table-like content to prevent misidentification of table data as headings.
2.  **Vertical Spacing Analysis:** Analyzes the vertical spacing between consecutive text elements. Larger gaps often indicate a new section or heading, contributing to its score.
3.  **Hierarchical Numbering Detection:** Employs regular expressions to identify common numerical and alphabetical hierarchical patterns (e.g., "1.", "1.1", "(A)", "I.") and directly infers the heading level (H1, H2, H3). This is given high priority in classification. This also includes logic to combine a numbering prefix with its subsequent text if they are parsed separately.
4.  **Comprehensive Scoring System:** Assigns a "heading score" to each candidate text element based on multiple weighted heuristics:
    * **Font Size Ratio:** Compares the font size of a text element to the most common (body) font size in the document; larger ratios indicate higher importance.
    * **Bold Formatting:** Text rendered in bold typically signifies importance.
    * **Spacing Patterns:** Detects significantly larger spacing above or below text, characteristic of headings.
    * **Positional Alignment:** Checks if text is centered or has minimal indentation from the left margin.
    * **Text Characteristics:** Evaluates if text is in ALL CAPS or Title Case, and if its length falls within an typical range for a heading.
    * **Content Keywords:** Looks for common keywords (e.g., "Introduction," "Summary," "Chapter," "Appendix") that are frequently used in headings.
    * **Font Family Indicators:** Identifies font names containing terms like "bold," "heavy," or "semibold".
    * **Page-Top Positioning:** Assigns a bonus score to text appearing near the top of a page, especially after the first page.
5.  **Dynamic Level Assignment:** The final heading level (H1, H2, H3) is determined first by any detected hierarchical numbering. Otherwise, it leverages the font size hierarchy and dynamically promotes levels based on the combined comprehensive score.
6.  **Post-processing for Refinement:** The extracted headings are sorted by page and calculated score. Duplicates are removed, and specific logic ensures the main document title is correctly identified and not replicated within the outline list.

### Dependencies (`HACKATHON/1a/requirements.txt`)
* `PyMuPDF>=1.23.0`
* `argparse`
* `pathlib`

### Dockerfile (Root `Dockerfile`)

```dockerfile
# Use a slim Python image for AMD64 architecture
FROM python:3.9-slim-buster

# Specify the platform explicitly as recommended in the problem statement
ARG TARGETPLATFORM=linux/amd64

# Install system dependencies required for PyMuPDF (fitz) and build tools.
# 'build-essential' provides compilers (gcc, g++) needed for Python packages with C extensions.
# 'libfreetype6-dev' is a development library for FreeType, often a dependency for PDF rendering libraries.
# 'apt-get clean' and 'rm -rf' reduce the final image size by clearing apt caches.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libfreetype6-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container.
# All subsequent commands will be executed relative to this directory.
WORKDIR /app

# Copy the requirements file from the repository's 'HACKATHON/1a' directory
# and install the Python dependencies.
# '--no-cache-dir' prevents pip from storing cached files, further reducing image size.
COPY HACKATHON/1a/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the main application script from 'HACKATHON/1a' into the container's working directory.
COPY HACKATHON/1a/main.py main.py

# Create necessary directories as expected by the application
# These directories are intended to be volume-mounted at runtime for input/output.
# Creating them here ensures they exist even if not mounted, preventing potential errors.
RUN mkdir -p /app/input /app/output

# Define the command that will be executed when the container starts.
# The 'main.py' script is designed to automatically process files within '/app/input'
# and write results to '/app/output', aligning with the hackathon's execution requirements.
CMD ["python", "main.py"]