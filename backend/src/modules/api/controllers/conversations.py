from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.core.models import Conversation, Message


async def list_recent_conversations(session: AsyncSession) -> list[dict]:
    result = await session.execute(
        select(
            Conversation.id,
            Conversation.title,
            Conversation.created_at,
            func.max(Message.created_at).label("last_message_at"),
            func.count(Message.id).label("message_count"),
        )
        .join(Message, Message.conversation_id == Conversation.id, isouter=True)
        .group_by(Conversation.id)
        .order_by(func.max(Message.created_at).desc().nullslast(), Conversation.created_at.desc())
    )
    return [
        {
            "id": row.id,
            "title": row.title,
            "created_at": row.created_at,
            "last_message_at": row.last_message_at or row.created_at,
            "message_count": int(row.message_count),
        }
        for row in result
    ]


async def get_conversation_detail(session: AsyncSession, conversation_id: int) -> dict | None:
    conversation = await session.get(Conversation, conversation_id)
    if not conversation:
        return None
    messages_result = await session.execute(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at, Message.id)
    )
    return {
        "id": conversation.id,
        "title": conversation.title,
        "created_at": conversation.created_at,
        "messages": list(messages_result.scalars()),
    }


async def delete_conversation(session: AsyncSession, conversation_id: int) -> bool:
    conversation = await session.get(Conversation, conversation_id)
    if not conversation:
        return False
    await session.delete(conversation)
    return True
