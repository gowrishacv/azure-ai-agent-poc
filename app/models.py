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

