# File: grade_documents.py
from chains.prompts import GRADE_PROMPT
from consts import gemini_strong_llm
from utils_retry import call_with_backoff

def grade_documents_node(state):
    print("Đánh giá Tài liệu...")
    q = state["question"]
    docs = state.get("documents", [])
    full_q = state.get("full_query", q)
    history = state.get("history", [])
    hist = "\\n".join([f"Câu hỏi: {h['question']}\\nCâu trả lời: {h['answer']}" for h in history])

    # Nếu không có tài liệu nào được tìm thấy, yêu cầu tìm kiếm web
    if not docs:
        print(" > Không có tài liệu nào được tìm thấy. Chuyển sang tìm web.")
        return {"web_search_required": True, "documents": [], "history": history}

    chain = GRADE_PROMPT | gemini_strong_llm
    
    def _invoke():
        return chain.invoke({"question": q, "full_query": full_q,
                             "documents": "\\n\\n".join(docs), "history_context": hist})
    
    resp = call_with_backoff(_invoke)
    resp_content = (resp.content or "").upper().strip()

    if "CÓ" in resp_content:
        print(" > Tài liệu nội bộ đủ thông tin, không cần tìm kiếm web.")
        # Chuyển tiếp với tài liệu nội bộ, không tìm web
        return {"web_search_required": False, "documents": docs, "history": history}
    
    elif "MỘT PHẦN" in resp_content:
        print(" > Tài liệu nội bộ chỉ có một phần thông tin, cần tìm kiếm web bổ sung.")
        # Chuyển tiếp với cả tài liệu nội bộ và yêu cầu tìm web
        return {"web_search_required": True, "documents": docs, "history": history}
    
    else: # Trường hợp "KHÔNG" hoặc bất kỳ câu trả lời nào khác
        print(" > Tài liệu nội bộ không liên quan, tìm kiếm web thay thế.")
        # Xóa tài liệu nội bộ và chỉ tìm kiếm web
        return {"web_search_required": True, "documents": [], "history": history}