"""Semantic boundary optimization for recursively split chunks."""

from dataclasses import dataclass

from app.services.chunking.embeddings import EmbeddingClient, average_embeddings, cosine_similarity
from app.services.chunking.recursive import RecursivePiece


@dataclass(frozen=True)
class SemanticMergeStats:
    merges: int = 0


async def optimize_chunk_boundaries(
    pieces: list[RecursivePiece],
    *,
    embedder: EmbeddingClient,
    similarity_threshold: float,
    min_chunk_size: int,
    max_chunk_size: int,
) -> tuple[list[RecursivePiece], SemanticMergeStats]:
    """
    Merge adjacent recursive chunks when embeddings indicate they belong together.
    Small trailing chunks are also merged with neighbors when possible.
    """
    if len(pieces) <= 1:
        return pieces, SemanticMergeStats()

    texts = [piece.content for piece in pieces]
    embeddings = await embedder.embed_texts(texts)
    merges = 0

    merged_pieces: list[RecursivePiece] = [pieces[0]]
    merged_embeddings: list[list[float]] = [embeddings[0]]

    for idx in range(1, len(pieces)):
        current_piece = pieces[idx]
        current_embedding = embeddings[idx]
        previous_piece = merged_pieces[-1]
        previous_embedding = merged_embeddings[-1]

        combined_text = f"{previous_piece.content}\n\n{current_piece.content}"
        similarity = cosine_similarity(previous_embedding, current_embedding)
        should_merge = (
            len(combined_text) <= max_chunk_size
            and (
                similarity >= similarity_threshold
                or len(previous_piece.content) < min_chunk_size
                or len(current_piece.content) < min_chunk_size
            )
        )

        if should_merge:
            merged_pieces[-1] = RecursivePiece(
                content=combined_text,
                section=previous_piece.section or current_piece.section,
                separator_level="semantic",
            )
            merged_embeddings[-1] = average_embeddings(previous_embedding, current_embedding)
            merges += 1
            continue

        merged_pieces.append(current_piece)
        merged_embeddings.append(current_embedding)

    return merged_pieces, SemanticMergeStats(merges=merges)
