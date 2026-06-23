"""Unit tests for recursive chunking (no API calls)."""

import pytest

from app.services.chunking.postprocess import coalesce_small_chunks
from app.services.chunking.recursive import (
    RecursivePiece,
    detect_section,
    recursive_chunk_document,
    recursive_split_text,
)
from app.services.chunking.semantic import optimize_chunk_boundaries


class FakeEmbedder:
    def __init__(self, similarities: list[float]):
        self.similarities = similarities
        self.calls = 0

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        # Distinct unit vectors so cosine similarity is easy to control.
        vectors: list[list[float]] = []
        for idx in range(len(texts)):
            vector = [0.0] * len(texts)
            vector[idx] = 1.0
            vectors.append(vector)
        return vectors


@pytest.mark.asyncio
async def test_semantic_merge_combines_similar_adjacent_chunks(monkeypatch):
    pieces = [
        RecursivePiece(content="Topic A part one."),
        RecursivePiece(content="Topic A part two."),
    ]

    async def fake_embed(_texts):
        return [[1.0, 0.0], [0.95, 0.31]]

    embedder = FakeEmbedder([])
    embedder.embed_texts = fake_embed  # type: ignore[method-assign]

    # Patch cosine to force merge
    from app.services.chunking import semantic as semantic_module

    monkeypatch.setattr(semantic_module, "cosine_similarity", lambda _a, _b: 0.9)

    merged, stats = await optimize_chunk_boundaries(
        pieces,
        embedder=embedder,
        similarity_threshold=0.75,
        min_chunk_size=80,
        max_chunk_size=1200,
    )
    assert len(merged) == 1
    assert stats.merges == 1


def test_recursive_split_respects_paragraphs():
    text = "Paragraph one.\n\nParagraph two with more detail.\n\nParagraph three."
    chunks = recursive_split_text(text, chunk_size=60, chunk_overlap=0)
    assert len(chunks) >= 2
    assert all(len(chunk) <= 60 for chunk in chunks)


def test_small_document_returns_single_chunk():
    text = "Short exam notice with enough characters to pass the minimum content threshold."
    pieces = recursive_chunk_document(
        text,
        chunk_size=1000,
        chunk_overlap=50,
        max_chunk_size=1200,
    )
    assert len(pieces) == 1
    assert pieces[0].content == text


def test_empty_document_returns_no_chunks():
    pieces = recursive_chunk_document(
        "   ",
        chunk_size=1000,
        chunk_overlap=50,
        max_chunk_size=1200,
    )
    assert pieces == []


def test_detect_section_from_heading_line():
    text = "## Exam Schedule\n\nDates for May and June."
    assert detect_section(text) == "Exam Schedule"


def test_overlap_is_applied_between_chunks():
    text = "A" * 80 + "\n\n" + "B" * 80 + "\n\n" + "C" * 80
    chunks = recursive_split_text(text, chunk_size=90, chunk_overlap=10)
    assert len(chunks) >= 2
    assert chunks[1].startswith(chunks[0][-10:])


def test_coalesce_small_chunks_merges_neighbors():
    pieces = [
        RecursivePiece(content="A" * 40),
        RecursivePiece(content="B" * 200),
    ]
    merged = coalesce_small_chunks(pieces, min_chunk_size=80, max_chunk_size=1200)
    assert len(merged) == 1
