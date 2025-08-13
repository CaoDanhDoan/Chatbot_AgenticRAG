from chains.prompts import GRADE_PROMPT
from consts import gemini_strong_llm
def grade_documents_node(state):
    print("Đánh giá Tài liệu...")
    question = state["question"]
    documents = state.get("documents", [])
    full_query = state.get("full_query", question)
    history = state.get("history", [])
    history_context = "\n".join([f"Câu hỏi: {h['question']}\nCâu trả lời: {h['answer']}" for h in history])
    new_state = state.copy()
    if not documents:
        print(" > Không tìm thấy tài liệu nội bộ, cần tìm kiếm web.")
        return {"web_search_required": True, "documents": [], "history": history}
    grader_chain = GRADE_PROMPT | gemini_strong_llm
    response = grader_chain.invoke({"question": question, "full_query": full_query, "documents": "\n\n".join(documents), "history_context": history_context})
    response_content_str = str(response.content)
    if "CÓ" in response_content_str.upper():
        print(" > Tài liệu nội bộ liên quan.")
        return {"web_search_required": False, "documents": documents, "history": history}
    else:
        print(" > Tài liệu nội bộ không liên quan, cần tìm kiếm web.")
        return {"web_search_required": True, "documents": documents, "history": history}
