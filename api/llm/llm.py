import google.generativeai as genai
import os
import traceback
from dotenv import load_dotenv
import json
import re

class ConnectLLM:
    """Class quản lý việc kết nối và gọi đến Gemini LLM."""

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        """Khởi tạo kết nối Gemini LLM."""
        try:
            load_dotenv()
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY missing in .env file")
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(model_name)
            print(f"Gemini model '{model_name}' initialized successfully.")
        except Exception as e:
            print("Init Error!!! Failed to initialize Gemini API:", e)
            print(traceback.format_exc())
            raise

    def generate(self, prompt: str = None, system_prompt: str = None) -> str:
        """Sinh nội dung từ LLM dựa vào prompt đầu vào.
        
        Thích hợp với hai trường hợp:
        1. Chỉ có prompt
        2. Có system_prompt 
        """
        try:
            if system_prompt:
                response = self.model.generate_content(system_prompt)
            elif prompt:
                response = self.model.generate_content(prompt)
            else:
                return "No prompt provided."

            if not response or not response.text:
                return "No response from model."
            return response.text.strip()
        except Exception as e:
            print("[ConnectLLM.generate] Error:", e)
            print(traceback.format_exc())
            return f"Error generating content: {e}"

    def summarize(self, context: str, question: str): 
        try: 
            prompt = f"""
            Đây là dữ liệu đầy đủ về: {context}
            Câu hỏi của người dùng là: {question}
            Hãy trích xuất và trả lời ngắn gọn, chính xác nhất dựa trên dữ liệu.
                    
            """
            return self.generate(prompt)
        except Exception as e: 
            print("[Summarize Error]", e)
            return f"Error summarizing content: {e}"

    def enhance_query(self, current_query: str, history: list) -> str:
        """
        Rewrites the user query to be standalone based on chat history.
        """
        if not history or not current_query.strip():
            return current_query

        # Handle both dict format {"user": ..., "bot": ...} and tuple format (user, bot)
        recent_history = history[-3:]
        history_lines = []
        for item in recent_history:
            if isinstance(item, dict):
                history_lines.append(f"User: {item.get('user', '')}\nBot: {item.get('bot', '')}")
            else:
                # Tuple format (user, bot)
                u, b = item
                history_lines.append(f"User: {u}\nBot: {b}")
        history_str = "\n".join(history_lines)
        
        prompt = f"""
        Rewrite the following question to be a standalone search query based on the history. Keep the language Vietnamese/English as input.

        History: {history_str}

        Question: {current_query}

        Standalone query:
        """

        try:
            result = self.generate(prompt)
            return result.strip() if result else current_query
        except Exception as e:
            print(f"[Enhancer Error] {e}")
            return current_query

    def generate_rag_answer(self, context: str, question: str) -> str:
        """
        Generate an answer based on RAG context and user question.
        """
        prompt = f"""
        You are a university assistant. Answer based on the context below.
        If the answer is not in the context, say "I don't have that information".

        Context:
        {context}

        Question: {question}
        """

        try:
            return self.generate(prompt)
        except Exception as e:
            print(f"[RAG Generate Error] {e}")
            return f"Error: {e}"

    def extract_document_metadata(self, text: str) -> dict:
        """
        Extract title and keywords from document text for RAG ingestion.
        Returns dict with 'title' and 'keywords' keys.
        """
        prompt = f"""
        Extract the title and 3 relevant keywords from the following text.
        Return your answer in this exact JSON format:
        {{"title": "extracted title", "keywords": ["keyword1", "keyword2", "keyword3"]}}

        Text:
        {text}

        JSON:
        """

        try:
            result = self.generate(prompt)
            # Find JSON in the response
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {"title": "", "keywords": []}
        except Exception as e:
            print(f"[Metadata Extract Error] {e}")
            return {"title": "", "keywords": []}

    def evaluate_rag_response(self, user_query: str, rag_response: str) -> dict:
        """
        Orchestration Agent: Evaluates if RAG response adequately answers the user query.
        
        Returns dict with:
        - 'is_sufficient': bool - True if RAG response is good enough
        - 'reason': str - Explanation of the decision
        - 'needs_student_data': bool - True if query requires student-specific data lookup
        """
        prompt = f"""You are an orchestration agent that evaluates chatbot responses.

        Analyze if the RAG response adequately answers the user's question.

        User Query: {user_query}

        RAG Response: {rag_response}

        Evaluate based on these criteria:
        1. Does the response directly answer the user's question?
        2. Is the response informative and not just an apology or "I don't know"?
        3. Does the query require student-specific data (like student info, credits, schedule) that RAG cannot provide?

        Student data queries include:
        - Questions about a specific student (with MSSV/student ID like K followed by 9 digits)
        - Questions about credits, schedules, grades of a student
        - Personal student information lookup

        Return your evaluation in this exact JSON format:
        {{"is_sufficient": true/false, "reason": "brief explanation", "needs_student_data": true/false}}

        JSON:
        """

        try:
            result = self.generate(prompt)
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                # Ensure all required keys exist
                return {
                    "is_sufficient": parsed.get("is_sufficient", False),
                    "reason": parsed.get("reason", ""),
                    "needs_student_data": parsed.get("needs_student_data", False)
                }
            return {"is_sufficient": False, "reason": "Failed to parse evaluation", "needs_student_data": False}
        except Exception as e:
            print(f"[Orchestration Error] {e}")
            return {"is_sufficient": False, "reason": str(e), "needs_student_data": False}