import os
from dotenv import load_dotenv
from typing import Dict

load_dotenv()

def get_config():

    cfg = {
        # --- MongoDB Atlas Configuration ---
        "MONGODB_URI": os.getenv("MONGODB_URI"),
        "MONGODB_DB_NAME": os.getenv("MONGODB_DB_NAME"),

        # --- Gemini Configuration ---
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),

        # --- API Configuration ---
        "API_BASE_URL": os.getenv("API_BASE_URL", "http://localhost:8000"),
        "VITE_API_BASE_URL": os.getenv("VITE_API_BASE_URL", "http://localhost:8000"),
    }

    # --- Validation ---
    if not cfg["MONGODB_URI"]:
        print("[Config] Warning: MONGODB_URI is missing.")
    
    if not cfg["GEMINI_API_KEY"]:
         print("[Config] Warning: GEMINI_API_KEY is missing.")

    return cfg
