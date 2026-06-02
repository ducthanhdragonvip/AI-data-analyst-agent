import asyncio
import logging

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import Job
from app.services.agent_runner import DataAnalystAgent
from app.services.jobs import JobStateMachine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("analyst-worker")


async def claim_next_job() -> Job | None:
    async with AsyncSessionLocal() as session:
        async with session.begin():
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


async def run_job(job_id: int) -> None:
    async with AsyncSessionLocal() as session:
        job = await session.get(Job, job_id)
        if not job:
            return
        agent = DataAnalystAgent(session)
        try:
            if job.job_type == "analysis":
                result = await agent.run_analysis_job(job)
            elif job.job_type == "report":
                result = await agent.run_report_job(job)
            else:
                raise ValueError(f"Unknown job type: {job.job_type}")
            machine = JobStateMachine(job.status)
            machine.transition_to("succeeded")
            job.status = machine.status
            job.result = result
            job.error = None
        except Exception as exc:
            logger.exception("Job %s failed", job.id)
            machine = JobStateMachine(job.status)
            machine.transition_to("failed")
            job.status = machine.status
            job.error = str(exc)
        await session.commit()


async def worker_loop() -> None:
    logger.info("Worker started")
    while True:
        job = await claim_next_job()
        if job:
            await run_job(job.id)
        else:
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(worker_loop())
