from collections.abc import Iterable
from pathlib import Path

from src.core.config import get_settings
from src.modules.data.embeddings.hash_embeddings import HashEmbeddingFunction


ALLOWED_DOCUMENT_TYPES = {
    "business_knowledge",
    "data_dictionary",
    "historical_report",
    "sop_business_process",
}


class BusinessKnowledgeStore:
    def __init__(self, path: Path | None = None) -> None:
        settings = get_settings()
        self._fallback_documents: dict[str, tuple[str, dict]] = {}
        try:
            import chromadb
        except ModuleNotFoundError:
            self.client = None
            self.collection = None
        else:
            self.client = chromadb.PersistentClient(path=str(path or settings.chroma_path))
            self.collection = self.client.get_or_create_collection(
                name="business_knowledge",
                embedding_function=HashEmbeddingFunction(),
            )

    def upsert_document(self, document_id: str, document_type: str, title: str, content: str) -> None:
        if document_type not in ALLOWED_DOCUMENT_TYPES:
            raise ValueError(
                "ChromaDB only stores Business Knowledge, Data Dictionary, Historical Reports, "
                "and SOP / Business Process documents"
            )
        document = f"Title: {title}\nType: {document_type}\n\n{content}"
        metadata = {
            "document_id": document_id,
            "document_type": document_type,
            "title": title,
        }
        if self.collection is None:
            self._fallback_documents[document_id] = (document, metadata)
            return
        self.collection.upsert(
            ids=[document_id],
            documents=[document],
            metadatas=[metadata],
        )

    def delete_document(self, document_id: str) -> None:
        if self.collection is None:
            self._fallback_documents.pop(document_id, None)
            return
        self.collection.delete(ids=[document_id])

    def search(
        self,
        query: str,
        document_types: Iterable[str] | None = None,
        limit: int = 5,
    ) -> list[dict]:
        types = list(document_types or [])
        invalid_types = set(types) - ALLOWED_DOCUMENT_TYPES
        if invalid_types:
            raise ValueError(f"Unsupported business document type: {sorted(invalid_types)[0]}")
        if self.collection is None:
            allowed_types = set(types)
            terms = [term for term in query.lower().split() if term]
            matches = []
            for document, metadata in self._fallback_documents.values():
                if allowed_types and metadata["document_type"] not in allowed_types:
                    continue
                haystack = document.lower()
                if not terms or any(term in haystack for term in terms):
                    matches.append({"document": document, "metadata": metadata})
            return matches[:limit]
        where = {"document_type": types[0]} if len(types) == 1 else None
        result = self.collection.query(query_texts=[query], n_results=limit, where=where)
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        return [{"document": document, "metadata": metadata} for document, metadata in zip(documents, metadatas)]
