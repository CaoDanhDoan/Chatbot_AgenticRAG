from chains.prompts import GRADE_PROMPT
from consts import gemini_strong_llm
from utils_retry import call_with_backoff

def grade_documents_node(state):
    print("Đánh giá Tài liệu...")
    q = state["question"]
    docs = state.get("documents", [])
    full_q = state.get("full_query", q)
    history = state.get("history", [])
    hist = "\n".join([f"Câu hỏi: {h['question']}\nCâu trả lời: {h['answer']}" for h in history])

    if not docs:
        print(" > Không có tài liệu → cân nhắc web.")
        return {"web_search_required": True, "documents": [], "history": history}

    chain = GRADE_PROMPT | gemini_strong_llm
    def _invoke(): return chain.invoke({"question": q, "full_query": full_q,
                                        "documents": "\n\n".join(docs), "history_context": hist})
    resp = call_with_backoff(_invoke)
    ok = "CÓ" in (resp.content or "").upper()
    print(" > Tài liệu", "liên quan." if ok else "chưa đủ thông tin, cần bổ sung.")
    return {"web_search_required": not ok, "documents": docs, "history": history}
