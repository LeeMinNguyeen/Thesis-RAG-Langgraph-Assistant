import os
from dotenv import load_dotenv
from typing import Dict

load_dotenv()

def get_config() -> Dict[str, str]:
    """
    Centralized configuration for the RAG module.
    """
    cfg = {
        # --- API Keys ---
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
        
        # --- Models ---
        "LLM_MODEL_ID": os.getenv("LLM_MODEL_ID", "gemini-2.5-flash"),
        "EMBEDDING_MODEL_ID": os.getenv("EMBEDDING_MODEL_ID", "models/text-embedding-004"),

        # --- MongoDB Configuration ---
        "MONGODB_URI": os.getenv("MONGODB_URI"),
        "MONGODB_DB_NAME": os.getenv("MONGODB_DB_NAME", "chatbot_development"),
        "MONGODB_RAG_COLLECTION_NAME": os.getenv("MONGODB_RAG_COLLECTION_NAME", "pdf"),
        "MONGODB_RAG_INDEX_NAME": os.getenv("MONGODB_RAG_INDEX_NAME", "embedding"),
    }
    # Validation
    if not cfg["GEMINI_API_KEY"]:
        print("[RAG Config] Warning: GEMINI_API_KEY is missing.")
    if not cfg["MONGODB_URI"]:
        print("[RAG Config] Warning: MONGODB_URI is missing.")
        
    return cfg