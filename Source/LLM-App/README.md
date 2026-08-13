# RAG QA Healthcare App

FastAPI backend for healthcare RAG Q&A with ChromaDB retrieval, Claude responses,
and optional Guardrail SDK checks.

This repo has two app entrypoints:

- `app.main`: original implementation using the local Anthropic wrapper.
- `app.main2`: alternate implementation that routes retrieval and LLM calls through
  LangChain.

## Setup

Create and activate a virtual environment from the project root:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install the base dependencies:

```bash
pip install -r requirements.txt
```

`main2.py` requires the Anthropic and Chroma LangChain integrations:

```bash
pip install langchain-anthropic langchain-chroma
```

Create `.env` from the example if needed:

```bash
cp .env.example .env
```

Set `ANTHROPIC_API_KEY` in `.env`.

## Run `main.py`

Run the original FastAPI app:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open:

```text
http://localhost:8000/docs
```

## Run `main2.py`

Run the LangChain-oriented FastAPI app on a different port:

```bash
uvicorn app.main2:app --reload --host 0.0.0.0 --port 8001
```

Open:

```text
http://localhost:8001/docs
```

`main2.py` requires `langchain-anthropic`, `langchain-chroma`, and
`langchain-core` to be installed.

## Useful Endpoints

- `GET /health`: check ChromaDB, rules file, and guardrail status.
- `POST /query`: ask a RAG-backed question.
- `POST /ingest`: upload and ingest a CSV file.
- `GET /rules`: view active guardrail rules.
- `POST /rules/reload`: reload `guardrails.yaml`.

Example query:

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question":"What medications are used for infections?","top_k":5}'
```

For `main2.py`, change the port to `8001`.

## Tests

Run tests from the project root:

```bash
pytest
```

## Docker
### Clean chromadb
```bash
rm -rf ~/Development/projects/ragqaapp/chroma_db/*
```
### Run Composer
```bash
cd ~/Development/projects/ragqaapp
docker compose up --build
```

### API
API: http://localhost:8000
Demo UI: http://localhost:9091
Rules UI: http://localhost:8081

