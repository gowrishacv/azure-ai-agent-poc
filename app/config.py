from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    azure_client_id: str | None = None
    azure_ai_endpoint: str = "https://example.cognitiveservices.azure.com/"
    azure_ai_project_name: str = "local-project"
    azure_openai_chat_deployment: str = "chat"
    azure_openai_embedding_deployment: str = "embedding"
    azure_search_endpoint: str = "https://example.search.windows.net"
    azure_search_index: str = "aiagent-knowledge"
    azure_key_vault_uri: str | None = None
    embedding_dimensions: int = 1536
    allowed_cors_origins: str = ""
    require_auth: bool = False
    auth_tenant_id: str | None = None
    auth_audience: str | None = None
    max_question_chars: int = Field(default=2000, ge=100, le=10000)
    max_search_results: int = Field(default=5, ge=1, le=10)

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.allowed_cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
