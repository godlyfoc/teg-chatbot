"""Unicode-aware tokenizer for BM25."""

import re

TOKEN_RE = re.compile(r"[a-zA-ZÀ-ÿ0-9]+(?:'[a-zA-ZÀ-ÿ]+)?", re.UNICODE)

STOPWORDS = frozenset(
    {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
        "ag", "ar", "na", "an", "le", "do", "den", "agus", "nach", "nó",
    }
)


def tokenize(text: str, *, remove_stopwords: bool = False) -> list[str]:
    """Tokenize text preserving Irish diacritics."""
    tokens = [match.group(0).lower() for match in TOKEN_RE.finditer(text)]
    if remove_stopwords:
        return [token for token in tokens if token not in STOPWORDS]
    return tokens
