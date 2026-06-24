"""BM25 sparse vector encoder for Qdrant."""

from dataclasses import dataclass

from rank_bm25 import BM25Okapi

from app.services.embedding.tokenizer import tokenize


@dataclass(frozen=True)
class SparseVector:
    indices: list[int]
    values: list[float]


class BM25SparseEncoder:
    """Fit BM25 on a corpus and encode documents as sparse vectors."""

    def __init__(self, *, max_terms: int = 256):
        self.max_terms = max_terms
        self._bm25: BM25Okapi | None = None
        self._vocabulary: dict[str, int] = {}
        self._tokenized_corpus: list[list[str]] = []

    @property
    def vocabulary_size(self) -> int:
        return len(self._vocabulary)

    def fit(self, texts: list[str]) -> None:
        self._tokenized_corpus = [tokenize(text) for text in texts]
        self._bm25 = BM25Okapi(self._tokenized_corpus)

        vocab: dict[str, int] = {}
        for doc_tokens in self._tokenized_corpus:
            for token in set(doc_tokens):
                if token not in vocab:
                    vocab[token] = len(vocab)
        self._vocabulary = vocab

    def encode(self, text: str) -> SparseVector:
        if self._bm25 is None:
            raise RuntimeError("BM25SparseEncoder.fit() must be called before encode()")

        doc_tokens = tokenize(text)
        if not doc_tokens:
            return SparseVector(indices=[], values=[])

        term_freq: dict[str, int] = {}
        for token in doc_tokens:
            if token in self._vocabulary:
                term_freq[token] = term_freq.get(token, 0) + 1

        doc_len = len(doc_tokens)
        avgdl = self._bm25.avgdl
        k1 = self._bm25.k1
        b = self._bm25.b

        weights: list[tuple[int, float]] = []
        for term, tf in term_freq.items():
            term_idx = self._vocabulary[term]
            idf = float(self._bm25.idf.get(term, 0.0))
            if idf <= 0:
                continue
            tf_norm = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * doc_len / avgdl))
            weight = idf * tf_norm
            if weight > 0:
                weights.append((term_idx, weight))

        weights.sort(key=lambda item: item[1], reverse=True)
        weights = weights[: self.max_terms]

        return SparseVector(
            indices=[idx for idx, _ in weights],
            values=[val for _, val in weights],
        )

    def encode_batch(self, texts: list[str]) -> list[SparseVector]:
        return [self.encode(text) for text in texts]

    def avg_nonzero_terms(self, texts: list[str]) -> float:
        vectors = self.encode_batch(texts)
        if not vectors:
            return 0.0
        return sum(len(vector.indices) for vector in vectors) / len(vectors)
