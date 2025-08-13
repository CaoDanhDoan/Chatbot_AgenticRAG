import datetime
def pre_process_node(state):
    question = state["question"]
    history = state.get("history", [])
    web_search_count = state.get("web_search_count", 0)
    if any(keyword in question.lower() for keyword in ["hôm nay", "ngày", "ngày mai", "hôm qua"]):
        today = datetime.date.today()
        updated_question = f"Hôm nay là ngày {today.day}/{today.month}/{today.year}. {question}"
        return {"question": updated_question, "history": history, "web_search_count": web_search_count}
    return {"question": question, "history": history, "web_search_count": web_search_count}
