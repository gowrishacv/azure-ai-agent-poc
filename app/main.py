import logging
from contextlib import asynccontextmanager

from azure.identity import DefaultAzureCredential
from azure.monitor.opentelemetry import configure_azure_monitor
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app.agent import AgentService
from app.auth import authorize
from app.config import get_settings
from app.models import AskRequest, AskResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()

try:
    configure_azure_monitor()
except (RuntimeError, ValueError):
    logger.info("Application Insights is not configured; using console telemetry.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    credential = DefaultAzureCredential(managed_identity_client_id=settings.azure_client_id)
    agent_factory = getattr(app.state, "agent_factory", AgentService)
    app.state.agent = agent_factory(settings, credential)
    yield
    await app.state.agent.close()
    credential.close()


app = FastAPI(
    title="Azure AI Agent POC",
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan,
)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["POST", "GET"],
        allow_headers=["Authorization", "Content-Type", "traceparent"],
    )


async def require_authorization(request: Request) -> None:
    await authorize(request, settings)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/ready")
async def ready() -> dict[str, str]:
    return {"status": "ready"}


@app.post(
    "/ask",
    response_model=AskResponse,
    dependencies=[Depends(require_authorization)],
)
async def ask(payload: AskRequest, request: Request) -> AskResponse:
    if len(payload.question) > settings.max_question_chars:
        raise HTTPException(status_code=422, detail="Question is too long")
    try:
        return await request.app.state.agent.answer(payload.question)
    except Exception as exc:
        logger.exception("Agent request failed")
        raise HTTPException(status_code=503, detail="AI service temporarily unavailable") from exc
