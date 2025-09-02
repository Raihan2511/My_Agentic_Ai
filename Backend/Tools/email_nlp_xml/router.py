import re
from Backend.Services.preprocess import plain_text_from_maybe_html

KEYWORDS = {
    "order_v1":   [r"\border\b", r"\bship\b", r"\bdeliver\b"],
    "leave_v1":   [r"\bleave\b", r"\bpto\b", r"\bvacation\b"],
    "meeting_v1": [r"\bmeeting\b", r"\bcalendar\b", r"\bschedule\b"],
}
DEFAULT_LABEL = "meeting_v1"

def route_intent(email_env) -> str:
    text = plain_text_from_maybe_html(email_env.body)
    for label, pats in KEYWORDS.items():
        if any(re.search(p, text, flags=re.I) for p in pats):
            return label
    return DEFAULT_LABEL
