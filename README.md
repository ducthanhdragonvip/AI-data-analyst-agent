# AI Data Analyst Agent

Full-stack AI data analyst app with FastAPI, LangGraph, ChromaDB business knowledge RAG, Postgres, a polling Python worker, React, and Plotly.

## Local Docker Run

Copy environment values, then start Postgres, the web app, and the worker:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Open:

```text
http://localhost:8000
```

Health check:

```text
http://localhost:8000/healthz
```

The Docker web container serves the built React frontend and FastAPI API. The worker container runs `python -m src.worker.main`.

## Local Non-Docker Run

Start Postgres:

```powershell
docker compose up -d postgres
```

Run backend:

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
```

Run worker in another terminal:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m src.worker.main
```

Run frontend dev server:

```powershell
cd frontend
npm install
npm run dev
```

Frontend dev URL: `http://localhost:5173`

## Railway Deployment

Create three Railway services:

- Postgres database service
- Web service from this repo using `Dockerfile`
- Worker service from this repo using the same `Dockerfile`

Web service:

- Start command can use the Dockerfile default:
  ```sh
  uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}
  ```
- Public networking should target the Railway-provided `PORT`.
- Healthcheck path: `/healthz`

Worker service:

```sh
python -m src.worker.main
```

Recommended Railway variables for both web and worker:

```text
DATABASE_URL=${{ Postgres.DATABASE_URL }}
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4.1-mini
EMBEDDING_MODEL=text-embedding-3-small
STORAGE_DIR=/app/backend/storage
UPLOAD_DIR=/app/backend/storage/uploads
ARTIFACT_DIR=/app/backend/storage/artifacts
CHROMA_PATH=/app/backend/storage/chroma
CORS_ORIGINS=["https://your-web-domain.up.railway.app"]
```

The app normalizes Railway `postgresql://...` URLs into SQLAlchemy async and sync URLs internally. `SYNC_DATABASE_URL` is optional on Railway.

For persistent uploads/artifacts/Chroma data, attach a Railway volume to the web and worker services and mount it at `/app/backend/storage`.

## GitHub Actions CI/CD

CI runs on pull requests and pushes to `main`:

```text
.github/workflows/ci.yml
```

It runs:

- Backend tests with Python 3.11 and Postgres
- Frontend tests and build with Node 22
- Docker image build

Railway deploy workflow:

```text
.github/workflows/railway-deploy.yml
```

Required GitHub secrets:

```text
RAILWAY_TOKEN
RAILWAY_PROJECT_ID
RAILWAY_WEB_SERVICE_ID
RAILWAY_WORKER_SERVICE_ID
```

Required GitHub variable:

```text
RAILWAY_DEPLOY_ENABLED=true
```

Optional GitHub variable:

```text
RAILWAY_ENVIRONMENT=production
```

The deploy workflow uses Railway CLI `railway up --ci --project ... --environment ... --service ...`, matching Railway's documented CI mode and service targeting.

## Verification

Backend:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests -q
```

Frontend:

```powershell
cd frontend
npm run build
```

Docker:

```powershell
docker compose up --build
```
