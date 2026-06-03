from fastapi import APIRouter, HTTPException

from src.core.schemas import BusinessKnowledgeHit, BusinessKnowledgeSearch, BusinessKnowledgeUpsert
from src.modules.data.vector_db.chroma_store import BusinessKnowledgeStore

router = APIRouter()


@router.post("/knowledge", status_code=204)
async def upsert_knowledge_document(request: BusinessKnowledgeUpsert) -> None:
    try:
        BusinessKnowledgeStore().upsert_document(
            document_id=request.document_id,
            document_type=request.document_type,
            title=request.title,
            content=request.content,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/knowledge/search", response_model=list[BusinessKnowledgeHit])
async def search_knowledge_documents(request: BusinessKnowledgeSearch) -> list[dict]:
    try:
        return BusinessKnowledgeStore().search(
            request.query,
            document_types=request.document_types,
            limit=request.limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
