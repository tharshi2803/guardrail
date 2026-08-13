"""FastAPI RAG QA app variant using LangChain for LLM orchestration."""

from __future__ import annotations

import secrets
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import chromadb
from fastapi import Body, Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from langchain_anthropic import ChatAnthropic
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from .config import settings
from .context import build_prompt
from .ingestion import ingest_allergies, ingest_csv, resolve_data_paths
from .rules_loader import get_rules, start_watcher, stop_watcher

# Module-level state
_chroma_client: chromadb.ClientAPI | None = None
_collection: chromadb.Collection | None = None
_vector_store: Chroma | None = None
_pipeline = None  # GuardrailPipeline - set during lifespan


def _get_collection() -> chromadb.Collection:
    """Return the active ChromaDB collection.

    The collection is created during FastAPI startup in `lifespan`. Endpoints
    call this helper instead of reading `_collection` directly so startup bugs
    fail with a clear error message.
    """
    if _collection is None:
        raise RuntimeError("ChromaDB collection not initialised")
    return _collection


def _refresh_pipeline() -> None:
    """Reload the rules file into the active guardrail pipeline."""
    if _pipeline is None:
        return
    try:
        from guardrail_sdk import GuardrailConfig

        _pipeline.update_config(GuardrailConfig.from_yaml(settings.RULES_FILE))
    except Exception:
        pass


def _get_vector_store() -> Chroma:
    """Return the active LangChain Chroma vector store.

    `main2.py` uses LangChain for retrieval, but ingestion still writes through
    the underlying Chroma collection. Both objects point at the same persisted
    collection, so uploaded or auto-ingested records are immediately retrievable.
    """
    if _vector_store is None:
        raise RuntimeError("LangChain Chroma vector store not initialised")
    return _vector_store


def _content_to_text(content: Any) -> str:
    """Normalise LangChain chat message content into a plain string.

    LangChain chat models usually return `AIMessage.content` as a string, but
    some providers can return a list of content blocks. This helper accepts both
    shapes and extracts text blocks so the API response model always receives a
    simple answer string.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "\n".join(parts)
    return str(content)


def ask_llm_langchain(system_prompt: str, user_message: str, model: str | None = None) -> str:
    """Generate an answer with Anthropic Claude through LangChain.

    Args:
        system_prompt: Instruction text that controls assistant behavior.
        user_message: The retrieved context plus the user's question.
        model: Optional model override. Defaults to `settings.LLM_MODEL`.

    Returns:
        The assistant answer as plain text.

    The prompt is built as a two-message chat prompt to preserve the existing
    contract from `build_prompt`: system instructions stay separate from the
    user message that contains XML-isolated retrieved context.
    """
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "{system_prompt}"),
            ("human", "{user_message}"),
        ]
    )
    llm = ChatAnthropic(
        anthropic_api_key=settings.ANTHROPIC_API_KEY,
        model_name=model or settings.LLM_MODEL,
        max_tokens=1024,
    )
    response = (prompt | llm).invoke(
        {
            "system_prompt": system_prompt,
            "user_message": user_message,
        }
    )
    text = _content_to_text(response.content)
    if not text.strip():
        # Sonnet 5's safety classifier can decline a request (stop_reason
        # "refusal") and return empty content — surface it instead of a blank.
        stop_reason = (getattr(response, "response_metadata", {}) or {}).get("stop_reason")
        if stop_reason == "refusal":
            return "[The model declined to answer this request (safety refusal).]"
        return "[The model returned an empty response.]"
    return text


def retrieve_langchain(
    query: str, top_k: int = 10, filters: dict[str, str] | None = None
) -> list[dict]:
    """Retrieve the most relevant document chunks through LangChain Chroma.

    Args:
        query: The user question to embed and search against ChromaDB.
        top_k: Maximum number of nearest chunks to return.

    Returns:
        A list of chunk dictionaries matching the shape expected by
        `build_prompt`, guardrail sanitisation, and the `/query` response.

    LangChain returns `Document` objects plus similarity scores. The rest of the
    app already expects dicts with `id`, `content`, `metadata`, and `distance`,
    so this function adapts LangChain's return type without changing downstream
    code.
    """
    docs_with_scores = _get_vector_store().similarity_search_with_score(
        query,
        k=top_k,
        filter=filters,
    )

    chunks: list[dict] = []
    for index, (doc, score) in enumerate(docs_with_scores, start=1):
        metadata = dict(doc.metadata or {})
        chunks.append(
            {
                "id": doc.id or metadata.get("id") or f"doc_{index}",
                "content": doc.page_content,
                "metadata": metadata,
                "distance": score,
            }
        )
    return chunks


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise and tear down shared application resources.

    Startup work:
    - Opens the persisted ChromaDB client and collection.
    - Wraps the same collection with LangChain's `Chroma` vector store.
    - Auto-ingests the sample healthcare CSV when the collection is empty.
    - Starts the guardrail rules watcher.
    - Attempts to initialise the Guardrail SDK pipeline.

    Shutdown work:
    - Stops the guardrail rules watcher.

    The Guardrail SDK is optional here by design: if its import or setup fails,
    the app still runs as an unguarded RAG service.
    """
    global _chroma_client, _collection, _vector_store, _pipeline

    # ChromaDB remains the persisted source of retrieved healthcare records.
    _chroma_client = chromadb.PersistentClient(path=settings.CHROMA_PATH)
    _collection = _chroma_client.get_or_create_collection(
        name=settings.CHROMA_COLLECTION
    )
    # LangChain uses the same client/collection for similarity search.
    _vector_store = Chroma(
        client=_chroma_client,
        collection_name=settings.CHROMA_COLLECTION,
    )

    # Prefer the full patients.csv/allergies.csv; fall back to the *_demo.csv.
    patients_path, allergies_path = resolve_data_paths("data")
    if _collection.count() == 0 and patients_path.exists() and allergies_path.exists():
        ingest_allergies(patients_path, allergies_path, _collection)

    start_watcher(settings.RULES_FILE)

    try:
        from guardrail_sdk import GuardrailConfig, GuardrailPipeline

        config = GuardrailConfig.from_yaml(settings.RULES_FILE)
        _pipeline = GuardrailPipeline(
            config,
            anthropic_api_key=settings.ANTHROPIC_API_KEY,
            rules_file=settings.RULES_FILE,
        )
    except Exception:
        _pipeline = None

    yield

    stop_watcher()


app = FastAPI(title="RAG QA Healthcare App", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


_security = HTTPBasic()


def require_admin(credentials: HTTPBasicCredentials = Depends(_security)) -> str:
    """Validate administrator credentials using constant-time comparison."""
    user_ok = secrets.compare_digest(credentials.username, settings.GUARDRAIL_USER)
    pass_ok = secrets.compare_digest(credentials.password, settings.GUARDRAIL_PASSWORD)
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


class QueryRequest(BaseModel):
    question: str
    session_id: str | None = None
    top_k: int = 10
    filters: dict[str, str] | None = None


class QueryResponse(BaseModel):
    answer: str
    sources: list[dict]
    guard_result: dict


class IngestResponse(BaseModel):
    chunk_count: int
    doc_id: str


class DemoResponse(BaseModel):
    """Per-stage trace of the guardrail pipeline for the demo visualiser."""

    question: str
    session_id: str
    input: dict
    llm: dict
    output: dict
    verdict: str


class HealthResponse(BaseModel):
    status: str
    backend: str
    chroma_collection: str
    doc_count: int
    rules_file: str
    guardrails_active: bool


@app.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    """Answer a user question with guarded retrieval-augmented generation.

    Flow:
    1. Run the input guardrail check before retrieval or LLM execution.
    2. Retrieve relevant chunks with LangChain Chroma.
    3. Sanitise retrieved chunks if the Guardrail SDK is active.
    4. Build the XML-isolated RAG prompt.
    5. Generate an answer through LangChain Anthropic.
    6. Run the output guardrail check and return answer plus sources.

    Raises:
        HTTPException: 400 when guardrails block input/output, or 404 when
        retrieval finds no relevant documents.
    """
    session_id = req.session_id or "default"

    # L1/L2/L6-style input checks happen before retrieval and model calls.
    # Use the L1-normalised text downstream so retrieval and the LLM never see
    # the raw encoding L1 defangs (e.g. a Base64 blob).
    query_text = req.question
    if _pipeline:
        input_result = await _pipeline.check_input(req.question, session_id=session_id)
        if input_result.blocked:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "blocked",
                    "reason_code": input_result.reason_code,
                    "layer": input_result.layer,
                    "severity": input_result.severity,
                },
            )
        query_text, _ = _pipeline._l1.normalise(req.question, redact=False)

    chunks = retrieve_langchain(query_text, top_k=req.top_k, filters=req.filters)
    if not chunks:
        raise HTTPException(status_code=404, detail="No relevant documents found")

    # L4 sanitisation removes or masks unsafe retrieved context before prompting.
    if _pipeline:
        chunks = _pipeline.sanitize_chunks(chunks)

    if _pipeline:
        ctx = _pipeline._get_context(session_id)
        system_msg = ctx.system_prompt
        _, user_msg = build_prompt(query_text, chunks, system_msg)
    else:
        system_msg, user_msg = build_prompt(query_text, chunks)

    answer = ask_llm_langchain(system_msg, user_msg)

    guard_dict: dict = {"passed": True}
    # L5 output checks can block or redact the model response.
    if _pipeline:
        ctx = _pipeline._get_context(session_id)
        output_result = await _pipeline.check_output(answer, ctx)
        if output_result.blocked:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "blocked",
                    "reason_code": output_result.reason_code,
                    "layer": output_result.layer,
                    "severity": output_result.severity,
                },
            )
        if output_result.sanitised_text:
            answer = output_result.sanitised_text
        guard_dict = {
            "passed": True,
            "latency_ms": round(output_result.latency_ms, 2),
        }

    sources = [
        {"id": c["id"], "source": c["metadata"].get("source", ""), "distance": c.get("distance")}
        for c in chunks
    ]

    return QueryResponse(answer=answer, sources=sources, guard_result=guard_dict)


@app.post("/demo/query", response_model=DemoResponse)
async def demo_query(req: QueryRequest):
    """Run the full pipeline and return a stage-by-stage trace."""
    print("REQUEST TOP_K:", req.top_k)
    session_id = req.session_id or "demo"

    input_stage: dict = {
        "normalized": req.question,
        "blocked": False,
        "reason_code": None,
        "layer": None,
        "severity": None,
        "scores": {},
        "latency_ms": None,
    }
    llm_stage: dict = {"reached": False, "raw_output": None}
    output_stage: dict = {
        "evaluated": False,
        "final_output": None,
        "blocked": False,
        "action": None,
        "reason_code": None,
        "redacted": False,
        "latency_ms": None,
    }

    def _resp(verdict: str) -> DemoResponse:
        return DemoResponse(
            question=req.question,
            session_id=session_id,
            input=input_stage,
            llm=llm_stage,
            output=output_stage,
            verdict=verdict,
        )

    if not _pipeline:
        try:
            chunks = retrieve_langchain(
                req.question, top_k=req.top_k, filters=req.filters
            )
            system_msg, user_msg = build_prompt(req.question, chunks)
            answer = ask_llm_langchain(system_msg, user_msg)
        except Exception as exc:
            answer = f"[error generating answer: {exc}]"
        llm_stage.update(reached=True, raw_output=answer)
        output_stage.update(final_output=answer)
        return _resp("answered")

    # Decode/clean for the LLM but keep PII intact so the L5 output scanner —
    # not L1 input redaction — is what handles PII in the response.
    normalized, _ = _pipeline._l1.normalise(req.question, redact=False)
    input_stage["normalized"] = normalized

    in_res = await _pipeline.check_input(req.question, session_id=session_id)
    input_stage["scores"] = in_res.scores or {}
    input_stage["latency_ms"] = (
        round(in_res.latency_ms, 2) if in_res.latency_ms else None
    )
    if in_res.blocked:
        input_stage.update(
            blocked=True,
            reason_code=in_res.reason_code,
            layer=in_res.layer,
            severity=in_res.severity,
        )
        return _resp("blocked_input")

    try:
        # Use the L1-normalised text downstream — retrieval and the LLM should
        # never see the raw encoding L1 just defanged (e.g. a Base64 blob).
        chunks = retrieve_langchain(
            normalized, top_k=req.top_k, filters=req.filters
        )
        chunks = _pipeline.sanitize_chunks(chunks)
        ctx = _pipeline._get_context(session_id)
        _, user_msg = build_prompt(normalized, chunks, ctx.system_prompt)
        raw = ask_llm_langchain(ctx.system_prompt, user_msg)
    except Exception as exc:
        llm_stage.update(reached=True, raw_output=f"[error generating answer: {exc}]")
        return _resp("answered")

    llm_stage.update(reached=True, raw_output=raw)
    out_res = await _pipeline.check_output(raw, ctx)
    output_stage.update(
        evaluated=True,
        action=out_res.action,
        reason_code=out_res.reason_code,
        latency_ms=round(out_res.latency_ms, 2) if out_res.latency_ms else None,
    )
    if out_res.blocked:
        output_stage["blocked"] = True
        return _resp("blocked_output")

    final = out_res.sanitised_text or raw
    output_stage.update(final_output=final, redacted=bool(out_res.sanitised_text))
    return _resp("answered")


@app.post("/ingest", response_model=IngestResponse)
async def ingest(file: UploadFile = File(...)):
    """Ingest an uploaded healthcare CSV into the active ChromaDB collection.

    Args:
        file: Multipart CSV upload following the schema expected by
        `ingest_csv`.

    Returns:
        The total collection count after ingestion and the uploaded filename.

    The upload is written to a temporary file because the existing ingestion
    helper works from filesystem paths. The temp file is removed even if
    ingestion fails.
    """
    collection = _get_collection()

    tmp_path = Path(f"/tmp/ingest_{uuid.uuid4().hex}.csv")
    try:
        content = await file.read()
        tmp_path.write_bytes(content)
        count = ingest_csv(tmp_path, collection)
    finally:
        tmp_path.unlink(missing_ok=True)

    return IngestResponse(chunk_count=count, doc_id=file.filename or "uploaded")


@app.get("/auth")
def auth(username: str = Depends(require_admin)):
    """Validate administrator credentials for the UI login screen."""
    return {"username": username}


@app.get("/rules")
def rules(_: str = Depends(require_admin)):
    """Return the currently active guardrail rules."""
    return get_rules()


@app.put("/rules")
def rules_update(rules: dict = Body(...), _: str = Depends(require_admin)):
    """Validate, persist, and hot-reload guardrail rules."""
    from .rules_loader import get_rules, save_rules

    def _validate(candidate_path: str) -> None:
        from guardrail_sdk import GuardrailConfig

        GuardrailConfig.from_yaml(candidate_path)

    try:
        save_rules(settings.RULES_FILE, rules, validator=_validate)
    except ImportError:
        save_rules(settings.RULES_FILE, rules)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=422, detail=f"Invalid guardrail config: {exc}"
        ) from exc

    _refresh_pipeline()
    return get_rules()


@app.post("/rules/reload")
def rules_reload(_: str = Depends(require_admin)):
    """Reload guardrail rules from disk and refresh the active pipeline."""
    from .rules_loader import reload_rules

    reload_rules(settings.RULES_FILE)
    _refresh_pipeline()
    return {"status": "reloaded"}


@app.get("/health", response_model=HealthResponse)
def health():
    """Return application health and dependency state.

    The response reports the backend name, Chroma collection, document count,
    rules file path, and whether the Guardrail SDK pipeline was initialised.
    """
    collection = _get_collection()
    return HealthResponse(
        status="healthy",
        backend=settings.BACKEND,
        chroma_collection=settings.CHROMA_COLLECTION,
        doc_count=collection.count(),
        rules_file=settings.RULES_FILE,
        guardrails_active=_pipeline is not None,
    )


