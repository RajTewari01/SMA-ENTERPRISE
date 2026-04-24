import unicodedata
import re

def sanitize_search_term(term : str) -> str :
    term = unicodedata.normalize("NFKD", term)
    term = term.encode("ascii", "ignore").decode("utf-8")
    term = re.sub(r"[-_.]", " ", term)
    term = re.sub(r"[^a-zA-Z0-9\s]", "", term)
    return re.sub(r"\s+", " ", term).strip().lower()