from fastapi.testclient import TestClient

from app.main import app
from app.models import AskResponse


class FakeAgent:
    def __init__(self, *_args, **_kwargs) -> None:
        pass

    async def answer(self, question: str) -> AskResponse:
        return AskResponse(
            answer="Use managed identity [S1].",
            citations=[{"id": "S1", "title": "Managed identity policy", "source": "test"}],
            model="fake",
            grounded=True,
        )

    async def close(self) -> None:
        return None


def test_health() -> None:
    app.state.agent_factory = FakeAgent
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


def test_ask_uses_agent() -> None:
    app.state.agent_factory = FakeAgent
    with TestClient(app) as client:
        response = client.post("/ask", json={"question": "How should the app authenticate?"})
        assert response.status_code == 200
        assert response.json()["grounded"] is True


def test_ask_rejects_short_question() -> None:
    app.state.agent_factory = FakeAgent
    with TestClient(app) as client:
        response = client.post("/ask", json={"question": "no"})
        assert response.status_code == 422
