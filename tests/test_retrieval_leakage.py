import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.agent import AgentService
from app.config import Settings

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "sharepoint"

EXPECTED_SOURCE_IDS = {
    "anonymous": {"sp-policy-public-001"},
    "public-user": {"sp-policy-public-001"},
    "authorized-user": {"sp-policy-public-001", "sp-runbook-incident-003"},
    "authorized-group-member": {
        "sp-policy-public-001",
        "sp-policy-network-002",
    },
    "authorized-role-holder": {
        "sp-policy-public-001",
        "sp-policy-network-002",
    },
    "disallowed-user": {"sp-policy-public-001"},
    "group-overage-user": {"sp-policy-public-001"},
}


class AsyncItems:
    def __init__(self, items: list[dict[str, object]]) -> None:
        self.items = items

    def __aiter__(self):
        return self._iterate()

    async def _iterate(self):
        for item in self.items:
            yield item


class FakeSearchClient:
    def __init__(self, items: list[dict[str, object]]) -> None:
        self.items = items
        self.last_filter: str | None = None

    async def search(self, **kwargs):
        self.last_filter = kwargs["filter"]
        # Deliberately return every active document. The application must still
        # prevent unauthorized chunks from reaching the model prompt.
        return AsyncItems(self.items)


class FakeEmbeddings:
    async def create(self, **_kwargs):
        return SimpleNamespace(data=[SimpleNamespace(embedding=[0.0, 0.0])])


class FakeChatCompletions:
    def __init__(self) -> None:
        self.messages: list[dict[str, str]] = []

    async def create(self, **kwargs):
        self.messages = kwargs["messages"]
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Supported [S1]"))]
        )


def _load_documents() -> list[dict[str, object]]:
    scenarios = json.loads(
        (FIXTURE_DIR / "scenarios.json").read_text(encoding="utf-8")
    )
    return [
        scenario["document"]
        for scenario in scenarios
        if not scenario["document"]["is_deleted"]
    ]


def _load_personas() -> list[dict[str, object]]:
    return json.loads((FIXTURE_DIR / "personas.json").read_text(encoding="utf-8"))


def _service() -> tuple[AgentService, FakeChatCompletions]:
    service = AgentService.__new__(AgentService)
    service.settings = Settings(embedding_dimensions=2, max_search_results=5)
    chat = FakeChatCompletions()
    service.openai = SimpleNamespace(
        embeddings=FakeEmbeddings(),
        chat=SimpleNamespace(completions=chat),
    )
    service.search = FakeSearchClient(_load_documents())
    return service, chat


@pytest.mark.asyncio
@pytest.mark.parametrize("persona", _load_personas(), ids=lambda item: item["persona"])
async def test_persona_matrix_returns_only_authorized_source_ids(persona) -> None:
    service, _chat = _service()

    documents = await service._retrieve(
        "synthetic question",
        tuple(persona["expected_principals"]),
    )

    assert {document.id for document in documents} == EXPECTED_SOURCE_IDS[
        persona["persona"]
    ]


@pytest.mark.asyncio
async def test_unauthorized_chunks_never_reach_prompt_builder() -> None:
    service, chat = _service()

    response = await service.answer(
        "What is public?",
        ("public", "user:synthetic-disallowed-user"),
    )

    prompt = chat.messages[1]["content"]
    assert "The platform support window" in prompt
    assert "revised standard requires approved private connectivity" not in prompt
    assert "restricted to one synthetic test identity" not in prompt
    assert [citation.title for citation in response.citations] == [
        "Platform support hours"
    ]
