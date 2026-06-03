import asyncio
import logging

from src.core.database import AsyncSessionLocal
from src.core.models import Job
from src.modules.ai.chain.graph import DataAnalystWorkflow
from src.modules.api.controllers.jobs import JobStateMachine, claim_next_job

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("analyst-worker")


async def run_job(job_id: int) -> None:
    async with AsyncSessionLocal() as session:
        job = await session.get(Job, job_id)
        if not job:
            return
        try:
            result = await DataAnalystWorkflow(session).run(job)
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
        async with AsyncSessionLocal() as session:
            async with session.begin():
                job = await claim_next_job(session)
                job_id = job.id if job else None
        if job_id is None:
            await asyncio.sleep(2)
            continue
        await run_job(job_id)


if __name__ == "__main__":
    asyncio.run(worker_loop())
