from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.schemas import DatasetOut
from src.modules.data.loaders.datasets import DatasetService

router = APIRouter()


@router.get("/datasets", response_model=list[DatasetOut])
async def list_datasets(session: AsyncSession = Depends(get_session)):
    return await DatasetService(session).list_datasets()


@router.post("/datasets/upload", response_model=DatasetOut)
async def upload_dataset(file: UploadFile = File(...), session: AsyncSession = Depends(get_session)):
    content = await file.read()
    try:
        dataset = await DatasetService(session).ingest_upload(file.filename or "dataset.csv", content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await session.commit()
    return dataset


@router.post("/datasets/{dataset_id}/import", response_model=DatasetOut)
async def import_dataset(dataset_id: int, session: AsyncSession = Depends(get_session)):
    try:
        dataset = await DatasetService(session).import_upload_to_database(dataset_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    await session.commit()
    return dataset


@router.post("/datasets/postgres/refresh", response_model=list[DatasetOut])
async def refresh_postgres(session: AsyncSession = Depends(get_session)):
    datasets = await DatasetService(session).refresh_postgres_tables()
    await session.commit()
    return datasets


@router.delete("/datasets/{dataset_id}", status_code=204)
async def delete_dataset(dataset_id: int, session: AsyncSession = Depends(get_session)) -> None:
    deleted = await DatasetService(session).delete_dataset(dataset_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Dataset not found")
    await session.commit()
