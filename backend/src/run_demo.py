import asyncio
import os
import signal
import sys


async def main() -> int:
    port = os.getenv("PORT", "8000")
    worker = await asyncio.create_subprocess_exec(sys.executable, "-m", "src.worker.main")
    web = await asyncio.create_subprocess_exec(
        "uvicorn",
        "src.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        port,
    )

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass

    stop_task = asyncio.create_task(stop_event.wait())
    worker_task = asyncio.create_task(worker.wait())
    web_task = asyncio.create_task(web.wait())
    done, pending = await asyncio.wait(
        {stop_task, worker_task, web_task},
        return_when=asyncio.FIRST_COMPLETED,
    )

    for process in (worker, web):
        if process.returncode is None:
            process.terminate()
    await asyncio.gather(worker.wait(), web.wait(), return_exceptions=True)
    for task in pending:
        task.cancel()

    if stop_task in done:
        return 0
    return next(iter(done)).result() or 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
