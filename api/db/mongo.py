import os
from dotenv import load_dotenv
from fastapi import HTTPException
from pymongo import MongoClient, errors
from pymongo.database import Database
import logging
from datetime import datetime

load_dotenv()

MONGO_URI = os.getenv("MONGODB_URI", "")
DATABASE_NAME = os.getenv("MONGODB_DB_NAME", "chatbot_development")

class MongoManager:
    client: MongoClient = None
    db: Database = None
    chat_collection = None
    hssv_collection = None
    stc_collection = None

    def get_mongo_client(self, path=MONGO_URI):
        """Establish and return a MongoDB client."""
        try:
            self.client = MongoClient(path)
            self.db = self.client[DATABASE_NAME]
            # Test the connection
            self.client.admin.command('ping')
            logging.info("Connected to MongoDB successfully.")
            self.get_collections()
        except errors.ConnectionFailure as e:
            logging.error(f"ERROR CONNECTING TO MONGODB: Please check MONGO_URI and Access List. Details: {e}")
            return None
        
    def close_connection(self):
        """Close the MongoDB client connection."""
        logging.info("Closing MongoDB connection...")
        if self.client:
            self.client.close()

    def get_collections(self):
        """Get the chat history collection."""
        self.chat_collection = self.db.get_collection("chat_history")
        self.hssv_collection = self.db.get_collection("HOSOSINHVIEN")
        self.stc_collection = self.db.get_collection("SOTINCHI")

        logging.info("Collections accessed.")

    def save_chat_message(self, session_id: str, user_message: str, bot_response: str):
        """Save a chat message to the database."""
        if self.chat_collection is None:
            logging.warning("Warning: Could not save chat message - database connection failed")
            return False
        
        try:
            self.chat_collection.insert_one({
                "session_id": session_id,
                "user_message": user_message,
                "bot_response": bot_response,
                "timestamp": datetime.utcnow()
            })
            return True
        except Exception as e:
            logging.error(f"Error saving chat message: {e}")
            return False

    def get_chat_history(self, session_id: str, limit: int = 100):
        """Retrieve chat history for a session."""
        if self.chat_collection is None:
            return []
        
        try:
            messages = list(self.chat_collection.find(
                {"session_id": session_id}
            ).sort("timestamp", -1).limit(limit))
            
            # Reverse to get chronological order
            messages.reverse()
            
            return [
                {
                    "user": msg["user_message"],
                    "bot": msg["bot_response"],
                    "timestamp": msg["timestamp"]
                }
                for msg in messages
            ]
        except Exception as e:
            logging.error(f"Error retrieving chat history: {e}")
            return []

    def get_all_sessions(self, limit: int = 50):
        """Retrieve all unique chat sessions with their first message as preview."""
        if self.chat_collection is None:
            logging.warning("Warning: Could not retrieve sessions - database connection failed")
            return []
        
        try:
            # Aggregation pipeline to get unique sessions with metadata
            pipeline = [
                {"$sort": {"timestamp": 1}},
                {"$group": {
                    "_id": "$session_id",
                    "first_message": {"$first": "$user_message"},
                    "first_timestamp": {"$first": "$timestamp"},
                    "last_timestamp": {"$last": "$timestamp"},
                    "message_count": {"$sum": 1}
                }},
                {"$sort": {"last_timestamp": -1}},
                {"$limit": limit}
            ]
            
            sessions = list(self.chat_collection.aggregate(pipeline))
            logging.info(f"Retrieved {len(sessions)} sessions from database.")

            return [
                {
                    "session_id": session["_id"],
                    "first_message": session["first_message"],
                    "first_timestamp": session["first_timestamp"],
                    "last_timestamp": session["last_timestamp"],
                    "message_count": session["message_count"]
                }
                for session in sessions
            ]
        except Exception as e:
            logging.error(f"Error retrieving sessions: {e}")
            return []

    def delete_session(self, session_id: str):
        """Delete all messages for a specific session."""
        if self.chat_collection is None:
            logging.warning("Warning: Could not delete session - database connection failed")
            return False
        
        try:
            result = self.chat_collection.delete_many({"session_id": session_id})
            return result.deleted_count > 0
        except Exception as e:
            logging.error(f"Error deleting session: {e}")
            return False
        
    def session_exists(self, session_id: str):
        """Check if a session ID already exists in the database."""
        if self.chat_collection is None:
            return False
        
        try:
            count = self.chat_collection.count_documents({"session_id": session_id})
            return count > 0
        except Exception as e:
            logging.error(f"Error checking session existence: {e}")
            return False
    
    def serialize(doc):
        doc['_id'] = str(doc['_id'])
        return doc

    def get_student_data(self, mssv: str):
        doc = self.hssv_collection.find_one({"MASV": mssv})
        if not doc:
            raise Exception(f"Không tìm thấy sinh viên {mssv}")
        doc["_id"] = str(doc["_id"])
        return doc

    def get_student_total_credits(self, mssv: str):
        student = self.hssv_collection.find_one({"MASV": mssv})
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        class_code = student.get("MALOP", "")
        if not class_code:
            raise HTTPException(status_code=400, detail="Class code not found")
        all_student_classcodes = list(self.stc_collection.find({"MALOP": class_code}))
        total_course_credits = sum(doc.get("STC", 0) for doc in all_student_classcodes)
        return {
            "MASV": mssv,
            "MALOP": class_code,
            "TONGTINCHI": total_course_credits,
            "MONHOC": [{"MSMH": doc.get("MSMH", ""), "STC": doc.get("STC", 0)} for doc in all_student_classcodes]
        }

    def get_student_credit_each_semester(self, mssv: str, hk: str, nam: str): 
        student = self.hssv_collection.find_one({"MASV": mssv})
        if not student:
            raise HTTPException(status_code=404, detail="Not found student data")
        malop = student.get("MALOP")
        if not malop:
            raise HTTPException(status_code=400, detail="Not found MALOP")
        student_docs = list(self.stc_collection.find({"MALOP": malop, "NAM": nam, "HK": hk}))
        if not student_docs:
            raise HTTPException(status_code=404, detail="Not found data TINCHI")
        tong_tinchi = sum(doc.get("STC", 0) for doc in student_docs)
        return {
            "MASV": mssv,
            "MALOP": malop,
            "HK": hk,
            "NAM": nam,
            "TONGTINCHI": tong_tinchi,
            "MON_HOC": [{"MAMH": doc.get("MSMH", ""), "STC": doc.get("STC", 0)} for doc in student_docs]
            }