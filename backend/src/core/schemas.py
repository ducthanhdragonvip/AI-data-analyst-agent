from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class DatasetOut(BaseModel):
    id: int
    source_type: str
    display_name: str
    table_schema: str | None
    table_name: str | None
    is_imported: bool
    row_count: int
    profile: dict[str, Any]

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    conversation_id: int | None = None
    dataset_ids: list[int] = Field(default_factory=list)
    message: str = Field(min_length=1)


class ReportRequest(BaseModel):
    conversation_id: int | None = None
    dataset_ids: list[int] = Field(default_factory=list)
    instructions: str | None = None


class CreateJobResponse(BaseModel):
    job_id: int


class JobOut(BaseModel):
    id: int
    job_type: Literal["analysis", "report"]
    status: Literal["pending", "running", "succeeded", "failed"]
    input: dict[str, Any]
    result: dict[str, Any] | None = None
    error: str | None = None

    model_config = {"from_attributes": True}


class ArtifactOut(BaseModel):
    id: int
    kind: str
    title: str
    mime_type: str
    payload: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class ConversationMessageOut(BaseModel):
    id: int
    role: Literal["user", "assistant", "system"]
    content: str
    artifact_ids: list[int]
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationSummaryOut(BaseModel):
    id: int
    title: str
    created_at: datetime
    last_message_at: datetime
    message_count: int


class ConversationDetailOut(BaseModel):
    id: int
    title: str
    created_at: datetime
    messages: list[ConversationMessageOut]


class BusinessKnowledgeUpsert(BaseModel):
    document_id: str = Field(min_length=1)
    document_type: Literal[
        "business_knowledge",
        "data_dictionary",
        "historical_report",
        "sop_business_process",
    ]
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)


class BusinessKnowledgeSearch(BaseModel):
    query: str = Field(min_length=1)
    document_types: list[
        Literal[
            "business_knowledge",
            "data_dictionary",
            "historical_report",
            "sop_business_process",
        ]
    ] = Field(default_factory=list)
    limit: int = Field(default=5, ge=1, le=20)


class BusinessKnowledgeHit(BaseModel):
    document: str
    metadata: dict[str, Any]
