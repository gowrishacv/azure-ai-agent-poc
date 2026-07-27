from app.openai_client import AZURE_AI_SCOPE, openai_v1_base_url


def test_openai_v1_base_url_normalizes_trailing_slash() -> None:
    endpoint = "https://example.openai.azure.com/"

    assert (
        openai_v1_base_url(endpoint)
        == "https://example.openai.azure.com/openai/v1/"
    )


def test_openai_v1_uses_foundry_token_scope() -> None:
    assert AZURE_AI_SCOPE == "https://ai.azure.com/.default"
