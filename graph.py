
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from state import GraphState

from nodes.pre_process import pre_process_node
from nodes.rewrite_query import rewrite_query_node
from nodes.aggregator import aggregator_node
from nodes.search_internal import search_internal_node
from nodes.grade_documents import grade_documents_node
from nodes.web_search import web_search_node
from nodes.generate import generate_node
from nodes.evaluate import evaluate_answer_node
from nodes.human_gates import review_answer_node 


def build_workflow():
    wf = StateGraph(GraphState)

    wf.add_node("pre_process", pre_process_node)
    wf.add_node("rewrite_query", rewrite_query_node)
    wf.add_node("aggregator", aggregator_node)
    wf.add_node("search_internal", search_internal_node)
    wf.add_node("grade_documents", grade_documents_node)
    wf.add_node("web_search", web_search_node)
    wf.add_node("generate", generate_node)
    wf.add_node("evaluate", evaluate_answer_node)
    wf.add_node("human_review_answer", review_answer_node)

    wf.set_entry_point("pre_process")
    wf.add_edge("pre_process", "rewrite_query")
    wf.add_edge("rewrite_query", "aggregator")

    # aggregator → (search_internal | web_search | generate)
    def route_after_agg(s):
        if s.get("agg_need_internal"):
            return "search_internal"
        if s.get("agg_need_web"):
            return "web_search"
        return "generate"

    wf.add_conditional_edges(
        "aggregator",
        route_after_agg,
        {"search_internal": "search_internal", "web_search": "web_search", "generate": "generate"},
    )

    # search_internal → grade_documents
    wf.add_edge("search_internal", "grade_documents")

    # grade_documents → (web_search | generate)
    def route_after_grade(s):
        return "web_search" if s.get("web_search_required") else "generate"

    wf.add_conditional_edges(
        "grade_documents",
        route_after_grade,
        {"web_search": "web_search", "generate": "generate"},
    )

    # web_search → generate
    wf.add_edge("web_search", "generate")

    # generate → evaluate
    wf.add_edge("generate", "evaluate")

    # evaluate → (END | human_review_answer)
    def route_eval(s):
        return END if s.get("answer_is_satisfactory") else "human_review_answer"

    wf.add_conditional_edges(
        "evaluate",
        route_eval,
        {"human_review_answer": "human_review_answer", END: END},
    )

    # human_review_answer → (generate | web_search | END)  — KHÔNG route sang evaluate nữa
    def route_hitl(s):
        nxt = (s.get("hitl_next") or "__end__").strip().lower()
        if nxt in ("__end__", "end", "approved", "approve", "ok", "yes"):
            return END
        if nxt == "generate":
            return "generate"
        if nxt == "web_search":
            return "web_search"
        return END

    wf.add_conditional_edges(
        "human_review_answer",
        route_hitl,
        {"generate": "generate", "web_search": "web_search", END: END},
    )

    return wf


def build_app():
    wf = build_workflow()
    return wf.compile(checkpointer=MemorySaver())


# ====== EXPORTS ======
app_rag = build_app()
__all__ = ["app_rag", "build_app"]
