import os, json, re, fitz

INPUT_DIR = "input"
OUTPUT_DIR = "output"

def is_heading(line: str):
    # number-based heading detection
    m = re.match(r'^(\d+(?:\.\d+)*)\s+(.*)', line)
    if m:
        numbering = m.group(1)
        level = numbering.count(".") + 1
        if level == 1: return "H1"
        if level == 2: return "H2"
        return "H3"
    # uppercase heuristic
    if len(line.split()) <= 6 and line.isupper():
        return "H1"
    return None

def process_pdf(input_path, output_path):
    doc = fitz.open(input_path)
    outline = []
    title = None
    for page_num, page in enumerate(doc, start=1):
        lines = page.get_text("text").split("\n")
        for i, line in enumerate(lines):
            clean = line.strip()
            if not clean:
                continue
            if page_num == 1 and title is None:
                title = clean  # first text as title
            level = is_heading(clean)
            if level:
                outline.append({"level": level, "text": clean, "page": page_num})
    if not title:
        title = os.path.basename(input_path)
    data = {"title": title, "outline": outline}
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ Finished: {output_path}")

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for fn in os.listdir(INPUT_DIR):
        if fn.lower().endswith(".pdf"):
            process_pdf(os.path.join(INPUT_DIR, fn),
                        os.path.join(OUTPUT_DIR, fn.replace(".pdf", ".json")))
