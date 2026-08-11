import logging
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from azure.identity import DefaultAzureCredential
from azure.monitor.opentelemetry import configure_azure_monitor
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.agent import AgentService
from app.auth import Principal, authorize
from app.config import get_settings
from app.models import AskRequest, AskResponse, FeedbackRequest, PublicConfiguration

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()
_SAFE_CORRELATION_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")

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
    version="0.2.0",
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
        allow_headers=["Authorization", "Content-Type", "traceparent", "X-Correlation-ID"],
    )


async def require_authorization(request: Request) -> Principal:
    return await authorize(request, settings)


@app.middleware("http")
async def add_security_and_correlation_headers(request: Request, call_next):
    requested_id = request.headers.get("X-Correlation-ID", "")
    request.state.correlation_id = (
        requested_id if _SAFE_CORRELATION_ID.fullmatch(requested_id) else str(uuid4())
    )
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = request.state.correlation_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "connect-src 'self' https://login.microsoftonline.com; "
        "img-src 'self' data:; frame-src https://login.microsoftonline.com; "
        "base-uri 'none'; frame-ancestors 'none'"
    )
    return response


@app.get("/", include_in_schema=False)
async def chat_ui() -> FileResponse:
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/config", response_model=PublicConfiguration)
async def public_configuration() -> PublicConfiguration:
    return PublicConfiguration(
        auth_enabled=settings.require_auth,
        tenant_id=settings.auth_tenant_id if settings.require_auth else None,
        client_id=settings.ui_client_id if settings.require_auth else None,
        api_scope=settings.auth_scope if settings.require_auth else None,
        document_authorization_enabled=settings.enable_document_authorization,
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/ready")
async def ready() -> dict[str, str]:
    return {"status": "ready"}


@app.post(
    "/ask",
    response_model=AskResponse,
)
async def ask(
    payload: AskRequest,
    request: Request,
    principal: Annotated[Principal, Depends(require_authorization)],
) -> AskResponse:
    if len(payload.question) > settings.max_question_chars:
        raise HTTPException(status_code=422, detail="Question is too long")
    try:
        search_principals = (
            principal.search_principals if settings.enable_document_authorization else None
        )
        result = await request.app.state.agent.answer(payload.question, search_principals)
        return result.model_copy(update={"correlation_id": request.state.correlation_id})
    except Exception as exc:
        logger.exception("Agent request failed")
        raise HTTPException(status_code=503, detail="AI service temporarily unavailable") from exc


@app.post(
    "/feedback",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_authorization)],
)
async def feedback(payload: FeedbackRequest, response: Response) -> dict[str, str]:
    logger.info(
        "agent_feedback",
        extra={"correlation_id": payload.correlation_id, "rating": payload.rating},
    )
    response.headers["Cache-Control"] = "no-store"
    return {"status": "accepted"}
