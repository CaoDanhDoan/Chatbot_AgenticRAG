from typing import TypedDict, List, Dict, Any, Optional

class GraphState(TypedDict, total=False):
    question: str
    generation: str
    documents: List[str]
    full_query: str

    web_search_required: bool
    web_search_count: int
    web_search_error: Optional[str]
    agg_need_internal: bool
    agg_need_web: bool
    agg_reason: str

    answer_is_satisfactory: bool
    history: List[dict]
    hitl: Dict[str, Any]
    human_feedback: Optional[Dict[str, Any]]

    llm_call_count: int
