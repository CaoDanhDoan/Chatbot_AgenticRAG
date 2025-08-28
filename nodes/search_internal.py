import os
from consts import model, collection

def search_internal_node(state):
    print("Tìm kiếm tài liệu nội bộ...")
    question = state["question"]
    full_query = state.get("full_query") or question
    history = state.get("history", [])

    if collection is None or model is None:
        print(" > collection/model chưa sẵn sàng → sang web.")
        return {"documents": [], "question": question, "full_query": full_query,
                "history": history, "web_search_required": True,
                "web_search_count": state.get("web_search_count", 0)}

    try:
        normalize = os.getenv("EMBED_NORMALIZE", "true").lower() == "true"
        q_vec = model.encode([full_query], normalize_embeddings=normalize)[0].tolist()
        res = collection.query(query_embeddings=[q_vec],
                               n_results=int(os.getenv("INTERNAL_TOPK", "10")),
                               include=["documents"])
        docs = (res.get("documents") or [[]])[0]
        return {"documents": docs, "has_internal_docs": bool(docs), "question": question, "full_query": full_query,
                "history": history, "web_search_count": state.get("web_search_count", 0)}
    except Exception as e:
        print(f" > Lỗi tìm nội bộ: {e}")
        return {"documents": [], "question": question, "full_query": full_query,
                "history": history, "web_search_required": True,
                "web_search_count": state.get("web_search_count", 0)}
