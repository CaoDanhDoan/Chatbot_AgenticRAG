from langgraph.types import interrupt

def review_answer_node(state):
    payload = {
        "type": "review_answer",
        "message": "Duyệt câu trả lời? (approve / reject / edit)",
        "draft": state.get("generation", "")
    }
    decision = interrupt(payload)
    action = (decision.get("action") if isinstance(decision, dict) else str(decision)).strip().lower()
    note   = (decision.get("note") if isinstance(decision, dict) else None)

    updates = {"hitl": {"last_gate": "review_answer", "last_resume": decision}}
    if note:
        updates["human_feedback"] = {"note": note}

    if action in ("approve", "ok", "yes"):
        updates["answer_is_satisfactory"] = True
        updates["hitl_next"] = "__end__"
    elif action in ("reject", "no"):
        updates.update({"documents": [], "web_search_required": True})
        updates["hitl_next"] = "web_search"
    elif action == "edit":
        if isinstance(note, str) and any(k in note.lower() for k in ("web", "internet", "tìm kiếm")):
            updates.update({"documents": [], "web_search_required": True})
            updates["hitl_next"] = "web_search"
        else:
            updates["hitl_next"] = "generate"
    else:
        updates["hitl_next"] = "__end__"

    return updates
