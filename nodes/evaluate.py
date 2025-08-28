from chains.prompts import EVALUATION_PROMPT
from consts import gemini_strong_llm
from utils_retry import call_with_backoff

def evaluate_answer_node(state):
    print("Đánh giá Câu Trả Lời...")
    hitl = state.get("hitl", {})
    lr = hitl.get("last_resume")
    if hitl.get("last_gate") == "review_answer":
        if isinstance(lr, str) and lr.strip().lower() in ("approve","ok","yes","duyet","đồng ý"):
            print(" > Người duyệt đã APPROVE.")
            return {"answer_is_satisfactory": True}
        if isinstance(lr, dict) and (lr.get("action","").strip().lower() in ("approve","ok","yes","duyet","đồng ý")):
            print(" > Người duyệt đã APPROVE.")
            return {"answer_is_satisfactory": True}

    q = state["question"]; ans = state["generation"]
    history = state.get("history", [])
    hist = "\n".join([f"Câu hỏi: {h['question']}\nCâu trả lời: {h['answer']}" for h in history])

    chain = EVALUATION_PROMPT | gemini_strong_llm
    def _invoke(): return chain.invoke({"history_context": hist, "question": q, "answer": ans})
    try:
        resp = call_with_backoff(_invoke); ok = "CÓ" in (resp.content or "").upper()
    except Exception:
        ok = False 

    if ok:
        print(" > Đủ thông tin.")
        return {"answer_is_satisfactory": True, "history": history,
                "llm_call_count": int(state.get("llm_call_count", 0)) + 1}

    print(" > Chưa chắc/Chưa đủ. Mở HITL.")
    return {"answer_is_satisfactory": False, "history": history,
            "llm_call_count": int(state.get("llm_call_count", 0)) + 1,
            "hitl": {"last_gate": "review_answer",
                     "payload": {"type": "review_answer",
                                 "message": "Duyệt câu trả lời? (approve/reject/edit)",
                                 "draft": ans}}}
