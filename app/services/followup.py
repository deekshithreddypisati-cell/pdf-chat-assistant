import re
from typing import List

FOLLOWUP_PATTERNS = [
    r"\bit\b", r"\bthat\b", r"\bthose\b", r"\bthey\b", r"\bthem\b", r"\bthis\b",
    r"\bwhich page\b", r"\bwhat about\b", r"\bcan you\b", r"\bexplain\b", r"\bwhy\b",
]

def looks_like_followup(q: str) -> bool:
    ql = (q or "").lower()
    return any(re.search(p, ql) for p in FOLLOWUP_PATTERNS)


def rewrite_query_with_history(user_query: str, history: List[str]) -> str:
    """
    history = list of previous user questions
    """

    if not history:
        return user_query

    if not looks_like_followup(user_query):
        return user_query

    last_question = history[-1]

    # Simple follow-up rewrite
    rewritten_query = f"{user_query} (context: {last_question})"

    return rewritten_query