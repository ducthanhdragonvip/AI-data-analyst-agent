from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Conversation, Message


def message_to_dict(message: Message) -> dict[str, Any]:
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "artifact_ids": message.artifact_ids or [],
        "created_at": message.created_at,
    }


async def list_recent_conversations(session: AsyncSession, limit: int = 30) -> list[dict[str, Any]]:
    last_message_subquery = (
        select(
            Message.conversation_id,
            func.max(Message.created_at).label("last_message_at"),
            func.count(Message.id).label("message_count"),
        )
        .group_by(Message.conversation_id)
        .subquery()
    )
    result = await session.execute(
        select(
            Conversation,
            last_message_subquery.c.last_message_at,
            last_message_subquery.c.message_count,
        )
        .outerjoin(last_message_subquery, Conversation.id == last_message_subquery.c.conversation_id)
        .order_by(func.coalesce(last_message_subquery.c.last_message_at, Conversation.created_at).desc())
        .limit(limit)
    )
    return [
        {
            "id": conversation.id,
            "title": conversation.title,
            "created_at": conversation.created_at,
            "last_message_at": last_message_at or conversation.created_at,
            "message_count": int(message_count or 0),
        }
        for conversation, last_message_at, message_count in result.all()
    ]


async def get_conversation_detail(session: AsyncSession, conversation_id: int) -> dict[str, Any] | None:
    conversation = await session.get(Conversation, conversation_id)
    if not conversation:
        return None
    result = await session.execute(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at, Message.id)
    )
    messages = [message_to_dict(message) for message in result.scalars()]
    return {
        "id": conversation.id,
        "title": conversation.title,
        "created_at": conversation.created_at,
        "messages": messages,
    }


def conversation_was_deleted(found: bool) -> bool:
    return found


async def delete_conversation(session: AsyncSession, conversation_id: int) -> bool:
    conversation = await session.get(Conversation, conversation_id)
    if not conversation:
        return conversation_was_deleted(False)
    await session.execute(delete(Message).where(Message.conversation_id == conversation_id))
    await session.delete(conversation)
    return conversation_was_deleted(True)
