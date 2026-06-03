from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.core.models import Job


ALLOWED_TRANSITIONS = {
    "pending": {"running", "failed"},
    "running": {"succeeded", "failed"},
    "succeeded": set(),
    "failed": set(),
}


class JobStateMachine:
    def __init__(self, status: str) -> None:
        self.status = status

    def transition_to(self, next_status: str) -> None:
        if next_status not in ALLOWED_TRANSITIONS.get(self.status, set()):
            raise ValueError(f"Cannot transition job from {self.status} to {next_status}")
        self.status = next_status


async def create_job(session: AsyncSession, job_type: str, input_payload: dict) -> Job:
    job = Job(job_type=job_type, status="pending", input=input_payload)
    session.add(job)
    await session.commit()
    return job


async def claim_next_job(session: AsyncSession) -> Job | None:
    result = await session.execute(
        select(Job)
        .where(Job.status == "pending")
        .order_by(Job.created_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    job = result.scalar_one_or_none()
    if not job:
        return None
    machine = JobStateMachine(job.status)
    machine.transition_to("running")
    job.status = machine.status
    await session.flush()
    return job
