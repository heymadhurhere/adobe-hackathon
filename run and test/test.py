import fitz

doc = fitz.open("input/6874ef2e50a4a_adobe_india_hackathon_challenge_doc.pdf")
for page_num, page in enumerate(doc, start=1):
    print(f"--- Page {page_num} ---")
    text = page.get_text("text")  # simpler extractor
    if text.strip():
        print(text)
    else:
        print("<< No text detected on this page >>")
