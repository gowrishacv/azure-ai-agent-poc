import asyncio

from azure.core.credentials import TokenCredential
from azure.identity import get_bearer_token_provider
from openai import AsyncOpenAI, OpenAI

AZURE_AI_SCOPE = "https://ai.azure.com/.default"


def openai_v1_base_url(endpoint: str) -> str:
    return f"{endpoint.rstrip('/')}/openai/v1/"


def create_openai_client(endpoint: str, credential: TokenCredential) -> OpenAI:
    return OpenAI(
        base_url=openai_v1_base_url(endpoint),
        api_key=get_bearer_token_provider(credential, AZURE_AI_SCOPE),
    )


def create_async_openai_client(
    endpoint: str, credential: TokenCredential
) -> AsyncOpenAI:
    sync_token_provider = get_bearer_token_provider(credential, AZURE_AI_SCOPE)

    async def async_token_provider() -> str:
        return await asyncio.to_thread(sync_token_provider)

    return AsyncOpenAI(
        base_url=openai_v1_base_url(endpoint),
        api_key=async_token_provider,
    )
