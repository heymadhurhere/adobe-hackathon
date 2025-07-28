# Adobe India Hackathon: Connecting the Dots Challenge

This repository contains the solutions for Round 1A and Round 1B of the Adobe India Hackathon, focusing on intelligent PDF processing.

## Project Overview

The "Connecting the Dots" Challenge aims to transform traditional PDF reading into an intelligent, interactive experience. This solution addresses two key aspects: extracting structured outlines from PDFs and performing persona-driven content analysis on document collections.

## Project Structure

The repository is organized as follows:
```

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
```
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

## Build and Run Instructions for Round 1A

1.  **Prepare Local Directories:**
    * Create an `input` directory and an `output` directory in the root of the local repository (e.g., `my_hackathon_repo/app/input/` and `my_hackathon_repo/app/output/`).
    * Place your sample PDF files (e.g., `file01.pdf`, `file03.pdf`, `file04.pdf`, `file05.pdf`, `sample.pdf`, `sample2.pdf`) into the `app/input/` directory.

2.  **Build the Docker Image:**
    * Open your terminal or command prompt.
    * Navigate to the root directory of your repository (where the `Dockerfile` for Round 1A is located).
    * Execute the following command to build the Docker image. Replace `mysolutionname` with a chosen image name and `somerandomidentifier` with a desired tag:
        ```bash
        docker build --platform linux/amd64 -t mysolutionname:somerandomidentifier .
        ```

3.  **Run the Docker Container:**
    * From the root directory of the repository, execute the following command. This will mount the local `app/input` and `app/output` directories to the container's `/app/input` and `/app/output`, respectively.
        ```bash
        docker run --rm -v "$(pwd)/app/input:/app/input" -v "$(pwd)/app/output:/app/output" --network none mysolutionname:somerandomidentifier
        ```
    * Upon successful execution, the generated JSON outline files (e.g., `sample.json`, `file03.json`) will be available in the local `app/output/` directory.


# Round 1B: Persona-Driven Document Intelligence

This document details the Round 1B solution, focusing on persona-driven document analysis.

## Mission
To build a system that acts as an intelligent document analyst, extracting and prioritizing the most relevant sections from a collection of documents based on a specific persona and their "job-to-be-done".

## Input Specification
* **Document Collection:** 3-10 related PDF files. These documents can be from any domain (e.g., research papers, textbooks, financial reports).
* **Persona Definition:** A textual description of the user's role, expertise, and focus areas (e.g., "HR professional"). This is expected to be in a file named `persona.txt` within the input directory.
* **Job-to-be-Done:** A concrete task the persona needs to accomplish (e.g., "Create and manage fillable forms for onboarding and compliance"). This is expected to be in a file named `job_description.txt` within the input directory.
* The solution must be generic to generalize to diverse document types, personas, and job descriptions.

## Output Specification
The output should be a JSON file (e.g., `analysis_results.json`) containing:
1.  **Metadata:** Information about the input documents, persona, job-to-be-done, and the processing timestamp.
2.  **Extracted Section:** A ranked list of relevant sections, including the source document filename, page number, section title, and an `importance_rank` (e.g., "high", "medium", "low").
3.  **Sub-section Analysis:** For highly relevant sections, a more granular analysis providing refined text content and page numbers for specific subsections.

## Constraints
* **CPU:** The solution must run exclusively on CPU.
* **Model Size:** The total size of any models used must be $\le$ 1GB.
* **Processing Time:** The solution should process a document collection (3-5 documents) within $\le$ 60 seconds.
* **Connectivity:** No internet access is permitted during execution.

## Approach (`HACKATHON/1b/main.py`)
The `PersonaDrivenDocumentAnalyzer` class in `HACKATHON/1b/main.py` utilizes a hybrid scoring approach:

1.  **Document and Section Extraction:** Extracts full text from all PDFs in the specified input directory using `PyMuPDF`. It cleans the text and attempts to identify logical sections within pages. If no clear structure is found, it falls back to creating sections based on paragraph breaks.
2.  **Query Formulation:** Concatenates the `persona` and `job_description` into a single comprehensive query string that represents the user's information need.
3.  **Keyword Extraction:** Extracts important keywords from the combined query and all document sections using NLTK for tokenization, stop word removal, and stemming, which helps in identifying core topics.
4.  **Hybrid Relevance Scoring:** Calculates a relevance score for each document section based on three components:
    * **Semantic Similarity:** Uses a pre-trained `SentenceTransformer` model (`all-MiniLM-L6-v2`, approximately 80MB) to generate embeddings for the query and document sections, then computes cosine similarity. This captures conceptual alignment beyond exact keyword matches.
    * **TF-IDF Similarity:** Employs `TfidfVectorizer` to transform text into TF-IDF features and computes cosine similarity to identify sections with high term frequency-inverse document frequency overlap with the query.
    * **Keyword Overlap:** Quantifies the proportion of shared keywords between the query and each document section.
    These three scores are then combined using a weighted average (`semantic`: 0.4, `tfidf`: 0.3, `keyword`: 0.3) to produce a final, comprehensive relevance score for each section.
5.  **Section Ranking and Importance:** Sections are ranked in descending order of their final relevance scores. An `importance_rank` (e.g., "high", "medium", "low") is assigned dynamically based on percentile thresholds (e.g., top 20% for "high", next 30% for "medium").
6.  **Granular Subsection Analysis:** For sections identified as "high" or "medium" importance, the content is further segmented into smaller subsections (typically groups of 3-4 sentences). These subsections are then also ranked based on their semantic similarity to the original query, providing finer-grained insights.
7.  **JSON Output:** The system aggregates all extracted metadata, ranked sections, and detailed subsection analyses into a structured JSON output file (`analysis_results.json`).

## Dependencies (Inferred for `HACKATHON/1b/main.py`)
* `PyMuPDF`
* `numpy`
* `sentence-transformers`
* `scikit-learn`
* `nltk` (requires `punkt` and `stopwords` data to be downloaded at runtime if not present)

## Dockerfile (`HACKATHON/1b/Dockerfile`)
This Dockerfile should be placed inside the `HACKATHON/1b/` directory of the repository.

```dockerfile
# Use a slim Python image for AMD64 architecture. 'bookworm' is a newer Debian version that provides recent packages.
FROM python:3.9-slim-bookworm

# Specify the platform explicitly for Docker buildx compatibility, ensuring the correct architecture.
ARG TARGETPLATFORM=linux/amd64

# Install system dependencies:
# - build-essential: Provides compilers (gcc, g++) needed for Python packages with C extensions (e.g., numpy, which scikit-learn depends on).
# - libfreetype6-dev: Development library for FreeType, often a dependency for PyMuPDF (fitz).
# - ca-certificates: Important for secure network connections, even if the primary operation is offline,
#   as model downloads or NLTK data downloads during build might require it.
# apt-get clean and rm -rf reduce the final image size by clearing package caches.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libfreetype6-dev \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container. All subsequent commands will operate relative to /app.
WORKDIR /app

# Copy the main application script for Round 1B into the container.
COPY HACKATHON/1b/main.py main.py

# Dynamically create a requirements.txt file for Round 1B's specific Python dependencies.
# This step is explicitly added because a separate requirements.txt for 1B was not provided,
# and its dependencies are distinct from Round 1A.
RUN echo "PyMuPDF>=1.23.0" >> requirements.txt \
    && echo "numpy" >> requirements.txt \
    && echo "sentence-transformers" >> requirements.txt \
    && echo "scikit-learn" >> requirements.txt \
    && echo "nltk" >> requirements.txt

# Install the Python dependencies listed in the newly created requirements.txt.
# --no-cache-dir prevents pip from storing downloaded packages, helping keep the image size minimal.
RUN pip install --no-cache-dir -r requirements.txt

# Download NLTK data necessary for text processing. This must be done after 'nltk' is installed.
RUN python -c "import nltk; nltk.download('punkt', quiet=True); nltk.download('stopwords', quiet=True)"

# Create the input and output directories within the container.
# These directories are placeholders where local volumes will be mounted at runtime.
# For Round 1B, '/app/input' will contain both PDF documents and the persona/job description text files.
RUN mkdir -p /app/input /app/output

# Define the default command to execute when the container starts.
# The 'main.py' script for Round 1B is designed to automatically read from '/app/input'
# and write results to '/app/output', aligning with the hackathon's volume mount setup.
CMD ["python", "main.py"]

## Build and Run Instructions for Round 1B

To test the Round 1B solution for any of the provided test cases (e.g., "Travel Planner", "Create Manageable Forms", "Dinner Menu Planning"), follow these steps:

1.  **Prepare a Dedicated Input Directory for a Test Case:**
    * **Choose a Collection:** Select one of the `Collection` subdirectories (e.g., `HACKATHON/1b/Collection 1/`, `Collection 2/`, or `Collection 3/`).
    * **Create Local Input Directory:** In the root of the repository, create a new local directory to serve as the input for this specific test case (e.g., `my_r1b_test_input/`).
    * **Copy PDFs:** Copy all PDF files from the selected collection's `PDFs/` subdirectory (e.g., `HACKATHON/1b/Collection 1/PDFs/`) into the newly created `my_r1b_test_input/` directory.
    * **Create Persona and Job Description Files:**
        * Open the corresponding `challenge1b_input.json` file for the chosen collection (e.g., `HACKATHON/1b/Collection 1/challenge1b_input.json`).
        * Create a text file named `persona.txt` inside the `my_r1b_test_input/` directory. Copy the content of the `"role"` field from the `challenge1b_input.json` into this `persona.txt` file.
            * *Example for Collection 1:* `Travel Planner`
        * Create a text file named `job_description.txt` inside the `my_r1b_test_input/` directory. Copy the content of the `"task"` field from the `challenge1b_input.json` into this `job_description.txt` file.
            * *Example for Collection 1:* `Plan a trip of 4 days for a group of 10 college friends.`
    * **Ensure Output Directory Exists:** Make sure an empty `app/output/` directory exists at the root level of the repository.

2.  **Build the Docker Image for Round 1B:**
    * Open a terminal or command prompt.
    * Navigate to the root directory of the repository.
    * Execute the following command to build the Docker image. The `-f HACKATHON/1b/Dockerfile` flag tells Docker to use the Dockerfile located in that specific subdirectory. Replace `mysolutionname` with a chosen image name and `somerandomidentifier` with a desired tag:
        ```bash
        docker build --platform linux/amd64 -t mysolutionname:somerandomidentifier -f HACKATHON/1b/Dockerfile .
        ```

3.  **Run the Docker Container for Round 1B:**
    * From the root directory of the repository, execute the following command. This command mounts the prepared `my_r1b_test_input/` directory (containing both PDFs and the persona/job description files) to the container's `/app/input`, and the local `app/output/` directory to the container's `/app/output`.
        ```bash
        docker run --rm -v "$(pwd)/my_r1b_test_input:/app/input" -v "$(pwd)/app/output:/app/output" --network none mysolutionname:somerandomidentifier
        ```
    * Upon successful execution, the `analysis_results.json` file, containing the persona-driven document analysis for the chosen test case, will be generated and saved in the local `app/output/` directory.