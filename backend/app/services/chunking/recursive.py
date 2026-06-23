"""Recursive text splitter that respects document structure."""

import re
from dataclasses import dataclass

# Ordered from strongest structural boundary to weakest.
DEFAULT_SEPARATORS: list[str] = [
    "\n\n\n",
    "\n\n",
    "\n",
    ". ",
    "? ",
    "! ",
    "; ",
    ", ",
    " ",
]

HEADING_LINE_RE = re.compile(
    r"^(?:#{1,6}\s+.+|.+\s\|\s.+)$",
    re.MULTILINE,
)


@dataclass(frozen=True)
class RecursivePiece:
    """Intermediate chunk produced by the recursive splitter."""

    content: str
    section: str | None = None
    separator_level: str | None = None


def detect_section(text: str) -> str | None:
    """Return a heading-like first line when present."""
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return None
    first = lines[0]
    if len(first) > 120:
        return None
    if first.startswith("#"):
        return first.lstrip("#").strip()
    if HEADING_LINE_RE.match(first) and len(lines) > 1:
        return first
    if first.isupper() and len(first.split()) <= 12:
        return first
    return None


def _split_with_separator(text: str, separator: str) -> list[str]:
    if not separator:
        return list(text)
    parts = text.split(separator)
    return [part + separator for part in parts[:-1]] + ([parts[-1]] if parts[-1] else [])


def _merge_splits(splits: list[str], separator: str, chunk_size: int) -> list[str]:
    merged: list[str] = []
    current = ""

    for piece in splits:
        candidate = current + piece if current else piece
        if len(candidate) <= chunk_size:
            current = candidate
            continue
        if current:
            merged.append(current.strip())
        current = piece

    if current.strip():
        merged.append(current.strip())
    return merged


def _split_oversized(text: str, separators: list[str], chunk_size: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    chosen_sep = ""
    for sep in separators:
        if sep and sep in text:
            chosen_sep = sep
            break

    if not chosen_sep:
        return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]

    next_separators = separators[separators.index(chosen_sep) + 1 :] if chosen_sep in separators else []
    splits = _split_with_separator(text, chosen_sep)
    chunks: list[str] = []

    buffer: list[str] = []
    for piece in splits:
        if len(piece) > chunk_size:
            if buffer:
                chunks.extend(_merge_splits(buffer, chosen_sep, chunk_size))
                buffer = []
            if next_separators:
                chunks.extend(recursive_split_text(piece, chunk_size, 0, next_separators))
            else:
                chunks.extend(_split_oversized(piece, [""], chunk_size))
            continue
        buffer.append(piece)
        if sum(len(p) for p in buffer) > chunk_size:
            merged = _merge_splits(buffer, chosen_sep, chunk_size)
            chunks.extend(merged[:-1])
            buffer = [merged[-1]] if merged else []

    if buffer:
        chunks.extend(_merge_splits(buffer, chosen_sep, chunk_size))
    return [c for c in chunks if c.strip()]


def recursive_split_text(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    separators: list[str] | None = None,
) -> list[str]:
    """Split text recursively using progressively finer separators."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    seps = separators or DEFAULT_SEPARATORS
    return _apply_overlap(_split_oversized(text, seps, chunk_size), chunk_overlap)


def _apply_overlap(chunks: list[str], overlap: int) -> list[str]:
    if overlap <= 0 or len(chunks) <= 1:
        return chunks

    overlapped = [chunks[0]]
    for idx in range(1, len(chunks)):
        previous = chunks[idx - 1]
        prefix = previous[-overlap:] if len(previous) > overlap else previous
        overlapped.append(f"{prefix}{chunks[idx]}")
    return overlapped


def recursive_chunk_document(
    content: str,
    *,
    chunk_size: int,
    chunk_overlap: int,
    max_chunk_size: int,
) -> list[RecursivePiece]:
    """Split a document into recursive chunks with section hints."""
    content = content.strip()
    if not content:
        return []

    if len(content) <= chunk_size:
        return [
            RecursivePiece(
                content=content,
                section=detect_section(content),
                separator_level="document",
            )
        ]

    raw_chunks = recursive_split_text(content, max_chunk_size, chunk_overlap)
    pieces: list[RecursivePiece] = []
    for chunk in raw_chunks:
        if not chunk.strip():
            continue
        pieces.append(
            RecursivePiece(
                content=chunk.strip(),
                section=detect_section(chunk),
                separator_level="recursive",
            )
        )
    return pieces
