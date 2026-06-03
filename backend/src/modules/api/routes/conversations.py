from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.schemas import ConversationDetailOut, ConversationSummaryOut
from src.modules.api.controllers.conversations import (
    delete_conversation,
    get_conversation_detail,
    list_recent_conversations,
)

router = APIRouter()


@router.get("/conversations", response_model=list[ConversationSummaryOut])
async def list_conversations(session: AsyncSession = Depends(get_session)):
    return await list_recent_conversations(session)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailOut)
async def get_conversation(conversation_id: int, session: AsyncSession = Depends(get_session)):
    conversation = await get_conversation_detail(session, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.delete("/conversations/{conversation_id}", status_code=204)
async def remove_conversation(conversation_id: int, session: AsyncSession = Depends(get_session)) -> None:
    deleted = await delete_conversation(session, conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await session.commit()
