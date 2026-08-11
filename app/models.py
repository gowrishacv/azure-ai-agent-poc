from typing import Literal

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    conversation_id: str | None = Field(default=None, max_length=100)


class Citation(BaseModel):
    id: str
    title: str
    source: str | None = None


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]
    model: str
    grounded: bool
    correlation_id: str | None = None


class FeedbackRequest(BaseModel):
    correlation_id: str = Field(pattern=r"^[A-Za-z0-9-]{8,64}$")
    rating: Literal["up", "down"]


class PublicConfiguration(BaseModel):
    auth_enabled: bool
    tenant_id: str | None
    client_id: str | None
    api_scope: str | None
    document_authorization_enabled: bool
