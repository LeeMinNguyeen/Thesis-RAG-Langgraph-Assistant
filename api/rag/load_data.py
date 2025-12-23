import os
import glob
import time
import pickle

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import MongoDBAtlasVectorSearch

# Local imports
from config import get_config

# --- Initialize shared objects for standalone execution ---
# These imports will initialize the llm and db objects
from api.llm import llm
from api.db import db

# Ensure DB connection is established
db.get_mongo_client()

# --- CACHE FILES ---
CACHE_DIR = os.path.dirname(os.path.abspath(__file__))
CLEANED_PAGES_CACHE = os.path.join(CACHE_DIR, "cache_cleaned_pages.pkl")
SPLIT_DOCS_CACHE = os.path.join(CACHE_DIR, "cache_split_docs.pkl")
TAGGED_DOCS_CACHE = os.path.join(CACHE_DIR, "cache_tagged_docs.pkl")

# --- INTERNAL VECTOR LOGIC ---
def _get_vector_store(cfg):
    if not db.client:
        raise ConnectionError("MongoDB connection failed - db.client is None")
    
    collection = db.client[cfg["MONGODB_DB_NAME"]][cfg["MONGODB_RAG_COLLECTION_NAME"]]
    embeddings = GoogleGenerativeAIEmbeddings(
        model=cfg["EMBEDDING_MODEL_ID"],
        google_api_key=cfg["GEMINI_API_KEY"]
    )
    return MongoDBAtlasVectorSearch(
        collection=collection,
        embedding=embeddings,
        index_name=cfg["MONGODB_RAG_INDEX_NAME"]
    )

def clear_and_upload(docs):
    cfg = get_config()
    print("[Ingest] Connecting to MongoDB...")
    
    # 1. Clear old data
    if not db.client:
        raise ConnectionError("MongoDB connection failed - db.client is None")
    db.client[cfg["MONGODB_DB_NAME"]][cfg["MONGODB_RAG_COLLECTION_NAME"]].delete_many({})
    print("[Ingest] Old collection cleared.")

    # 2. Upload new
    if not docs: return
    try:
        vs = _get_vector_store(cfg)
        vs.add_documents(docs)
        print(f"[Ingest] Successfully uploaded {len(docs)} chunks.")
    except Exception as e:
        print(f"[Ingest Error] Upload failed: {e}")

# --- PIPELINE STEPS ---

def get_pdf_files():

    current_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_dir = os.path.join(current_dir, "pdf")
    
    print(f"[Debug] Đang tìm PDF tại: {pdf_dir}")
    
    if not os.path.exists(pdf_dir):
        print(f"[Ingest] Creating folder: {pdf_dir}")
        os.makedirs(pdf_dir, exist_ok=True)
        return []
        
    files = glob.glob(os.path.join(pdf_dir, "*.pdf"))
    if not files:
        print(f"[Ingest Warning] Thư mục {pdf_dir} đang trống. Hãy bỏ file .pdf vào đó!")
    else:
        print(f"[Ingest] Tìm thấy {len(files)} file PDF.")
    return files

def process_documents(files):
    # 1. Load
    pages = []
    for f in files:
        print(f"Reading: {os.path.basename(f)}")
        loader = PyPDFLoader(f)
        pages.extend(loader.load())
    
    # 2. Clean
    cleaned = [p for p in pages if len(p.page_content.split()) > 20]
    
    # 3. Split
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=150)
    chunks = splitter.split_documents(cleaned)
    return chunks

def extract_metadata(chunks):
    """Extract metadata (title, keywords) from document chunks using shared llm object."""
    
    processed = []
    # Resume cache logic
    if os.path.exists(TAGGED_DOCS_CACHE):
        try: 
            with open(TAGGED_DOCS_CACHE, "rb") as f: processed = pickle.load(f)
        except: pass
    
    start = len(processed)
    print(f"[Ingest] Tagging {len(chunks) - start} chunks...")
    
    for i, doc in enumerate(chunks[start:], start=start):
        try:
            meta = llm.extract_document_metadata(doc.page_content)
            doc.metadata.update(meta)
            processed.append(doc)
            
            with open(TAGGED_DOCS_CACHE, "wb") as f: pickle.dump(processed, f)
            if i % 5 == 0: print(f"Tagged {i+1}/{len(chunks)}")
            time.sleep(0.5)
        except Exception as e:
            print(f"Error chunk {i}: {e}")
            processed.append(doc)
            
    return processed

def run_ingest():
    files = get_pdf_files()
    if not files: return

    # Check cache for split docs
    if os.path.exists(SPLIT_DOCS_CACHE):
        with open(SPLIT_DOCS_CACHE, "rb") as f: chunks = pickle.load(f)
        print(f"[Cache] Loaded {len(chunks)} chunks.")
    else:
        chunks = process_documents(files)
        with open(SPLIT_DOCS_CACHE, "wb") as f: pickle.dump(chunks, f)

    # Metadata & Upload
    final_docs = extract_metadata(chunks)
    clear_and_upload(final_docs)

if __name__ == "__main__":
    run_ingest()

