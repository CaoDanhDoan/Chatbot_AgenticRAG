import os, json, re
from typing import Dict, Any, List, Tuple

from consts import gemini_strong_llm, collection, model, reranker_model
from utils_retry import call_with_backoff

def _extract_json(text: str) -> Dict[str, Any]:
    m = re.search(r"\{.*\}", text or "", re.DOTALL)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except Exception:
        return {}

def _clip01(x: float) -> float:
    return 0.0 if x < 0 else (1.0 if x > 1 else x)

def _probe_internal_score(q: str) -> Tuple[float, List[str]]:
    if collection is None:
        return 0.0, []
    topk = int(os.getenv("AGG_PROBE_TOPK", "3"))
    docs: List[str] = []
    dists: List[float] = []
    emb = None
    if model is not None:
        try:
            emb = model.encode([q], normalize_embeddings=True)[0].tolist()
        except Exception:
            emb = None
    try:
        if emb is not None:
            res = collection.query(query_embeddings=[emb], n_results=topk, include=["documents", "distances"])
        else:
            res = collection.query(query_texts=[q], n_results=topk, include=["documents"])
        docs = (res.get("documents") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]

        # Khối code đã được chuyển vào trong try
        if dists:
            try:
                best_sim = 1.0 - float(min(dists))
                return _clip01(best_sim), docs
            except Exception:
                pass
        if docs:
            if reranker_model is not None:
                try:
                    pairs = [[q, d] for d in docs]
                    scores = reranker_model.predict(pairs).tolist()
                    return _clip01(float(max(scores))) if scores else 0.0, docs
                except Exception:
                    return 0.55, docs
            else:
                return 0.55, docs

    except Exception:
        # Khối except bắt lỗi, giúp chương trình không bị crash
        return 0.0, []

    return 0.0, []

def aggregator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    print("Aggregator Agent (agentic) đang định tuyến...")
    q = state["question"]
    history = state.get("history", [])
    history_context = "\n".join(
        [f"- Hỏi: {h['question']}\n  Đáp: {h['answer']}" for h in history]
    )[:2000]

    internal_ready = bool(collection is not None)
    sem_score, probe_docs = _probe_internal_score(q)
    print(f" > Probe nội bộ: score={sem_score:.2f} | top_doc_sample={probe_docs[0][:80]+'…' if probe_docs else '∅'}")

    # Lấy ngưỡng linh hoạt từ biến môi trường
    internal_thr = float(os.getenv("AGG_INTERNAL_THR", "0.6"))
    hybrid_thr = float(os.getenv("AGG_HYBRID_THR", "0.4"))

    strategy = "common"
    need_internal = False
    need_web = False
    reason = ""

    # Logic định tuyến mới dựa trên điểm số ngữ nghĩa
    if sem_score >= internal_thr:
        strategy = "internal"
        need_internal = True
        need_web = False
        reason = f"score_high_enough_for_internal (score={sem_score:.2f} >= thr={internal_thr})"
    elif sem_score >= hybrid_thr:
        strategy = "hybrid"
        need_internal = True
        need_web = True
        reason = f"score_moderate_for_hybrid (score={sem_score:.2f} >= thr={hybrid_thr})"
    else:
        strategy = "web"
        need_internal = False
        need_web = True
        reason = f"score_low_for_web (score={sem_score:.2f} < thr={hybrid_thr})"
        
    # Trường hợp không có index nội bộ, luôn chuyển sang web
    if not internal_ready:
        strategy = "web"
        need_internal = False
        need_web = True
        reason = "no_internal_index_ready"

    print(f" > Quyết định: strategy={strategy}, internal={need_internal}, web={need_web}, common=False - {reason}")

    new_state = state.copy()
    new_state.update({
        "agg_strategy": strategy,
        "agg_need_internal": need_internal,
        "agg_need_web": need_web,
        "agg_reason": reason,
        "web_search_required": need_web,
        "internal_probe_score": round(sem_score, 3),
        "documents": probe_docs
    })
    return new_state