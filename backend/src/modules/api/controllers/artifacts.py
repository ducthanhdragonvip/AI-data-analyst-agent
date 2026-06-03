from pathlib import Path

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.core.models import Artifact


async def create_plotly_bar_artifact(
    session: AsyncSession,
    job_id: int,
    title: str,
    frame: pd.DataFrame,
    x: str,
    y: str,
) -> Artifact:
    payload = {
        "data": [{"type": "bar", "x": frame[x].astype(str).tolist(), "y": frame[y].tolist()}],
        "layout": {"title": title, "xaxis": {"title": x}, "yaxis": {"title": y}},
    }
    artifact = Artifact(job_id=job_id, kind="plotly", title=title, mime_type="application/json", payload=payload)
    session.add(artifact)
    await session.flush()
    return artifact


async def create_markdown_artifact(session: AsyncSession, job_id: int, title: str, content: str) -> Artifact:
    settings = get_settings()
    settings.artifact_dir.mkdir(parents=True, exist_ok=True)
    path = settings.artifact_dir / f"job-{job_id}-report.md"
    path.write_text(content, encoding="utf-8")
    artifact = Artifact(job_id=job_id, kind="report", title=title, mime_type="text/markdown", path=str(path))
    session.add(artifact)
    await session.flush()
    return artifact


def artifact_file_path(artifact: Artifact) -> Path:
    if not artifact.path:
        raise ValueError("Artifact has no file")
    return Path(artifact.path)
