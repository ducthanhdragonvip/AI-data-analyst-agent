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


class JobOut(BaseModel):
    id: int
    job_type: Literal["analysis", "report"]
    status: Literal["pending", "running", "succeeded", "failed"]
    input: dict[str, Any]
    result: dict[str, Any] | None = None
    error: str | None = None

    model_config = {"from_attributes": True}


class CreateJobResponse(BaseModel):
    job_id: int


class ArtifactOut(BaseModel):
    id: int
    kind: str
    title: str
    mime_type: str
    payload: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class DatabaseTableOut(BaseModel):
    table_schema: str
    table_name: str
