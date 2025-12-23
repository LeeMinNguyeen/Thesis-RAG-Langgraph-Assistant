import logging
from api.db import db
from api.llm import llm
from api.langgraph.flow import run_chatbot
from api.rag.chat_session import *
import uuid

# =============================== RAG ===============================
def func_rag(message: str, history: list):
    try:
        answer = ask(message, history)
        
        return answer
    except Exception as e:
        logging.error(f"RAG Error: {e}")
        return f"Error: {e}"

# =============================== Langgraph ==============================
def func_run_langgraph(query: str):
    return run_chatbot(query)

# =============================== Chat functions ===============================

def func_chat(session_id: str, message: str):
    logging.info("Calling RAG...")
    # RAG integration
    history = func_get_session_history(session_id).get("history", [])
    rag_answer = func_rag(message, history)
    
    # Use orchestration agent to evaluate RAG response
    logging.info("Evaluating RAG response with orchestration agent...")
    evaluation = llm.evaluate_rag_response(message, rag_answer)
    
    logging.info(f"[Orchestration] is_sufficient={evaluation['is_sufficient']}, "
                 f"needs_student_data={evaluation['needs_student_data']}, "
                 f"reason={evaluation['reason']}")
    
    # Decide whether to use RAG answer or fallback to LangGraph
    if evaluation['is_sufficient'] and not evaluation['needs_student_data']:
        answer = rag_answer
    else:
        logging.info("Triggering fallback LangGraph...")
        try:
            fallback = func_run_langgraph(message)
            # If LangGraph provides a meaningful response, use it
            # Otherwise, fall back to RAG answer (even if incomplete)
            if fallback and fallback.strip() and "Error" not in fallback:
                answer = fallback
                logging.info("Using LangGraph response.")
            else:
                answer = rag_answer  # Use RAG even if not perfect
                logging.info("Using RAG response.")
        except Exception as e:
            logging.error(f"LangGraph fallback error: {e}")
            answer = rag_answer  # Use RAG answer on error
            logging.info("Using RAG response due to LangGraph error.")

    # Save chat message to database
    func_save_chat_message(session_id, message, answer)       
    # History is already in correct format from db.get_chat_history
    # Each item is {"user": ..., "bot": ..., "timestamp": ...}
    return {
        "answer": answer,
        "history": history
    }

# ===============================MongoDB functions===============================

def func_get_mongo_client():
    """ Get MongoDB client info """
    try:
        client_info = db.get_mongo_client()
        return client_info
    except Exception as e:
        logging.error(f"Error: {e}")
        return None
    
def func_close_mongo_connection():
    """ Close MongoDB connection """
    try:
        db.close_connection()
        return {"success": True}
    except Exception as e:
        logging.error(f"Error: {e}")
        return {"success": False, "error": str(e)}

def func_summarize_response(content):
    """
    Hàm tóm tắt câu trả lời (Placeholder).
    Hiện tại trả về nguyên văn nội dung để code chạy được.
    """
    # Nếu content là object, thử chuyển sang string
    if not isinstance(content, str):
        return str(content)
    return content

def func_show_callbacks():
    """ Show 'registered callbacks' in Langgraph """
    try:
        return {"registered_callbacks": list(flow.list_callbacks().keys())}
    except Exception as e:
        return {"Error": str(e)}

def func_get_session_history(session_id: str, limit: int = 100):
    """
    Retrieve chat history for a specific session from database.
    """
    try:
        history = db.get_chat_history(session_id, limit)
        return {"session_id": session_id, "history": history}
    except Exception as e:
        logging.error(f"Error: {e}")
        return {"session_id": session_id, "history": []}

def func_list_all_sessions(limit: int = 50):
    """
    List all chat sessions with metadata.
    Returns session_id, first message preview, timestamps, and message count.
    """
    try:
        sessions_list = db.get_all_sessions(limit)

    except Exception as e:
        logging.error(f"Error: {e}")

    return {
        "total": len(sessions_list),
        "sessions": sessions_list
    }

def func_delete_chat_session(session_id: str):
    """
    Delete all messages for a specific session.
    """
    try:
        success = db.delete_session(session_id)
        if success:
            return {
                "success": True,
                "message": f"Session {session_id} deleted successfully"
            }
      
    except Exception as e:
        logging.error(f"Error deleting session {session_id}: {e}")    
        return {
            "success": False,
            "message": f"Session {session_id} not found or could not be deleted"
        }
    
def func_create_chat_session():
    """
    Create a new chat session and return its ID.
    """
    try:
        session_id = str(uuid.uuid4())
        while db.session_exists(session_id):
            session_id = str(uuid.uuid4())
        return {
            "success": True,
            "session_id": session_id
        }
    except Exception as e:
        logging.error(f"Error creating chat session: {e}")
        return {
            "success": False,
            "session_id": None
        }
        
def func_save_chat_message(session_id: str, user_message: str, bot_response: str):
    """
    Save a chat message to the database.
    """
    try:
        success = db.save_chat_message(session_id, user_message, bot_response)
        if success:
            return {"success": True}
        else:
            return {"success": False}
    except Exception as e:
        logging.error(f"Error saving chat message: {e}")
        return {"success": False}
    