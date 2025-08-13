from consts import model, collection
def search_internal_node(state):
    print("Tìm kiếm tài liệu nội bộ...")
    full_query = state.get("full_query", state["question"])
    question_embedding = model.encode(full_query)
    results = collection.query(query_embeddings=[question_embedding.tolist()], n_results=10, include=["documents"])
    documents = results['documents'][0] if results and results['documents'] else []
    return {
        "documents": documents,
        "question": state["question"],
        "full_query": state.get("full_query"),
        "history": state.get("history", []),
        "web_search_count": state.get("web_search_count", 0)
    }
