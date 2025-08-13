from chains.prompts import GENERATE_PROMPT_WITH_DOCS, GENERATE_PROMPT_NO_DOCS
from consts import gemini_fast_llm, reranker_model

def generate_node(state):
    print("Tạo Câu Trả lời...")
    question = state["question"]
   
    full_query = state.get("full_query", question) 
    documents = state.get("documents", [])
    history = state.get("history", [])
    
    history_context = "\n".join([f"Câu hỏi: {h['question']}\nCâu trả lời: {h['answer']}" for h in history])

    if documents:
        sentence_pairs = [[full_query, context] for context in documents]
        rerank_scores = reranker_model.predict(sentence_pairs)
        reranked_contexts_with_scores = sorted(
            zip(documents, rerank_scores),
            key=lambda x: x[1],
            reverse=True
        )
        reranked_documents = [doc for doc, score in reranked_contexts_with_scores[:3]]

        chain = GENERATE_PROMPT_WITH_DOCS | gemini_fast_llm
        answer = chain.invoke({
            "question": question, 
            "documents": "\n\n".join(reranked_documents),
            "history_context": history_context
        })
    else:
        print(" > Không có tài liệu, tạo câu trả lời dựa trên kiến thức chung.")
        chain = GENERATE_PROMPT_NO_DOCS | gemini_fast_llm
        answer = chain.invoke({
            "question": question,
            "history_context": history_context
        })

    print(f" > Câu trả lời được tạo: {answer.content[:100]}...")
    
    new_history = history + [{"question": question, "answer": answer.content}]
    if len(new_history) > 5:
        new_history = new_history[-5:]

    new_state = state.copy()
    new_state.update({
        "generation": answer.content,
        "history": new_history
    })
    
    return new_state