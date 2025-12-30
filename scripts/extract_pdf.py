from pypdf import PdfReader
import os
import json

data_dir = r"c:\Projects\Thesis-RAG-Langgraph-Assistant\data"
output_file = r"c:\Projects\Thesis-RAG-Langgraph-Assistant\scripts\pdf_content.json"

# Read all PDFs
all_content = {}
for filename in os.listdir(data_dir):
    if filename.endswith('.pdf'):
        filepath = os.path.join(data_dir, filename)
        try:
            reader = PdfReader(filepath)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            all_content[filename] = text
            print(f"Read: {filename} ({len(text)} chars)")
        except Exception as e:
            all_content[filename] = f"Error: {str(e)}"
            print(f"Error reading {filename}: {e}")

# Save to JSON
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(all_content, f, ensure_ascii=False, indent=2)

print(f"\nSaved to {output_file}")
print(f"Total files: {len(all_content)}")
