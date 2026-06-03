from typing import Any

from src.modules.ai.tools.result import tool_result
from src.modules.data.vector_db.chroma_store import BusinessKnowledgeStore


class RagTools:
    def __init__(self, business_store: BusinessKnowledgeStore | None = None) -> None:
        self.business_store = business_store or BusinessKnowledgeStore()

    async def search_business_knowledge(
        self,
        query: str,
        document_types: list[str] | None = None,
    ) -> dict[str, Any]:
        try:
            hits = self.business_store.search(query, document_types=document_types or [])
        except ValueError as exc:
            return tool_result("search_business_knowledge", "error", str(exc))
        return tool_result(
            "search_business_knowledge",
            "ok",
            f"Found {len(hits)} business knowledge matches.",
            {"hits": hits},
        )
