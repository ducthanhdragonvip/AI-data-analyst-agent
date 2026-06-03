from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import get_settings
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


app.include_router(datasets.router)
app.include_router(conversations.router)
app.include_router(jobs.router)
app.include_router(artifacts.router)
app.include_router(knowledge.router)
