from chains.prompts import SEARCH_QUERY_PROMPT
from consts import gemini_strong_llm
def rewrite_query_node(state):
    print("Viết lại truy vấn ...")
    question = state["question"]
    history = state.get("history", [])
    if not history:
        return {
            "full_query": question,
            "question": question,
            "history": history
        }
    history_context = "\n".join([f"Câu hỏi: {h['question']}\nCâu trả lời: {h['answer']}" for h in history])
    search_query_chain = SEARCH_QUERY_PROMPT | gemini_strong_llm
    full_query = search_query_chain.invoke({
        "question": question,
        "history_context": history_context
    }).content.strip()
    print(f" > Truy vấn đã được viết lại: {full_query}")

    return {
        "full_query": full_query,
        "question": question,
        "history": history
    }
