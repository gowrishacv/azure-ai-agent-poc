"""Create the vector index and load the small POC knowledge set using Entra ID."""

import argparse
import json
import os
from pathlib import Path

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
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
from openai import AzureOpenAI


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/sample-documents.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    credential = DefaultAzureCredential(
        managed_identity_client_id=os.getenv("AZURE_CLIENT_ID")
    )
    ai = AzureOpenAI(
        azure_endpoint=os.environ["AZURE_AI_ENDPOINT"],
        azure_ad_token_provider=get_bearer_token_provider(
            credential, "https://cognitiveservices.azure.com/.default"
        ),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview"),
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
        result = ai.embeddings.create(
            model=os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT"],
            input=document["content"],
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
