from typing import TypedDict, List
from typing_extensions import TypedDict

class GraphState(TypedDict):
    question: str
    generation: str
    documents: List[str]
    web_search_required: bool
    answer_is_satisfactory: bool
    history: List[dict]
    web_search_count: int
    full_query: str
