"""Qdrant hybrid vector store."""

import logging
import uuid
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.http import models

logger = logging.getLogger(__name__)

DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "sparse"


def chunk_id_to_uuid(chunk_id: str) -> str:
    """Map a chunkId hex string to a deterministic UUID for Qdrant."""
    return str(uuid.UUID(chunk_id[:32].ljust(32, "0")))


class QdrantStore:
    def __init__(
        self,
        collection: str,
        *,
        url: str = "",
        path: str = "",
        api_key: str = "",
        dense_dimensions: int = 1536,
        upsert_batch_size: int = 100,
    ):
        self.collection = collection
        self.dense_dimensions = dense_dimensions
        self.upsert_batch_size = upsert_batch_size

        if path:
            storage = Path(path)
            storage.mkdir(parents=True, exist_ok=True)
            logger.info("Using local Qdrant storage at %s", storage)
            self.client = QdrantClient(path=str(storage))
        else:
            logger.info("Connecting to Qdrant at %s", url)
            self.client = QdrantClient(url=url, api_key=api_key or None)

    def ensure_collection(self, *, recreate: bool = False) -> None:
        exists = self.client.collection_exists(self.collection)
        if exists and recreate:
            logger.info("Deleting collection %s", self.collection)
            self.client.delete_collection(self.collection)
            exists = False

        if not exists:
            logger.info("Creating hybrid collection %s", self.collection)
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config={
                    DENSE_VECTOR_NAME: models.VectorParams(
                        size=self.dense_dimensions,
                        distance=models.Distance.COSINE,
                    )
                },
                sparse_vectors_config={
                    SPARSE_VECTOR_NAME: models.SparseVectorParams(
                        modifier=models.Modifier.IDF,
                    )
                },
            )

    def upsert_points(self, points: list[models.PointStruct]) -> int:
        if not points:
            return 0

        upserted = 0
        for start in range(0, len(points), self.upsert_batch_size):
            batch = points[start : start + self.upsert_batch_size]
            self.client.upsert(collection_name=self.collection, points=batch)
            upserted += len(batch)
            logger.debug("Upserted points %d-%d", start, start + len(batch))
        return upserted

    def delete_stale_points(self, current_chunk_ids: set[str]) -> int:
        """Remove Qdrant points whose chunk IDs are no longer in chunks.json."""
        if not self.client.collection_exists(self.collection):
            return 0

        current_ids = {chunk_id_to_uuid(chunk_id) for chunk_id in current_chunk_ids}
        deleted = 0
        next_offset = None

        while True:
            records, next_offset = self.client.scroll(
                collection_name=self.collection,
                limit=256,
                offset=next_offset,
                with_payload=False,
                with_vectors=False,
            )
            stale_ids = [record.id for record in records if str(record.id) not in current_ids]
            if stale_ids:
                self.client.delete(
                    collection_name=self.collection,
                    points_selector=models.PointIdsList(points=stale_ids),
                )
                deleted += len(stale_ids)

            if next_offset is None:
                break

        if deleted:
            logger.info("Removed %d stale points from %s", deleted, self.collection)
        return deleted

    def count_points(self) -> int:
        result = self.client.count(collection_name=self.collection, exact=True)
        return int(result.count)

    def get_payload(self, chunk_id: str) -> dict | None:
        point_id = chunk_id_to_uuid(chunk_id)
        points = self.client.retrieve(
            collection_name=self.collection,
            ids=[point_id],
            with_payload=True,
            with_vectors=False,
        )
        if not points:
            return None
        payload = points[0].payload
        return dict(payload) if payload else None
