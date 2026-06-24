"""Format retrieved chunks into LLM context."""

from app.models.retrieval import RetrievedChunk


def format_retrieval_context(
    chunks: list[RetrievedChunk],
    *,
    max_chars: int = 6000,
) -> str:
    """Build a numbered context block from retrieved chunks."""
    if not chunks:
        return ""

    parts: list[str] = []
    used = 0

    for index, chunk in enumerate(chunks, start=1):
        header = f"[{index}] {chunk.title or 'Untitled'} ({chunk.source_url})"
        block = f"{header}\n{chunk.content.strip()}"
        if used + len(block) > max_chars:
            remaining = max_chars - used
            if remaining <= len(header) + 10:
                break
            block = f"{header}\n{chunk.content.strip()[: remaining - len(header) - 1]}"
        parts.append(block)
        used += len(block) + 2
        if used >= max_chars:
            break

    return "\n\n".join(parts)
