from googleapiclient.discovery import build
import os
def google_custom_search(query: str):
    try:
        service = build("customsearch", "v1", developerKey=os.environ.get("GOOGLE_CSE_API_KEY"))
        res = service.cse().list(q=query, cx=os.environ.get("GOOGLE_CSE_CX_ID")).execute()
        snippets = [item['snippet'] for item in res.get('items', []) if 'snippet' in item]
        return snippets
    except Exception as e:
        print(f"Lỗi khi tìm kiếm web: {e}")
        return []
def web_search_node(state):
    print("Tìm kiếm trên Web...")
    search_query = state.get("full_query", state["question"])
    web_snippets = google_custom_search(search_query)
    web_search_count = state.get("web_search_count", 0) + 1
    new_state = state.copy()
    new_state.update({
        "documents": web_snippets,
        "web_search_count": web_search_count
    })
    return new_state