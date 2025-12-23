from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.functions import *

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Application start
    func_get_mongo_client()
    
    yield # Application stop
    func_close_mongo_connection()

app = FastAPI(title="Chatbot", lifespan=lifespan)

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Chat endpoint with RAG
@app.post("/chat")
def chat_endpoint(session_id: str, message: str):
    """
    Chat endpoint that processes user messages and returns bot responses.
    Inputs:
    {
        "session_id": "string",
        "message": "string"
    }

    Outputs:
    {
        "response": "string",
        "history": [
            {
                "user": "string",
                "bot": "string"
            }
        ]
    }
    """
    return func_chat(session_id, message)

@app.get("/chat/history/{session_id}")
def get_session_history(session_id: str, limit: int=100):
    """
    Get chat history for a specific session.
    
    Inputs:
    {
        "session_id": "string",
        "limit": 100 -> number of messages to retrieve
    }

    Outputs:
    {
        "session_id": "string",
        "history": [
            {
            "user": "string",
            "bot": "string",
            "timestamp": "datetime"
            }
        ]
    }
    """
    return func_get_session_history(session_id, limit)

@app.get("/chat/sessions")
def list_all_sessions(limit: int=10):
    """
    List all chat sessions with their first message as preview.

    Inputs:
    {
        "limit": 10 -> number of sessions to retrieve
    }

    Outputs:
    {
        "total": int,
        "sessions": [
            {
                "session_id": "string",
                "first_message": "string",
                "message_count": int,
                "created_at": "datetime",
                "updated_at": "datetime"
            }
        ]
    }
    """
    return func_list_all_sessions(limit)

@app.delete("/chat/session/{session_id}")
def delete_chat_session(session_id: str):
    """
    Delete all messages for a specific session.

    Inputs:
    {
        "session_id": "string"
    }

    Outputs:
    {
        "success": bool,
        "message": "Session {session_id} deleted successfully" OR "Session {session_id} not found or could not be deleted"
    }
    """
    return func_delete_chat_session(session_id)

@app.post("/chat/session/create")
def create_chat_session():
    """
    Create a new chat session and return its ID.

    Outputs:
    {
        "success": bool,
        "session_id": "string" OR null
    }
    """
    return func_create_chat_session()

@app.get("/")
def root():
    """Root endpoint to check if API is running."""
    return {"message": "Chatbot FastAPI backend is running with integrated chat and student APIs."}


