import os
from functools import lru_cache
from typing import Tuple, List, Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

_service = None
def _get_service():
    global _service
    if _service is None:
        _service = build("customsearch", "v1", developerKey=os.environ.get("GOOGLE_CSE_API_KEY"))
    return _service

@lru_cache(maxsize=1024)
def _cached_search(query: str) -> List[str]:
    service = _get_service()
    res = service.cse().list(q=query, cx=os.environ.get("GOOGLE_CSE_CX_ID")).execute()
    return [item['snippet'] for item in res.get('items', []) if 'snippet' in item]

def google_custom_search(query: str) -> Tuple[List[str], Optional[str]]:
    try:
        snippets = _cached_search(query)
        return snippets, None
    except HttpError as e:
        code = getattr(e, 'resp', None).status if hasattr(e, 'resp') and e.resp else None
        reason = ""
        try:
            reason = e._get_reason() or ""
        except Exception:
            reason = str(e) or ""
        r = reason.lower()
        if code in (403, 429) or "ratelimit" in r or "quota" in r or "daily" in r:
            if "daily" in r:
                return [], "daily_limit"
            return [], "rate_limited"
        return [], "http_error"
    except Exception:
        return [], "unknown"

def web_search_node(state):
    print("Tìm kiếm Web (Google CSE)...")
    q = state.get("full_query", state["question"]) or ""
    snippets, err = google_custom_search(q)
    web_search_count = int(state.get("web_search_count", 0)) + 1
    new_state = state.copy()
    new_state.update({"documents": snippets, "has_web_docs": bool(snippets), "web_search_count": web_search_count})
    if err:
        new_state["web_search_error"] = err
        print(f" > Web search error: {err}")
    return new_state
