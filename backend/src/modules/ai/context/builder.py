from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.core.config import get_settings
from src.core.models import Dataset, Message
from src.modules.data.loaders.dataset_profile import profile_to_text
from src.modules.data.loaders.tabular import load_uploaded_frame, summarize_frame
from src.modules.data.vector_db.chroma_store import BusinessKnowledgeStore


async def load_datasets(session: AsyncSession, dataset_ids: list[int]) -> list[Dataset]:
    if dataset_ids:
        result = await session.execute(select(Dataset).where(Dataset.id.in_(dataset_ids)))
        return list(result.scalars())
    result = await session.execute(select(Dataset).order_by(Dataset.created_at.desc()).limit(5))
    return list(result.scalars())


async def build_context(session: AsyncSession, question: str, dataset_ids: list[int], conversation_id: int | None) -> str:
    datasets = await load_datasets(session, dataset_ids)
    settings = get_settings()
    profile_text = "\n\n".join(
        profile_to_text(dataset.display_name, dataset.table_schema, dataset.table_name, dataset.profile)
        for dataset in datasets
    )
    local_summaries = []
    for dataset in datasets:
        if dataset.source_type == "upload" and dataset.file_name and not dataset.table_name:
            frame = load_uploaded_frame(settings.upload_dir, dataset.file_name)
            local_summaries.append(summarize_frame(dataset.display_name, frame))
    business_hits = BusinessKnowledgeStore().search(question)
    business_text = "\n\n".join(hit["document"] for hit in business_hits)
    history = ""
    if conversation_id:
        messages = await session.execute(
            select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.desc()).limit(8)
        )
        history = "\n".join(f"{message.role}: {message.content}" for message in reversed(list(messages.scalars())))
    return (
        f"Dataset profiles:\n{profile_text or 'No datasets registered.'}\n\n"
        f"Local file summaries:\n{chr(10).join(local_summaries) or 'No staged local files selected.'}\n\n"
        f"Business knowledge matches:\n{business_text or 'No business knowledge matches.'}\n\n"
        f"Recent conversation:\n{history or 'No prior messages.'}"
    )
