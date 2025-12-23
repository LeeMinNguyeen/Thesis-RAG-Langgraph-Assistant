from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import MongoDBAtlasVectorSearch

# Imports
from config import get_config
from api.db import db
from api.llm import llm

def _get_search_engine(cfg):
    """Internal helper to get vector store for searching"""
        
    return MongoDBAtlasVectorSearch(
        collection=db.client[cfg["MONGODB_DB_NAME"]][cfg["MONGODB_RAG_COLLECTION_NAME"]],
        embedding=GoogleGenerativeAIEmbeddings(
            model=cfg["EMBEDDING_MODEL_ID"],
            google_api_key=cfg["GEMINI_API_KEY"]
        ),
        index_name=cfg["MONGODB_RAG_INDEX_NAME"]
    )

def enhance_query(current_query: str, history: list) -> str:
    """
    Rewrites the user query to be standalone based on chat history.
    Uses the shared llm object.
    """
    return llm.enhance_query(current_query, history)

def answer_query(user_query: str, history: list = None, topk: int = 3):
    """
    Main RAG function.
    Returns: (answer_string, source_documents)
    """
    cfg = get_config()
        
    # 1. Enhance
    enhanced = enhance_query(user_query, history)
    print(f"[RAG] Search Query: {enhanced}")

    # 2. Search
    docs = []
    try:
        vs = _get_search_engine(cfg)
        if vs:
            docs = vs.similarity_search(enhanced, k=topk)
    except Exception as e:
        print(f"[RAG Error] DB Search: {e}")

    # 3. Generate
    context = "\n---\n".join([d.page_content for d in docs]) if docs else "No documents found."
    
    try:
        answer = llm.generate_rag_answer(context, user_query)
        return answer, docs
    
    except Exception as e:
        return f"Error: {e}", []

def ask(question: str, history: list = None):
    answer, docs = answer_query(question, history)

    return answer

