import os, json, re
from typing import Dict, Any, List, Tuple

from chains.prompts import AGG_ROUTER_PROMPT  
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
            res = collection.query(query_embeddings=[emb],
                                   n_results=topk,
                                   include=["documents", "distances"])
        else:
            # vẫn có thể query bằng text, nhưng nhiều phiên bản Chroma không trả distances
            res = collection.query(query_texts=[q],
                                   n_results=topk,
                                   include=["documents"])
        docs = (res.get("documents") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]
    except Exception:
        docs, dists = [], []

    # 2) tính score
    if dists:
        try:
            best_sim = 1.0 - float(min(dists))  # cosine distance -> similarity
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
                # có docs nhưng không chấm được -> tín hiệu vừa
                return 0.55, docs
        else:
            return 0.55, docs

    return 0.0, []


# ---------- router (agent + fallback theo điểm ngữ nghĩa) ----------
def aggregator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    print("Aggregator Agent (agentic) đang định tuyến...")

    q = state["question"]
    history = state.get("history", [])
    history_context = "\n".join(
        [f"- Hỏi: {h['question']}\n  Đáp: {h['answer']}" for h in history]
    )[:2000]

    # Tín hiệu hệ thống
    last_web_error = state.get("web_search_error") or "none"
    internal_ready = bool(collection is not None)
    mode = os.getenv("AGG_ROUTER_MODE", "agent").lower()  # agent | hybrid | threshold

    # 1) Ngữ nghĩa nội bộ
    sem_score, probe_docs = _probe_internal_score(q)
    print(f" > Probe nội bộ: score={sem_score:.2f} | top_doc_sample={probe_docs[0][:80]+'…' if probe_docs else '∅'}")

    # 2) Agent quyết định
    decision: Dict[str, Any] = {}
    if mode in ("agent", "hybrid"):
        payload = {
            "question": q,
            "history_context": history_context,
            "domain_hint": f"{sem_score:.2f}",          # <-- điểm ngữ nghĩa, KHÔNG dùng keywords
            "last_web_error": last_web_error,
            "internal_index_ready": internal_ready,
        }
        chain = AGG_ROUTER_PROMPT | gemini_strong_llm
        try:
            resp = call_with_backoff(lambda: chain.invoke(payload))
            decision = _extract_json(getattr(resp, "content", "") or "")
        except Exception as e:
            print(f" > Router agent error: {e}")

    # 3) Fallback nếu agent im lặng
    if not decision:
        thr = float(os.getenv("AGG_DOMAIN_SIM_THR", "0.48"))
        reason = f"fallback_by_semantic(score={sem_score:.2f}, thr={thr})"
        if sem_score >= thr and internal_ready:
            decision = {"strategy": "internal", "need_internal": True, "need_web": False,
                        "confidence": 0.55, "reason": reason}
        elif sem_score >= thr and not internal_ready:
            decision = {"strategy": "web", "need_internal": False, "need_web": True,
                        "confidence": 0.5, "reason": reason + ";no_collection"}
        else:
            decision = {"strategy": "common", "need_internal": False, "need_web": False,
                        "confidence": 0.4, "reason": reason}

    # 4) Hybrid boost (tùy chọn)
    if mode == "hybrid" and decision.get("strategy") == "internal" and sem_score >= 0.65:
        decision.update({"strategy": "hybrid", "need_web": True, "reason": (decision.get("reason","") + ";boost_hybrid")})

    # 5) Chuẩn hóa và log
    strategy = str(decision.get("strategy", "common")).lower()
    need_internal = bool(decision.get("need_internal", strategy in ("internal", "hybrid")))
    need_web = bool(decision.get("need_web", strategy in ("web", "hybrid")))
    need_common = strategy == "common" and not need_web
    conf = float(decision.get("confidence", 0.5))
    reason = str(decision.get("reason", ""))[:512]

    print(f" > Quyết định: strategy={strategy}, internal={need_internal}, web={need_web}, common={need_common} (conf={conf:.2f})"
          + (f" - {reason}" if reason else ""))

    new_state = state.copy()
    new_state.update({
        "agg_strategy": strategy,
        "agg_need_internal": need_internal,
        "agg_need_web": need_web,
        "agg_need_common": need_common,
        "agg_reason": reason,
        "web_search_required": need_web,
        # gợi ý cho downstream / debug
        "internal_probe_score": round(sem_score, 3),
    })
    return new_state
