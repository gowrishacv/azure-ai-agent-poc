from fastapi.testclient import TestClient

from app.main import app, settings
from app.models import AskResponse


class FakeAgent:
    def __init__(self, *_args, **_kwargs) -> None:
        pass

    async def answer(
        self,
        question: str,
        principals: tuple[str, ...] | None = None,
    ) -> AskResponse:
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
        assert response.json()["correlation_id"] == response.headers["X-Correlation-ID"]


def test_ask_rejects_short_question() -> None:
    app.state.agent_factory = FakeAgent
    with TestClient(app) as client:
        response = client.post("/ask", json={"question": "no"})
        assert response.status_code == 422


def test_chat_ui_and_public_configuration() -> None:
    app.state.agent_factory = FakeAgent
    with TestClient(app) as client:
        page = client.get("/")
        configuration = client.get("/config")

    assert page.status_code == 200
    assert "Azure AI Platform Assistant" in page.text
    assert configuration.status_code == 200
    assert configuration.json()["auth_enabled"] is False


def test_compiled_ui_assets_are_mounted() -> None:
    assets_route = next(route for route in app.routes if route.name == "assets")

    assert assets_route.path == "/assets"


def test_feedback_accepts_only_rating_and_correlation() -> None:
    app.state.agent_factory = FakeAgent
    with TestClient(app) as client:
        response = client.post(
            "/feedback",
            json={"correlation_id": "12345678-abcd", "rating": "up"},
        )

    assert response.status_code == 202
    assert response.json() == {"status": "accepted"}


def test_document_authorization_passes_public_principal(monkeypatch) -> None:
    captured: dict[str, tuple[str, ...] | None] = {}

    class CapturingAgent(FakeAgent):
        async def answer(
            self,
            question: str,
            principals: tuple[str, ...] | None = None,
        ) -> AskResponse:
            captured["principals"] = principals
            return await super().answer(question, principals)

    monkeypatch.setattr(settings, "enable_document_authorization", True)
    app.state.agent_factory = CapturingAgent
    with TestClient(app) as client:
        response = client.post("/ask", json={"question": "What is public?"})

    assert response.status_code == 200
    assert captured["principals"] == ("public",)
