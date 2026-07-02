"""Format validated LLM output into user-facing markdown."""

from __future__ import annotations

import re

from app.services.language import LanguageCode

_ANSWER_PATTERN = re.compile(
    r"(?is)^\s*#{1,3}\s*answer\s*\n(.*?)(?=^\s*#{1,3}\s*sources\s*$|\Z)",
    re.MULTILINE,
)
_SOURCES_PATTERN = re.compile(
    r"(?is)^\s*#{1,3}\s*sources\s*\n(.*)\Z",
    re.MULTILINE,
)
_SOURCE_LINK_PATTERN = re.compile(
    r"\[([^\]]+)\]\((https?://[^)]+)\)",
)
_INLINE_CITE_PATTERN = re.compile(r"(?<!\[)\[(\d{1,2})\](?!\()")


def _parse_sources_list(sources_text: str) -> list[tuple[str, str]]:
    """Extract ordered (title, url) pairs from the Sources section."""
    sources: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for match in _SOURCE_LINK_PATTERN.finditer(sources_text):
        title = match.group(1).strip()
        url = match.group(2).strip().rstrip(".,;")
        key = (title.lower(), url.lower())
        if key in seen:
            continue
        seen.add(key)
        sources.append((title, url))
    return sources


def _inject_inline_citations(answer: str, sources: list[tuple[str, str]]) -> str:
    """Turn [1], [2] markers into clickable citation links."""

    def replace(match: re.Match[str]) -> str:
        index = int(match.group(1))
        if 1 <= index <= len(sources):
            _title, url = sources[index - 1]
            return f"[{index}]({url})"
        return match.group(0)

    return _INLINE_CITE_PATTERN.sub(replace, answer)


def _format_sources_block(sources: list[tuple[str, str]], heading: str) -> str:
    lines = [f"### {heading}", ""]
    for index, (title, url) in enumerate(sources, start=1):
        lines.append(f"{index}. [{title}]({url})")
    return "\n".join(lines)


def format_response_for_display(response: str, query_language: LanguageCode) -> str:
    """
    Convert the validated LLM structure (## Answer / ## Sources) into clean
    markdown for the chat UI — inline citation badges plus a numbered sources block.
    """
    text = response.strip()
    if not text:
        return text

    answer_match = _ANSWER_PATTERN.search(text)
    sources_match = _SOURCES_PATTERN.search(text)

    if answer_match:
        answer = answer_match.group(1).strip()
    else:
        answer = text
        if sources_match:
            answer = text[: sources_match.start()].strip()

    sources_text = sources_match.group(1).strip() if sources_match else ""
    sources = _parse_sources_list(sources_text)
    sources_heading = "Foinsí" if query_language == "ga" else "Sources"

    if sources:
        answer = _inject_inline_citations(answer, sources)

    if not sources:
        return answer

    return f"{answer}\n\n---\n\n{_format_sources_block(sources, sources_heading)}"
