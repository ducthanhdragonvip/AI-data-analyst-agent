import hashlib
import math
from typing import Iterable

import chromadb
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

from app.config import get_settings
from app.models import Dataset
from app.services.dataset_profile import profile_to_text


class HashEmbeddingFunction(EmbeddingFunction[Documents]):
    def __call__(self, input: Documents) -> Embeddings:
        return [self._embed(text) for text in input]

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * 256
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:2], "big") % len(vector)
            sign = 1.0 if digest[2] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


class ChromaProfileStore:
    def __init__(self) -> None:
        settings = get_settings()
        self.client = chromadb.PersistentClient(path=str(settings.chroma_path))
        self.collection = self.client.get_or_create_collection(
            name="dataset_profiles",
            embedding_function=HashEmbeddingFunction(),
        )

    def upsert_dataset(self, dataset: Dataset) -> None:
        document = profile_to_text(dataset.display_name, dataset.table_schema, dataset.table_name, dataset.profile)
        self.collection.upsert(
            ids=[f"dataset-{dataset.id}"],
            documents=[document],
            metadatas=[
                {
                    "dataset_id": dataset.id,
                    "display_name": dataset.display_name,
                    "table_schema": dataset.table_schema or "",
                    "table_name": dataset.table_name or "",
                    "is_imported": bool(dataset.table_name),
                    "source_type": dataset.source_type,
                }
            ],
        )

    def delete_dataset(self, dataset_id: int) -> None:
        self.collection.delete(ids=[f"dataset-{dataset_id}"])

    def search(self, query: str, dataset_ids: Iterable[int] | None = None, limit: int = 5) -> list[dict]:
        where = None
        ids = list(dataset_ids or [])
        if len(ids) == 1:
            where = {"dataset_id": ids[0]}
        result = self.collection.query(query_texts=[query], n_results=limit, where=where)
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        return [{"document": doc, "metadata": meta} for doc, meta in zip(documents, metadatas)]
