"""Post-processing helpers for chunk lists."""

from app.services.chunking.recursive import RecursivePiece


def coalesce_small_chunks(
    pieces: list[RecursivePiece],
    *,
    min_chunk_size: int,
    max_chunk_size: int,
) -> list[RecursivePiece]:
    """Merge undersized chunks with neighbors when they fit within max size."""
    if len(pieces) <= 1:
        return pieces

    merged: list[RecursivePiece] = [pieces[0]]
    for piece in pieces[1:]:
        previous = merged[-1]
        combined = f"{previous.content}\n\n{piece.content}"
        if (
            len(combined) <= max_chunk_size
            and (len(previous.content) < min_chunk_size or len(piece.content) < min_chunk_size)
        ):
            merged[-1] = RecursivePiece(
                content=combined,
                section=previous.section or piece.section,
                separator_level=previous.separator_level or piece.separator_level,
            )
            continue
        merged.append(piece)

    return merged
