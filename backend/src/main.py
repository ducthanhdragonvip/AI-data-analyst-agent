from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.core.config import get_settings
from src.core.config import REPO_DIR
from src.core.database import Base, engine
from src.modules.api.routes import artifacts, conversations, datasets, jobs, knowledge

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


ROUTERS = [datasets.router, conversations.router, jobs.router, artifacts.router, knowledge.router]
for router in ROUTERS:
    app.include_router(router)
    app.include_router(router, prefix="/api")

frontend_dist = REPO_DIR / "frontend" / "dist"
if frontend_dist.exists():
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def serve_spa(path: str) -> FileResponse:
        requested = (frontend_dist / path).resolve()
        if path and requested.exists() and frontend_dist.resolve() in requested.parents:
            return FileResponse(requested)
        return FileResponse(frontend_dist / "index.html")
