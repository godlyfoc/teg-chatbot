"""Unit tests for embedding tokenizer and BM25 sparse encoder."""

from app.services.embedding.sparse import BM25SparseEncoder
from app.services.embedding.tokenizer import tokenize


def test_tokenize_preserves_irish_diacritics():
    tokens = tokenize("Fáilte chuig Teastas Eorpach na Gaeilge")
    assert "fáilte" in tokens
    assert "gaeilge" in tokens


def test_tokenize_english_text():
    tokens = tokenize("B1 oral exams for PME candidates")
    assert "oral" in tokens
    assert "exams" in tokens
    assert "pme" in tokens


def test_bm25_sparse_vector_shape():
    corpus = [
        "TEG offers Irish language exams at multiple levels.",
        "B1 oral exams run in Maynooth for PME candidates.",
        "Scrúduithe TEG ar siúl ag leibhéal B1 agus B2.",
    ]
    encoder = BM25SparseEncoder(max_terms=32)
    encoder.fit(corpus)

    vector = encoder.encode(corpus[0])
    assert len(vector.indices) == len(vector.values)
    assert len(vector.indices) > 0
    assert all(index >= 0 for index in vector.indices)
    assert all(value > 0 for value in vector.values)


def test_bm25_batch_encoding():
    corpus = [
        "Exam dates announced for 2025.",
        "Dátaí scrúdaithe fógartha do 2025.",
    ]
    encoder = BM25SparseEncoder(max_terms=16)
    encoder.fit(corpus)
    vectors = encoder.encode_batch(corpus)
    assert len(vectors) == 2
    assert encoder.vocabulary_size > 0


def test_qdrant_delete_stale_points(tmp_path):
    from qdrant_client.http import models

    from app.services.vectorstore.qdrant import DENSE_VECTOR_NAME, QdrantStore, chunk_id_to_uuid

    store = QdrantStore(
        collection="test_chunks",
        path=str(tmp_path / "qdrant"),
        dense_dimensions=4,
    )
    store.ensure_collection(recreate=True)

    chunk_ids = ["aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"]
    points = [
        models.PointStruct(
            id=chunk_id_to_uuid(chunk_id),
            vector={DENSE_VECTOR_NAME: [0.1, 0.2, 0.3, 0.4]},
            payload={"chunkId": chunk_id},
        )
        for chunk_id in chunk_ids
    ]
    store.upsert_points(points)
    assert store.count_points() == 2

    removed = store.delete_stale_points({chunk_ids[0]})
    assert removed == 1
    assert store.count_points() == 1
    assert store.get_payload(chunk_ids[0]) is not None
    assert store.get_payload(chunk_ids[1]) is None
