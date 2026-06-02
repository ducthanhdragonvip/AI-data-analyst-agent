# AI Data Analyst Agent

Local/demo full-stack AI data analyst app using FastAPI, LangChain ReAct, GPT-4o, ChromaDB, Postgres, React TypeScript, Plotly, and Matplotlib.

## What It Does

- Upload CSV/XLSX files and register them as analyzable Postgres tables.
- Uploaded files are staged first and can be analyzed from the local file. Data rows are written into Postgres only after clicking **Save to DB**.
- Refresh local Postgres tables for analysis.
- Chat with the agent in natural language.
- Generate Plotly and Matplotlib chart artifacts.
- Continue conversations with follow-up questions.
- Generate downloadable Markdown reports.
- Use ChromaDB for schema/profile RAG context.

## Prerequisites

- Python 3.11. On Windows, do not use Python 3.12 for this project because `chroma-hnswlib`, a ChromaDB dependency, does not provide the needed stable Windows wheel for Python 3.12 and will try to compile C++.
- Node.js 20+
- Docker Desktop
- OpenAI API key

## Setup

```powershell
Copy-Item .env.example .env
docker compose up -d postgres

cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python scripts\check_python_version.py
pip install -r requirements.txt
python -m app.db_init
uvicorn app.main:app --reload --port 8000
```

If `py -3.11` is not found, install Python 3.11 from https://www.python.org/downloads/release/python-3119/ and make sure the launcher is installed. Check available versions with:

```powershell
py -0p
```

Alternative: install Microsoft C++ Build Tools and keep Python 3.12, but Python 3.11 is the cleaner path for this local demo.

### Fix a Broken Virtualenv

If you see an error like `No module named 'pydantic_core._pydantic_core'`, the backend virtualenv was likely created or partially installed with the wrong Python version. Delete and recreate it instead of reinstalling packages into the same `.venv`:

```powershell
cd C:\Users\JT\Desktop\AI\backend
deactivate
Remove-Item -Recurse -Force .venv
py -3.11 --version
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python scripts\check_python_version.py
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m app.db_init
```

If `py -3.11 --version` fails, reinstall Python 3.11 and include the Python launcher option in the installer.

In a second terminal:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m worker.main
```

In a third terminal:

```powershell
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:5173

Backend health: http://localhost:8000/healthz

## RAG Design

ChromaDB indexes schema and profile context only: table names, column names, data types, row counts, summary stats, sample values, and prior insights. Calculations are performed with pandas for staged local uploads and read-only SQL for datasets saved in Postgres.

## Uploads

Uploading a CSV/XLSX saves the source file under `backend/storage/uploads` and creates a staged dataset record with profile metadata. It does not create a Postgres data table. You can analyze, chart, and report on the staged file through pandas. Click **Save to DB** only when you want to load that file into a generated Postgres table such as `public.uploaded_sales`.

## Safety

The SQL tool accepts only single-statement `SELECT` or safe `WITH ... SELECT` queries. Mutating SQL, DDL, COPY, and multi-statement requests are rejected before execution.
