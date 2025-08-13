from langgraph.graph import StateGraph, START, END
from state import GraphState
from nodes.pre_process import pre_process_node
from nodes.rewrite_query import rewrite_query_node
from nodes.search_internal import search_internal_node
from nodes.grade_documents import grade_documents_node
from nodes.web_search import web_search_node
from nodes.generate import generate_node
from nodes.evaluate import evaluate_answer_node
from consts import gemini_fast_llm, gemini_strong_llm

workflow = StateGraph(GraphState)
workflow.add_node("pre_process", pre_process_node)
workflow.add_node("rewrite_query", rewrite_query_node)
workflow.add_node("search_internal", search_internal_node)
workflow.add_node("grade_documents", grade_documents_node)
workflow.add_node("web_search", web_search_node)
workflow.add_node("generate", generate_node)
workflow.add_node("evaluate", evaluate_answer_node)
workflow.set_entry_point("pre_process")
workflow.add_edge("pre_process", "rewrite_query")
workflow.add_edge("rewrite_query", "search_internal")
workflow.add_edge("search_internal", "grade_documents")
def route_grade(state):
    if state["web_search_required"]:
        return "web_search"
    else:
        return "generate"
workflow.add_conditional_edges(
    "grade_documents",
    route_grade,
    {
        "web_search": "web_search",
        "generate": "generate"
    }
)
workflow.add_edge("web_search", "generate")
workflow.add_edge("generate", "evaluate")
def route_evaluation(state):
    if state.get("answer_is_satisfactory", False):
        return END
    if state.get("web_search_count", 0) >= 3:
        return END
    return "web_search"
workflow.add_conditional_edges(
    "evaluate",
    route_evaluation,
    {
        "web_search": "web_search",
        END: END
    }
)
app_rag = workflow.compile()
