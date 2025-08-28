import os
import re
from typing import List
from chains.prompts import (
    GENERATE_PROMPT_WITH_DOCS,
    GENERATE_PROMPT_NO_DOCS,
    CONTINUE_PROMPT,
)
from consts import gemini_fast_llm, reranker_model
from utils_retry import call_with_backoff

def _looks_truncated(text: str) -> bool:
    if not text:
        return True
    t = text.rstrip()

    if re.search(r'([.!?…]["\')\]]?\s*$)|(\n\s*\n\s*$)', t):
        return False

    last = t.splitlines()[-1].strip()
    if re.match(r'^[-•–—]\s*[\w\(\[]+', last):
        return True
    if re.search(r'[,:;]\s*$', last):
        return True

    if len(t) < 300 and len(t.split()) < 50:
        return True
    return True


def _invoke_with_budget(chain, payload, max_tokens: int) -> str:
    llm = gemini_fast_llm.bind(max_output_tokens=max_tokens)

    def _do():
        return (chain | llm).invoke(payload)

    resp = call_with_backoff(_do)
    return (getattr(resp, "content", None) or "").strip()


def _estimate_budget(q: str) -> int:
    base = int(os.getenv("GEN_MAX_OUTPUT_TOKENS_BASE", "1400"))
    hard = int(os.getenv("GEN_MAX_OUTPUT_TOKENS_HARD", "3072"))
    bonus = 0
    if len(q) > 800:
        bonus += 300
    if any(k in q.lower() for k in ("kế hoạch", "outline", "dàn ý", "chi tiết", "phương án", "tích hợp")):
        bonus += 300
    return min(base + bonus, hard)


def _rerank_inline(query: str, docs: List[str]) -> List[str]:
 
    if not docs:
        return []
    top_k = int(os.getenv("RERANK_TOPK", "3"))
    thr_raw = os.getenv("DOC_REL_THRESHOLD", "0.28").strip()
    threshold = float(thr_raw) if thr_raw != "" else None  # "" => không dùng threshold (behavior "classic")

    if reranker_model is None:
        return docs[:top_k]

    pairs = [[query, d] for d in docs]
    scores = reranker_model.predict(pairs).tolist()
    ranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)
    if threshold is None:
        return [d for d, _ in ranked[:top_k]]
    filtered = [(d, s) for d, s in ranked if float(s) >= threshold][:top_k]
    return [d for d, _ in filtered]


def generate_node(state):
    print("Tạo Câu Trả Lời...")
    question = state["question"]
    full_query = state.get("full_query", question)
    documents = state.get("documents", [])
    history = state.get("history", [])
    llm_calls = int(state.get("llm_call_count", 0))

    history_context = "\n".join([f"Câu hỏi: {h['question']}\nCâu trả lời: {h['answer']}" for h in history])
    hf = state.get("human_feedback")
    if hf and hf.get("note"):
        history_context += f"\n[Ghi chú từ người duyệt: {hf['note']}]"

    use_docs = False
    payload = {"question": question, "history_context": history_context}
    if documents:
        top_docs = _rerank_inline(full_query, documents)
        if top_docs:
            payload["documents"] = "\n\n".join(top_docs)
            use_docs = True

    print(f" > Nguồn sinh: {'COMMON' if not use_docs else 'DOCS'} | web_count={state.get('web_search_count', 0)}")

    chain = GENERATE_PROMPT_WITH_DOCS if use_docs else GENERATE_PROMPT_NO_DOCS

    budget = _estimate_budget(question)
    draft = _invoke_with_budget(chain, payload, budget)

    rounds = 0
    prev_len = 0
    while _looks_truncated(draft) and rounds < 3:
        more = _invoke_with_budget(
            CONTINUE_PROMPT,
            {"question": question,
             "draft": draft + "\n\n(Hãy tiếp tục đúng mạch hiện tại, hoàn tất danh sách/bullet dang dở; không lặp lại.)"},
            max_tokens=900
        )
        if not more or len(draft) <= prev_len:
            break
        prev_len = len(draft)
        draft = (draft.rstrip() + "\n" + more.strip()).strip()
        rounds += 1

    print(f" > Preview: {draft[:100]}...")

    new_history = (history + [{"question": question, "answer": draft}])[-5:]
    ns = state.copy()
    ns.update({
        "generation": draft,
        "history": new_history,
        "llm_call_count": llm_calls + 1,
        "used_common_knowledge": not use_docs  
    })
    return ns
