from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.models import Artifact
from src.core.schemas import ArtifactOut

router = APIRouter()


@router.get("/artifacts/{artifact_id}/metadata", response_model=ArtifactOut)
async def get_artifact_metadata(artifact_id: int, session: AsyncSession = Depends(get_session)) -> Artifact:
    artifact = await session.get(Artifact, artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return artifact


@router.get("/artifacts/{artifact_id}/file")
async def get_artifact_file(artifact_id: int, session: AsyncSession = Depends(get_session)):
    artifact = await session.get(Artifact, artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    if artifact.payload is not None:
        return artifact.payload
    if not artifact.path:
        raise HTTPException(status_code=404, detail="Artifact has no file")
    path = Path(artifact.path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact file missing")
    return FileResponse(path, media_type=artifact.mime_type, filename=path.name)
