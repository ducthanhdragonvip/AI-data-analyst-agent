from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.config import get_settings
from app.database import Base, engine, get_session
from app.models import Artifact, Job
from app.schemas import ArtifactOut, ChatRequest, CreateJobResponse, DatabaseTableOut, DatasetOut, JobOut, ReportRequest
from app.services.database_introspection import list_database_tables
from app.services.datasets import DatasetService

settings = get_settings()

app = FastAPI(title="AI Data Analyst Agent", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/datasets", response_model=list[DatasetOut])
async def list_datasets(session: AsyncSession = Depends(get_session)) -> list:
    return await DatasetService(session).list_datasets()


@app.get("/database/tables", response_model=list[DatabaseTableOut])
async def get_database_tables() -> list[dict]:
    return list_database_tables()


@app.post("/datasets/upload", response_model=DatasetOut)
async def upload_dataset(file: UploadFile = File(...), session: AsyncSession = Depends(get_session)):
    content = await file.read()
    try:
        dataset = await DatasetService(session).ingest_upload(file.filename or "dataset.csv", content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await session.commit()
    return dataset


@app.post("/datasets/{dataset_id}/import", response_model=DatasetOut)
async def import_dataset_to_database(dataset_id: int, session: AsyncSession = Depends(get_session)):
    try:
        dataset = await DatasetService(session).import_upload_to_database(dataset_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    await session.commit()
    return dataset


@app.post("/datasets/postgres/refresh", response_model=list[DatasetOut])
async def refresh_postgres(session: AsyncSession = Depends(get_session)) -> list:
    datasets = await DatasetService(session).refresh_postgres_tables()
    await session.commit()
    return datasets


@app.delete("/datasets/{dataset_id}", status_code=204)
async def delete_dataset(dataset_id: int, session: AsyncSession = Depends(get_session)) -> None:
    deleted = await DatasetService(session).delete_dataset(dataset_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Dataset not found")
    await session.commit()


@app.post("/chat", response_model=CreateJobResponse)
async def chat(request: ChatRequest, session: AsyncSession = Depends(get_session)) -> CreateJobResponse:
    job = Job(job_type="analysis", status="pending", input=request.model_dump())
    session.add(job)
    await session.commit()
    return CreateJobResponse(job_id=job.id)


@app.post("/reports", response_model=CreateJobResponse)
async def reports(request: ReportRequest, session: AsyncSession = Depends(get_session)) -> CreateJobResponse:
    job = Job(job_type="report", status="pending", input=request.model_dump())
    session.add(job)
    await session.commit()
    return CreateJobResponse(job_id=job.id)


@app.get("/jobs/{job_id}", response_model=JobOut)
async def get_job(job_id: int, session: AsyncSession = Depends(get_session)) -> Job:
    job = await session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/artifacts/{artifact_id}")
async def get_artifact(artifact_id: int, session: AsyncSession = Depends(get_session)):
    artifact = await session.get(Artifact, artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    if artifact.payload is not None:
        return ArtifactOut.model_validate(artifact)
    if not artifact.path:
        raise HTTPException(status_code=404, detail="Artifact has no file")
    path = Path(artifact.path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact file missing")
    return FileResponse(path, media_type=artifact.mime_type, filename=path.name)


@app.get("/artifacts/{artifact_id}/metadata", response_model=ArtifactOut)
async def get_artifact_metadata(artifact_id: int, session: AsyncSession = Depends(get_session)) -> Artifact:
    artifact = await session.get(Artifact, artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return artifact


@app.get("/artifacts/{artifact_id}/file")
async def get_artifact_file(artifact_id: int, session: AsyncSession = Depends(get_session)):
    artifact = await session.get(Artifact, artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    if not artifact.path:
        raise HTTPException(status_code=404, detail="Artifact has no file")
    path = Path(artifact.path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact file missing")
    return FileResponse(path, media_type=artifact.mime_type, filename=path.name)


@app.get("/artifacts", response_model=list[ArtifactOut])
async def list_artifacts(session: AsyncSession = Depends(get_session)) -> list:
    result = await session.execute(select(Artifact).order_by(Artifact.created_at.desc()).limit(50))
    return list(result.scalars())
