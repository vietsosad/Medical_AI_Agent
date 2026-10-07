from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.agents.deepagent_runtime import (
    configure_deepagent_runtime,
    reset_deepagent_runtime,
)
from src.agents.simple_agent_runtime import (
    configure_simple_agent_runtime,
    reset_simple_agent_runtime,
)
from src.api.routes import router
from src.config import get_settings
from src.services.db import dispose_db_engine, init_db_schema
from src.services.llm_provider import get_resilient_llm
from src.services.log_redaction import install_uvicorn_log_redaction

install_uvicorn_log_redaction()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    print(f"Starting {settings.app_name} in {settings.app_env} mode")
    try:
        await init_db_schema()
    except Exception as e:
        print(f"⚠️ [Lifespan Warning] DB Init error or waiting for PostgreSQL container: {str(e)}")
    # Construct configured clients before requests so the first clinical turn
    # does not pay synchronous SDK import/setup time between SSE heartbeats.
    if settings.openai_api_key or settings.groq_api_key or settings.google_api_key:
        get_resilient_llm(tier="large")
        if settings.intent_llm_fallback_enabled:
            get_resilient_llm(tier="small")

    try:
        await configure_deepagent_runtime()
        print("[DeepAgent] Tool-gated supervisor runtime is ready.")
        if settings.simple_agent_enabled:
            await configure_simple_agent_runtime()
            print("[SimpleAgent] Pilot runtime is ready (/api/v1/simple-triage/*).")
        yield
    finally:
        if settings.simple_agent_enabled:
            await reset_simple_agent_runtime()
        await reset_deepagent_runtime()
        print("Shutting down and disposing DB connection pool...")
        try:
            await dispose_db_engine()
        except Exception as e:
            print(f"[Shutdown Warning] Error during DB dispose: {str(e)}")



app = FastAPI(
    title="AI20K Agent",
    description="MedTriage AI built with a tool-gated DeepAgent supervisor",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.app_env}
