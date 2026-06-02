import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Artifact


async def create_payload_artifact(
    session: AsyncSession,
    *,
    job_id: int | None,
    kind: str,
    title: str,
    mime_type: str,
    payload: dict[str, Any],
) -> Artifact:
    artifact = Artifact(job_id=job_id, kind=kind, title=title, mime_type=mime_type, payload=payload)
    session.add(artifact)
    await session.flush()
    return artifact


async def create_markdown_artifact(session: AsyncSession, *, job_id: int, title: str, content: str) -> Artifact:
    settings = get_settings()
    path = settings.artifact_dir / f"report-{job_id}.md"
    path.write_text(content, encoding="utf-8")
    artifact = Artifact(job_id=job_id, kind="report", title=title, mime_type="text/markdown", path=str(path))
    session.add(artifact)
    await session.flush()
    return artifact


async def create_plotly_bar_artifact(
    session: AsyncSession,
    *,
    job_id: int,
    title: str,
    frame: pd.DataFrame,
    x: str,
    y: str,
) -> Artifact:
    fig = px.bar(frame, x=x, y=y, title=title)
    payload = json.loads(fig.to_json())
    return await create_payload_artifact(
        session,
        job_id=job_id,
        kind="plotly",
        title=title,
        mime_type="application/vnd.plotly.v1+json",
        payload=payload,
    )


async def create_matplotlib_line_artifact(
    session: AsyncSession,
    *,
    job_id: int,
    title: str,
    frame: pd.DataFrame,
    x: str,
    y: str,
) -> Artifact:
    settings = get_settings()
    path = Path(settings.artifact_dir) / f"chart-{job_id}.png"
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(frame[x], frame[y], marker="o")
    ax.set_title(title)
    ax.set_xlabel(x)
    ax.set_ylabel(y)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    artifact = Artifact(job_id=job_id, kind="matplotlib", title=title, mime_type="image/png", path=str(path))
    session.add(artifact)
    await session.flush()
    return artifact
