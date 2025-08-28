# rewrite_query.py
from chains.prompts import SEARCH_QUERY_PROMPT
from consts import gemini_strong_llm
from utils_retry import call_with_backoff

def rewrite_query_node(state):
    print("Viết lại truy vấn ...")
    question = state["question"]
    history = state.get("history", [])
    llm_calls = int(state.get("llm_call_count", 0))

    if not history:
        return {"full_query": question, "question": question, "history": history, "llm_call_count": llm_calls}

    history_context = "\n".join([f"Câu hỏi: {h['question']}\nCâu trả lời: {h['answer']}" for h in history])
    chain = SEARCH_QUERY_PROMPT | gemini_strong_llm

    def _invoke():
        return chain.invoke({"question": question, "history_context": history_context})

    ans = call_with_backoff(_invoke)
    fq = (ans.content or "").strip() or question
    print(f" > Truy vấn đã được viết lại: {fq}")
    return {"full_query": fq, "question": question, "history": history, "llm_call_count": llm_calls + 1}
