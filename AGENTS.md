# Repository Guidelines

## Project Structure & Module Organization

This repository is a local full-stack AI Data Analyst Agent. Backend code lives in `backend/app`, with service logic under `backend/app/services` and background job processing in `backend/worker`. Backend tests are in `backend/tests` and follow `test_*.py` naming. Frontend code lives in `frontend/src`, with the main React app in `frontend/src/App.tsx`, API helpers in `frontend/src/api.ts`, and Tailwind entry styles in `frontend/src/styles.css`. Runtime uploads and generated artifacts are stored under `backend/storage` and root `storage`. Sample data belongs in `samples`.

## Build, Test, and Development Commands

Start Postgres:

```powershell
docker compose up -d postgres
```

Run the backend from `backend`:

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
python -m worker.main
```

Run frontend commands from `frontend`:

```powershell
npm install
npm run dev
npm run build
npm test -- --run
```

Run backend tests from the repository root:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests -q
```

## Coding Style & Naming Conventions

Use Python 3.11 for backend work. Keep FastAPI route handlers thin and put reusable logic in `backend/app/services`. Prefer async database access where the existing code uses `AsyncSession`. Use TypeScript React function components on the frontend. Style UI with Tailwind utilities and shared class constants when repeated; keep custom CSS limited to Tailwind imports and base rules. Use Lucide icons, not emoji UI icons.

## Testing Guidelines

Backend tests use `pytest` and `pytest-asyncio`; frontend tests use `vitest`. Add focused tests for service behavior, SQL safety, dataset handling, conversation history, and API helpers when changing those areas. Test names should describe behavior, for example `test_uploaded_dataset_is_not_imported_by_default`.

## Commit & Pull Request Guidelines

Recent history is minimal (`initial`, `fix`, `feat: add conversation history`). Prefer concise Conventional Commit-style messages such as `feat: add dataset import action` or `fix: reject unsafe sql`. Pull requests should include a short summary, test commands run, linked issue if any, and screenshots for frontend UI changes.

## Security & Configuration Tips

Copy `.env.example` to `.env` and keep secrets out of git. Do not commit uploaded files, generated artifacts, virtual environments, `node_modules`, or build output. The SQL tool should remain read-only and single-statement safe.
