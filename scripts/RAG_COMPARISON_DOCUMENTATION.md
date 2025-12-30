# LLM RAG Accuracy Comparison - Technical Documentation

This document describes the complete workflow for comparing multiple Large Language Models (LLMs) on Retrieval-Augmented Generation (RAG) accuracy using Vietnamese PDF documents from UEL (University of Economics and Law).

---

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Fact Table Creation](#fact-table-creation)
4. [PDF Embedding Pipeline](#pdf-embedding-pipeline)
5. [Comparison Framework](#comparison-framework)
6. [Accuracy Calculation](#accuracy-calculation)
7. [Evaluation Results](#evaluation-results)
8. [Key Findings](#key-findings)

---

## Overview

This project evaluates the accuracy of 5 different LLM models when answering questions based on retrieved context from a vector database. The system uses:

- **Embedding Model**: Google Gemini `text-embedding-004` (768 dimensions)
- **Vector Store**: MongoDB Atlas with cosine similarity search
- **Source Data**: 9 Vietnamese PDF documents from UEL
- **Ground Truth**: 10 Q&A pairs manually extracted from PDFs

### Models Evaluated

| Model Name | Provider | Model ID |
|------------|----------|----------|
| Gemini 2.5 Flash | Google | `gemini-2.5-flash` |
| Gemini 2.5 Pro | Google | `gemini-2.5-pro` |
| Llama 3.3 70B | Groq | `llama-3.3-70b-versatile` |
| GPT-OSS 120B | Groq | `openai/gpt-oss-120b` |
| Kimi K2 | Groq | `moonshotai/kimi-k2-instruct-0905` |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        PDF Documents                             │
│   (9 Vietnamese PDFs about UEL - library, history, policies)    │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Text Extraction (pypdf)                       │
│            + Text Cleaning (regex for Vietnamese)                │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Text Chunking (RecursiveCharacterTextSplitter)      │
│           Chunk Size: 1000 chars | Overlap: 200 chars            │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│           Embedding (Gemini text-embedding-004)                  │
│                    768 dimensions per chunk                      │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     MongoDB Atlas Vector Store                   │
│   Collection: "pdf" | Index: "vector_index" | Cosine Similarity  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Fact Table Creation

### Purpose

The fact table serves as ground truth for evaluating LLM accuracy. It contains question-answer pairs manually extracted from the source PDF documents.

### Structure

The fact table is stored in `scripts/fact_table.json` with the following schema:

```json
{
  "description": "Fact table for evaluating LLM RAG accuracy",
  "source_files": ["list of 9 PDF files"],
  "questions_and_answers": [
    {
      "id": 1,
      "question": "Vietnamese question text",
      "answer": "Expected answer with key facts",
      "source": "source_document.pdf",
      "category": "category name"
    }
  ],
  "metadata": {
    "created_date": "2025-12-31",
    "total_questions": 10,
    "language": "Vietnamese"
  }
}
```

### Categories

Questions are categorized into the following types:

| Category | Description | Example |
|----------|-------------|---------|
| `facilities` | Library resources, buildings | Document counts, locations |
| `contact` | Addresses, phone numbers | University address |
| `education` | Programs, degrees | Number of majors |
| `statistics` | Staff counts, enrollment | Personnel numbers |
| `regulations` | Academic policies | Discipline rules |
| `scholarship` | Financial aid | Scholarship percentages |
| `ranking` | University rankings | QS Rankings |
| `awards` | Achievements | Labor medals |

### Source Files

The fact table was created from these 9 PDF documents:

1. `gioi_thieu_thu_vien.pdf` - Library introduction
2. `hieu_truong_pho_hieu_truong.pdf` - Rector information
3. `lich_su_hinh_thanh_phat_trien_uel.pdf` - UEL history
4. `Quy dinh Danh gia KQRL - Signed (3).pdf` - Student evaluation regulations
5. `Quy đinh xet cap hoc bong sinh vien - Signed (3).pdf` - Scholarship policies
6. `so tay sinh vien 2025.pdf` - Student handbook 2025
7. `TB chế độ chính sách sv L1 2025-2026 - Signed (2).pdf` - Student policies
8. `Thong bao 251_Tuyen sinh song nganh noi bo - Signed.pdf` - Dual degree admission
9. `Thông tin lưu ý dành cho K25.pdf` - K25 student information

---

## PDF Embedding Pipeline

### Script Location

`scripts/embed_pdfs_to_mongo.py`

### Pipeline Steps

#### 1. PDF Text Extraction

Uses `pypdf` library to extract raw text from PDF files:

```python
from pypdf import PdfReader

def extract_text_from_pdf(filepath: str) -> str:
    reader = PdfReader(filepath)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text
```

#### 2. Text Cleaning (Critical for Vietnamese)

PDF extraction often produces noisy text with:
- Multiple spaces between characters
- Broken words across lines
- Inconsistent whitespace

The `clean_text()` function addresses these issues:

```python
def clean_text(text: str) -> str:
    """
    Clean PDF-extracted text by removing noise and normalizing whitespace.
    This significantly improves embedding quality for Vietnamese text.
    """
    # Replace multiple spaces/tabs with single space
    text = re.sub(r'[ \t]+', ' ', text)
    
    # Replace multiple newlines with double newline (paragraph break)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    # Remove spaces before/after newlines
    text = re.sub(r' *\n *', '\n', text)
    
    # Fix common PDF issues: rejoin words split by newlines
    # (lowercase Vietnamese letter followed by newline followed by lowercase letter)
    vietnamese_lower = r'a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ'
    text = re.sub(f'([{vietnamese_lower}])\n([{vietnamese_lower}])', r'\1 \2', text)
    
    # Remove single newlines within paragraphs (but keep double newlines)
    text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
    
    # Clean up any remaining multiple spaces
    text = re.sub(r' +', ' ', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text
```

**Impact**: Text cleaning typically removes 10-15% of noise characters and significantly improves semantic search accuracy.

#### 3. Text Chunking

Uses LangChain's `RecursiveCharacterTextSplitter`:

```python
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,        # Maximum characters per chunk
    chunk_overlap=200,      # Overlap between chunks
    length_function=len,
    separators=["\n\n", "\n", ". ", " ", ""]  # Priority order
)
```

**Configuration Rationale**:
- **1000 chars**: Balances context retention with embedding precision
- **200 char overlap**: Ensures key information isn't split at chunk boundaries
- **Separators**: Prioritizes paragraph breaks, then sentences, then words

#### 4. Embedding Generation

Uses Gemini's `text-embedding-004` model:

```python
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004",
    google_api_key=GEMINI_API_KEY
)
```

**Model Specifications**:
- Dimensions: 768
- Max tokens: 2048
- Multilingual support (Vietnamese)

#### 5. MongoDB Atlas Storage

Documents are stored with this structure:

```json
{
  "text": "cleaned chunk content",
  "embedding": [0.123, -0.456, ...],  // 768 floats
  "source": "filename.pdf",
  "filename": "filename.pdf",
  "type": "pdf"
}
```

### Vector Index Configuration

Create a vector search index in MongoDB Atlas:

**Index Name**: `vector_index`

**Index Definition**:
```json
{
  "mappings": {
    "dynamic": true,
    "fields": {
      "embedding": {
        "dimensions": 768,
        "similarity": "cosine",
        "type": "knnVector"
      }
    }
  }
}
```

---

## Comparison Framework

### Script Location

`scripts/llm_rag_comparison.ipynb` (Jupyter Notebook)

### RAG Workflow

1. **Load Fact Table**: Read Q&A pairs from `fact_table.json`
2. **Initialize Vector Store**: Connect to MongoDB Atlas
3. **Retrieve Context**: For each question, retrieve top-k similar chunks
4. **Query Models**: Send context + question to each LLM
5. **Calculate Accuracy**: Compare model answer to ground truth
6. **Aggregate Results**: Generate summary statistics

### Context Retrieval

```python
def retrieve_context(question: str, k: int = 5) -> str:
    """Retrieve relevant context from vector store."""
    docs = vector_store.similarity_search(question, k=k)
    context = "\n\n".join([doc.page_content for doc in docs])
    return context
```

### RAG Prompt Template

```python
def create_rag_prompt(question: str, context: str) -> str:
    return f"""Dựa vào ngữ cảnh được cung cấp dưới đây, hãy trả lời câu hỏi một cách chính xác và ngắn gọn.
Chỉ sử dụng thông tin từ ngữ cảnh để trả lời. Nếu không tìm thấy thông tin, hãy nói "Không tìm thấy thông tin".

NGỮ CẢNH:
{context}

CÂU HỎI: {question}

TRẢ LỜI:"""
```

---

## Accuracy Calculation

### Methodology

Accuracy is calculated based on **key fact extraction** rather than exact text matching:

```python
def calculate_accuracy(model_answer: str, ground_truth: str) -> float:
    # 1. Extract key facts from ground truth
    gt_facts = extract_key_facts(ground_truth)
    
    # 2. Check how many facts appear in model answer
    matches = 0
    for fact in gt_facts:
        if fact.lower() in model_answer.lower():
            matches += 1
    
    # 3. Return proportion of matched facts
    return matches / len(gt_facts)
```

### Key Fact Extraction

The `extract_key_facts()` function identifies:

1. **Numbers**: Including decimals and percentages (e.g., `428`, `48,5%`, `66.419`)
2. **Proper Nouns**: Vietnamese names and titles (e.g., `PGS.TS`, `Huân chương`)
3. **Dates/Years**: (e.g., `2025`, `30/6/2025`)

### Scoring

| Accuracy Range | Interpretation |
|----------------|----------------|
| 90-100% | Perfect/Near-perfect answer |
| 70-89% | Good answer with minor omissions |
| 50-69% | Partial answer |
| 0-49% | Poor/Incorrect answer |

---

## Evaluation Results

### Summary (as of 2025-12-31)

| Rank | Model | Avg Accuracy | Perfect Scores (≥90%) |
|------|-------|--------------|----------------------|
| 1 | **Gemini 2.5 Flash** | 83.0% | 5/10 |
| 1 | **Llama 3.3 70B** | 83.0% | 5/10 |
| 3 | Gemini 2.5 Pro | 78.2% | 5/10 |
| 4 | Kimi K2 | 65.4% | 4/10 |
| 5 | GPT-OSS 120B | 49.9% | 2/10 |

### Detailed Statistics

| Model | Max | Min | Std Dev |
|-------|-----|-----|---------|
| Gemini 2.5 Flash | 100% | 50% | ~18% |
| Llama 3.3 70B | 100% | 50% | ~18% |
| Gemini 2.5 Pro | 100% | 33% | ~22% |
| Kimi K2 | 100% | 5% | ~35% |
| GPT-OSS 120B | 100% | 0% | ~40% |

---

## Key Findings

### 1. Text Cleaning is Critical

**Before cleaning**: Average accuracy ~30% across all models  
**After cleaning**: Average accuracy improved to 65-83%

The Vietnamese text from PDF extraction contained significant noise that degraded embedding quality. The `clean_text()` function was essential for achieving usable accuracy.

### 2. Smaller Models Can Match Larger Ones

Gemini 2.5 Flash (smaller, faster model) matched Llama 3.3 70B in accuracy, suggesting that for RAG tasks with good context retrieval, model size is less important than prompt quality.

### 3. Context Quality Matters More Than Model Size

All models performed poorly when retrieval returned irrelevant chunks. The vector index configuration and text cleaning had more impact on accuracy than switching between LLMs.

### 4. Vietnamese-Specific Processing Required

Standard text processing pipelines designed for English don't handle Vietnamese well. Key adaptations included:
- Vietnamese character ranges in regex patterns
- Handling of tone marks and diacritics
- Word boundary detection for Vietnamese

---

## Files Reference

| File | Purpose |
|------|---------|
| `scripts/embed_pdfs_to_mongo.py` | PDF extraction, cleaning, and embedding |
| `scripts/fact_table.json` | Ground truth Q&A pairs |
| `scripts/llm_rag_comparison.ipynb` | Evaluation notebook |
| `scripts/evaluation_results.json` | Saved evaluation results |
| `scripts/extract_pdf.py` | Standalone PDF text extraction |
| `data/*.pdf` | Source PDF documents |

---

## Environment Setup

### Required Environment Variables

```env
GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key
MONGODB_URI2=mongodb+srv://...
MONGODB_DB_NAME2=thesis
```

### Required Python Packages

```
pypdf
langchain-text-splitters
langchain-google-genai
langchain-mongodb
pymongo
google-genai
groq
python-dotenv
pandas
tabulate
```

---

## Running the Evaluation

### Step 1: Embed PDFs

```bash
cd scripts
python embed_pdfs_to_mongo.py
```

This will:
1. Extract text from all PDFs in `data/`
2. Clean the text using Vietnamese-aware regex
3. Split into chunks (1000 chars, 200 overlap)
4. Generate embeddings using Gemini
5. Store in MongoDB Atlas

### Step 2: Create Vector Index

In MongoDB Atlas UI:
1. Navigate to your cluster → Database → Collection "pdf"
2. Go to "Search Indexes" tab
3. Create index with name `vector_index`
4. Use the JSON definition provided above

### Step 3: Run Evaluation Notebook

Open `scripts/llm_rag_comparison.ipynb` in Jupyter/VS Code and run all cells sequentially.

Results will be saved to `scripts/evaluation_results.json`.

---

*Documentation generated: 2025-12-31*
