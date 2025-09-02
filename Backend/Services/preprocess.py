from bs4 import BeautifulSoup

def plain_text_from_maybe_html(s: str) -> str:
    if not s:
        return ""
    if "<" in s and ">" in s:
        return BeautifulSoup(s, "html.parser").get_text(" ", strip=True)
    return s
