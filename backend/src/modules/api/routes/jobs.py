from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.models import Job
from src.core.schemas import ChatRequest, CreateJobResponse, JobOut, ReportRequest
from src.modules.api.controllers.jobs import create_job

router = APIRouter()


@router.post("/chat", response_model=CreateJobResponse)
async def chat(request: ChatRequest, session: AsyncSession = Depends(get_session)) -> CreateJobResponse:
    job = await create_job(session, "analysis", request.model_dump())
    return CreateJobResponse(job_id=job.id)


@router.post("/reports", response_model=CreateJobResponse)
async def reports(request: ReportRequest, session: AsyncSession = Depends(get_session)) -> CreateJobResponse:
    job = await create_job(session, "report", request.model_dump())
    return CreateJobResponse(job_id=job.id)


@router.get("/jobs/{job_id}", response_model=JobOut)
async def get_job(job_id: int, session: AsyncSession = Depends(get_session)) -> Job:
    job = await session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
