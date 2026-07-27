from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from openai import NotFoundError

from scripts.index_documents import create_embedding_with_retry


def deployment_not_found_error() -> NotFoundError:
    request = httpx.Request("POST", "https://example.openai.azure.com/openai/embeddings")
    response = httpx.Response(404, request=request)
    return NotFoundError(
        "Deployment not found",
        response=response,
        body={"error": {"code": "DeploymentNotFound"}},
    )


def test_embedding_retries_when_deployment_is_propagating(monkeypatch) -> None:
    expected = SimpleNamespace(data=[SimpleNamespace(embedding=[0.1, 0.2])])
    create = Mock(side_effect=[deployment_not_found_error(), expected])
    client = SimpleNamespace(embeddings=SimpleNamespace(create=create))
    sleep = Mock()
    monkeypatch.setattr("scripts.index_documents.time.sleep", sleep)
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT_RETRY_ATTEMPTS", "2")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT_RETRY_DELAY_SECONDS", "0")

    result = create_embedding_with_retry(
        client,
        deployment="embedding",
        content="hello",
        dimensions=2,
    )

    assert result is expected
    assert create.call_count == 2
    sleep.assert_called_once_with(0.0)


def test_embedding_does_not_retry_unrelated_not_found(monkeypatch) -> None:
    request = httpx.Request("POST", "https://example.openai.azure.com/openai/embeddings")
    response = httpx.Response(404, request=request)
    error = NotFoundError(
        "Other resource not found",
        response=response,
        body={"error": {"code": "ResourceNotFound"}},
    )
    client = SimpleNamespace(
        embeddings=SimpleNamespace(create=Mock(side_effect=error))
    )
    sleep = Mock()
    monkeypatch.setattr("scripts.index_documents.time.sleep", sleep)

    with pytest.raises(NotFoundError) as caught:
        create_embedding_with_retry(
            client,
            deployment="embedding",
            content="hello",
            dimensions=2,
        )

    assert caught.value is error
    sleep.assert_not_called()
