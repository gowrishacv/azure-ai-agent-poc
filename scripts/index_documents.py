"""Create the vector index and load the small POC knowledge set using Entra ID."""

import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Any

from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)
from openai import NotFoundError, OpenAI

from app.openai_client import create_openai_client

_SAFE_PRINCIPAL = re.compile(r"^(public|(?:user|group|role):[A-Za-z0-9._:@-]{1,160})$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/sample-documents.json")
    return parser.parse_args()


def _is_deployment_not_found(error: NotFoundError) -> bool:
    body = error.body if isinstance(error.body, dict) else {}
    nested_error = body.get("error")
    nested_code = nested_error.get("code") if isinstance(nested_error, dict) else None
    return error.status_code == 404 and (
        body.get("code") == "DeploymentNotFound" or nested_code == "DeploymentNotFound"
    )


def create_embedding_with_retry(
    ai: OpenAI,
    *,
    deployment: str,
    content: str,
    dimensions: int,
) -> Any:
    attempts = int(os.getenv("AZURE_OPENAI_DEPLOYMENT_RETRY_ATTEMPTS", "20"))
    delay_seconds = float(os.getenv("AZURE_OPENAI_DEPLOYMENT_RETRY_DELAY_SECONDS", "15"))
    if attempts < 1:
        raise ValueError("AZURE_OPENAI_DEPLOYMENT_RETRY_ATTEMPTS must be at least 1")
    if delay_seconds < 0:
        raise ValueError("AZURE_OPENAI_DEPLOYMENT_RETRY_DELAY_SECONDS cannot be negative")

    for attempt in range(1, attempts + 1):
        try:
            return ai.embeddings.create(
                model=deployment,
                input=content,
                dimensions=dimensions,
            )
        except NotFoundError as error:
            if not _is_deployment_not_found(error) or attempt == attempts:
                raise
            print(
                f"Embedding deployment {deployment!r} is not ready "
                f"(attempt {attempt}/{attempts}); retrying in {delay_seconds:g}s."
            )
            time.sleep(delay_seconds)

    raise RuntimeError("Embedding deployment retry loop ended unexpectedly")


def validate_document_principals(document: dict[str, Any]) -> list[str]:
    principals = document.get("allowed_principals")
    if not isinstance(principals, list) or not principals:
        raise ValueError(
            f"Document {document.get('id', '<unknown>')!r} must define allowed_principals"
        )
    normalized = sorted(
        {
            principal
            for principal in principals
            if isinstance(principal, str) and _SAFE_PRINCIPAL.fullmatch(principal)
        }
    )
    if len(normalized) != len(principals):
        raise ValueError(
            f"Document {document.get('id', '<unknown>')!r} contains an invalid principal"
        )
    return normalized


def main() -> None:
    args = parse_args()
    credential = DefaultAzureCredential(
        managed_identity_client_id=os.getenv("AZURE_CLIENT_ID")
    )
    ai = create_openai_client(
        os.environ["AZURE_AI_ENDPOINT"],
        credential,
    )
    search_endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
    index_name = os.environ["AZURE_SEARCH_INDEX"]
    dimensions = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))
    index = SearchIndex(
        name=index_name,
        fields=[
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="title", type=SearchFieldDataType.String),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SimpleField(name="source", type=SearchFieldDataType.String, filterable=True),
            SearchField(
                name="allowed_principals",
                type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                filterable=True,
            ),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=dimensions,
                vector_search_profile_name="default",
            ),
        ],
        vector_search=VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="hnsw")],
            profiles=[
                VectorSearchProfile(
                    name="default", algorithm_configuration_name="hnsw"
                )
            ],
        ),
    )
    SearchIndexClient(search_endpoint, credential).create_or_update_index(index)

    source_documents = json.loads(Path(args.data).read_text(encoding="utf-8"))
    for document in source_documents:
        document["allowed_principals"] = validate_document_principals(document)
        result = create_embedding_with_retry(
            ai,
            deployment=os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT"],
            content=document["content"],
            dimensions=dimensions,
        )
        document["content_vector"] = result.data[0].embedding
    results = SearchClient(search_endpoint, index_name, credential).upload_documents(
        source_documents
    )
    failed = [result.key for result in results if not result.succeeded]
    if failed:
        raise RuntimeError(f"Indexing failed for: {failed}")
    print(f"Indexed {len(results)} documents into {index_name}.")


if __name__ == "__main__":
    main()
