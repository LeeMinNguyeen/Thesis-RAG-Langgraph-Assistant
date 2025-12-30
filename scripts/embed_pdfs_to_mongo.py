"""
Script to embed PDF documents using Gemini embedding model and store in MongoDB Atlas.
Uses MONGODB_URI2 and MONGO_DB_NAME2 for the connection.
Includes text cleaning to improve embedding quality for Vietnamese text.
"""

import os
import re
import sys
import time
from dotenv import load_dotenv
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_core.documents import Document
from pymongo import MongoClient

# Load environment variables
load_dotenv()

# Configuration
MONGODB_URI = os.getenv("MONGODB_URI2")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME2")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
COLLECTION_NAME = "pdf"
EMBEDDING_MODEL = "models/text-embedding-004"
INDEX_NAME = "vector_index"

# Data directory
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def validate_config():
    """Validate that all required environment variables are set."""
    if not MONGODB_URI:
        raise ValueError("MONGODB_URI2 is not set in .env file")
    if not MONGODB_DB_NAME:
        raise ValueError("MONGODB_DB_NAME2 is not set in .env file")
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set in .env file")
    print("[Config] All environment variables validated.")
    print(f"  - MongoDB URI: {MONGODB_URI[:50]}...")
    print(f"  - Database: {MONGODB_DB_NAME}")
    print(f"  - Collection: {COLLECTION_NAME}")
    print(f"  - Embedding Model: {EMBEDDING_MODEL}")


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


def get_pdf_files():
    """Get all PDF files from the data directory."""
    if not os.path.exists(DATA_DIR):
        raise FileNotFoundError(f"Data directory not found: {DATA_DIR}")
    
    pdf_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.pdf')]
    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found in: {DATA_DIR}")
    
    print(f"\n[PDF] Found {len(pdf_files)} PDF files:")
    for f in pdf_files:
        print(f"  - {f}")
    
    return pdf_files


def extract_text_from_pdf(filepath: str) -> str:
    """Extract text content from a PDF file."""
    reader = PdfReader(filepath)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text


def load_and_split_documents():
    """Load PDFs, clean text, and split them into chunks."""
    pdf_files = get_pdf_files()
    
    documents = []
    total_chars_original = 0
    total_chars_cleaned = 0
    
    for pdf_file in pdf_files:
        filepath = os.path.join(DATA_DIR, pdf_file)
        print(f"\n[Processing] {pdf_file}")
        
        try:
            # Extract raw text
            raw_text = extract_text_from_pdf(filepath)
            total_chars_original += len(raw_text)
            
            # Clean the text
            cleaned_text = clean_text(raw_text)
            total_chars_cleaned += len(cleaned_text)
            
            print(f"  - Extracted: {len(raw_text):,} chars → Cleaned: {len(cleaned_text):,} chars")
            print(f"  - Noise removed: {len(raw_text) - len(cleaned_text):,} chars ({(1 - len(cleaned_text)/len(raw_text))*100:.1f}%)")
            
            # Create a document with metadata
            doc = Document(
                page_content=cleaned_text,
                metadata={
                    "source": pdf_file,
                    "filename": pdf_file,
                    "type": "pdf"
                }
            )
            documents.append(doc)
        except Exception as e:
            print(f"  - Error processing {pdf_file}: {e}")
            continue
    
    print(f"\n[Documents] Loaded {len(documents)} documents")
    print(f"[Cleaning] Total noise removed: {total_chars_original - total_chars_cleaned:,} chars")
    
    # Split documents into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
    chunks = text_splitter.split_documents(documents)
    print(f"[Chunks] Split into {len(chunks)} chunks")
    
    return chunks


def get_mongodb_client():
    """Create MongoDB client connection."""
    try:
        client = MongoClient(MONGODB_URI)
        # Test connection
        client.admin.command('ping')
        print("[MongoDB] Successfully connected to MongoDB Atlas")
        return client
    except Exception as e:
        raise ConnectionError(f"Failed to connect to MongoDB: {e}")


def clear_collection(client):
    """Clear the existing collection."""
    db = client[MONGODB_DB_NAME]
    collection = db[COLLECTION_NAME]
    
    count = collection.count_documents({})
    if count > 0:
        collection.delete_many({})
        print(f"[MongoDB] Cleared {count} existing documents from '{COLLECTION_NAME}' collection")
    else:
        print(f"[MongoDB] Collection '{COLLECTION_NAME}' is already empty")


def create_vector_index(client):
    """Create vector search index if it doesn't exist."""
    db = client[MONGODB_DB_NAME]
    collection = db[COLLECTION_NAME]
    
    # Check if index exists
    try:
        existing_indexes = list(collection.list_search_indexes())
        index_exists = any(idx.get("name") == INDEX_NAME for idx in existing_indexes)
    except Exception:
        index_exists = False
    
    if not index_exists:
        print(f"[MongoDB] Vector search index '{INDEX_NAME}' not found.")
        print("  Note: Create the index in MongoDB Atlas UI with this config:")
        print(f"""
  Index Name: {INDEX_NAME}
  Index Definition:
  {{
    "fields": [
      {{
        "type": "vector",
        "path": "embedding",
        "numDimensions": 768,
        "similarity": "cosine"
      }}
    ]
  }}
        """)
    else:
        print(f"[MongoDB] Vector search index '{INDEX_NAME}' already exists")


def embed_and_store(chunks, client):
    """Embed document chunks and store in MongoDB."""
    print("\n[Embedding] Initializing Gemini embedding model...")
    
    embeddings = GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        google_api_key=GEMINI_API_KEY
    )
    
    # Get collection
    collection = client[MONGODB_DB_NAME][COLLECTION_NAME]
    
    print(f"[Embedding] Processing {len(chunks)} chunks...")
    
    # Create vector store and add documents
    vector_store = MongoDBAtlasVectorSearch(
        collection=collection,
        embedding=embeddings,
        index_name=INDEX_NAME,
        relevance_score_fn="cosine",
        text_key="text"
    )
    
    # Add documents in batches to avoid rate limits
    batch_size = 10
    total_added = 0
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        try:
            vector_store.add_documents(batch)
            total_added += len(batch)
            print(f"  - Added batch {i // batch_size + 1}: {total_added}/{len(chunks)} chunks")
        except Exception as e:
            print(f"  - Error adding batch {i // batch_size + 1}: {e}")
            # Wait and retry
            time.sleep(2)
            try:
                vector_store.add_documents(batch)
                total_added += len(batch)
                print(f"  - Retry successful: {total_added}/{len(chunks)} chunks")
            except Exception as e2:
                print(f"  - Retry failed: {e2}")
        
        # Rate limiting
        if (i + batch_size) < len(chunks):
            time.sleep(0.5)
    
    print(f"\n[Complete] Successfully embedded and stored {total_added} chunks")
    return total_added


def main():
    """Main function to run the embedding pipeline."""
    print("=" * 60)
    print("PDF Embedding Pipeline for MongoDB Atlas RAG")
    print("(with text cleaning for improved quality)")
    print("=" * 60)
    
    try:
        # Step 1: Validate configuration
        validate_config()
        
        # Step 2: Load and split documents
        chunks = load_and_split_documents()
        
        # Step 3: Connect to MongoDB
        client = get_mongodb_client()
        
        # Step 4: Clear existing data
        clear_collection(client)
        
        # Step 5: Create vector index (note: may need manual creation)
        create_vector_index(client)
        
        # Step 6: Embed and store
        embed_and_store(chunks, client)
        
        print("\n" + "=" * 60)
        print("Pipeline completed successfully!")
        print("=" * 60)
        
        # Close connection
        client.close()
        
    except Exception as e:
        print(f"\n[Error] Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
