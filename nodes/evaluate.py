from chains.prompts import EVALUATION_PROMPT
from consts import gemini_strong_llm
def evaluate_answer_node(state):
    print("Đánh giá Câu Trả lời...")
    question = state["question"]
    answer = state["generation"]
    history = state.get("history", [])
    history_context = "\n".join([f"Câu hỏi: {h['question']}\nCâu trả lời: {h['answer']}" for h in history])
    evaluation_chain = EVALUATION_PROMPT | gemini_strong_llm
    evaluation_response = evaluation_chain.invoke({"history_context": history_context, "question": question, "answer": answer})
    if "CÓ" in evaluation_response.content.upper():
        print(" > Câu trả lời đủ thông tin.")
        return {"answer_is_satisfactory": True, "history": history}
    else:
        print(" > Câu trả lời chưa đủ, đang bổ sung thông tin.")
        return {"answer_is_satisfactory": False, "history": history}
