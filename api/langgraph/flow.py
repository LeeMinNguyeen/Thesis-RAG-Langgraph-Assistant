from typing import TypedDict
from langgraph.graph import StateGraph, START, END
import re
import json
import traceback
from dotenv import load_dotenv
from api.db import db
from api.llm import llm

load_dotenv()

# State Type Definition
class StateAgent(TypedDict):
    query: str
    cleaned_query: str
    intent: str
    pretty_data: str
    mssv: str
    bot_reply: str

# Intent Map
INTENT_MAP = {
    "student_info": "tra cứu thông tin sinh viên",
    "student_credit": "tra cứu tín chỉ sinh viên",
    "student_lesson": "tra cứu lịch học của sinh viên"
}

# Graph nodes
def get_user_input(state: StateAgent) -> StateAgent:
    """Initial node: receive raw user query."""
    try:
        return {"query": state['query']}
    except Exception as e:
        print("[get_user_input] Error:", e)
        print(traceback.format_exc())
        return state

# Clean query
def preprocess_query(state: StateAgent) -> StateAgent:
    """Clean user query by removing unwanted characters."""
    try:
        q = re.sub(r"[^a-zA-Z0-9áàảãạâấầẩẫậăắằẳẵặđéèẻẽẹêếềểễệíìỉĩịòóỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵ\s]", "",
                   state['query'])
        q = re.sub(r"\s+", " ", q).strip()
        state['cleaned_query'] = q
        state['bot_reply'] = f"Nội dung đã làm sạch:\n{q}"
    except Exception as e:
        print(" [preprocess_query] Error:", e)
        print(traceback.format_exc())
        state['bot_reply'] = f"Error while cleaning query: {e}"
    return state

# Identify content api route
def classify_intent(state: StateAgent) -> StateAgent:
    """Use Gemini to classify user intent based on the query."""
    try:
        q = state["cleaned_query"]

        system_prompt = f"""
        [ROLE]
        Bạn là bộ phân loại ý định (Intent Router) của hệ thống chatbot đại học.

        [OBJECTIVE]
        Phân loại câu hỏi người dùng vào **duy nhất một** trong các nhóm ý định sau.

        [INTENT MAP]
        {json.dumps(INTENT_MAP, ensure_ascii=False, indent=2)}

        [INSTRUCTION]
        - Chỉ được chọn **một key hợp lệ** trong INTENT_MAP.
        - Không mô tả lại, không thêm ký tự, không viết hoa, không dịch.
        - Luôn đảm bảo kết quả thuộc đúng 1 trong các key sau:
            → student_info
            → student_credit
            → student_lesson
        - Nếu thấy nội dung liên quan đến nhiều nhóm, hãy chọn nhóm **phù hợp nhất**.
        - Trả về duy nhất một dòng, chứa đúng key hợp lệ.

        [OUTPUT FORMAT]
        <intent_key>

        [USER QUERY]
        {q}
        """

        intent = llm.generate(system_prompt=system_prompt).strip().lower()

        return {
            "intent": intent,
            "bot_reply": state.get("bot_reply", "") + f"\nIntent xác định: {intent}"
        }
    except Exception as e:
        print("[clasify_intent] Error: {e}")
        print(traceback.format_exc())
        state['intent'] = "unknown"
        state['bot_reply'] += f"\nError while classifying intent: {e}"
    return state


def extract_student_id(state: StateAgent) -> StateAgent:
    """Extract student ID (MSSV) pattern like Kxxxxxxxxx."""
    try:
        match = re.search(r"\bK\d{9}\b", state['cleaned_query'], re.IGNORECASE)
        state['mssv'] = match.group(0).upper() if match else None
        state['bot_reply'] += f"\nMã số sinh viên: {state['mssv']}" if match else "\nKhông tìm thấy mã sinh viên"
    except Exception as e:
        print("[Extract_student_id] Error;", e)
        print(traceback.format_exc())
        state['mssv'] = None
        state['bot_reply'] += f"\nError while extracting student ID: {e}"
    return state

def handle_student_query(state: StateAgent, function, desc: str): 
    try: 
        mssv = state["mssv"]
        cleaned_query = state["cleaned_query"]

        data = function(mssv)

        answer = llm.summarize(
            context = f"Dữ liệu {desc} của sinh viên: {data}",
            question = cleaned_query    
        )

        state['bot_reply'] += "\n" + answer 
    except Exception as e: 
        state["bot_reply"] += f"\nError: {e}"
    return state

# Specialized handlers per intent
def handle_student_info(state: StateAgent) -> StateAgent:
    return handle_student_query(state, db.get_student_data, "thông tin cá nhân")

def handle_student_credit(state: StateAgent) -> StateAgent:
    return handle_student_query(state, db.get_student_total_credits, "tín chỉ và môn học")

def handle_student_credit_semester(state: StateAgent) -> StateAgent:
    return handle_student_query(state, db.get_student_credit_each_semester, "lịch học")

# Build graph
graph = StateGraph(StateAgent)
graph.add_node("get_user_input", get_user_input)
graph.add_node("preprocess_query", preprocess_query)
graph.add_node("extract_student_id", extract_student_id)
graph.add_node("classify_intent", classify_intent)
graph.add_node("handle_student_info", handle_student_info)
graph.add_node("handle_student_credit", handle_student_credit)
graph.add_node("handle_student_lesson", handle_student_credit_semester)

graph.add_edge(START, "get_user_input")
graph.add_edge("get_user_input", "preprocess_query")
graph.add_edge("preprocess_query", "extract_student_id")
graph.add_edge("extract_student_id", "classify_intent")

graph.add_conditional_edges(
    "classify_intent",
    lambda s: s['intent'],
    {
        "student_info": "handle_student_info",
        "student_credit": "handle_student_credit",
        "student_lesson": "handle_student_lesson"
    }
)

graph.add_edge("handle_student_info", END)
graph.add_edge("handle_student_credit", END)
graph.add_edge("handle_student_lesson", END)

app = graph.compile()

# Trigger langgraph
def run_chatbot(query: str) -> str:
    try:
        result = app.invoke({"query": query})
        return result["bot_reply"]
    except Exception as e:
        print("[Run_chatbot] Error:", e)
        print(traceback.format_exc())
        return f'Error while running chatbot: {e}'