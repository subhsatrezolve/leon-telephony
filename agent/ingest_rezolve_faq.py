import os
from typing import List, Dict

from dotenv import load_dotenv
from loguru import logger
from openai import AzureOpenAI
import weaviate


load_dotenv()


AZURE_EMBEDDING_API_KEY = os.getenv("AZURE_EMBEDDING_API_KEY")
AZURE_EMBEDDING_ENDPOINT = os.getenv("AZURE_EMBEDDING_ENDPOINT")
AZURE_EMBEDDING_API_VERSION = os.getenv("AZURE_EMBEDDING_API_VERSION")
AZURE_EMBEDDING_MODEL = os.getenv("AZURE_EMBEDDING_MODEL")

WEAVIATE_URL = os.getenv("WEAVIATE_URL")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")

COLLECTION_NAME = "REZOLVE_FAQ"


def get_azure_client() -> AzureOpenAI:
    if not (AZURE_EMBEDDING_API_KEY and AZURE_EMBEDDING_ENDPOINT and AZURE_EMBEDDING_API_VERSION):
        raise RuntimeError("Azure OpenAI environment variables are not fully configured.")

    return AzureOpenAI(
        api_key=AZURE_EMBEDDING_API_KEY,
        azure_endpoint=AZURE_EMBEDDING_ENDPOINT,
        api_version=AZURE_EMBEDDING_API_VERSION,
    )


def get_weaviate_client() -> weaviate.WeaviateClient:
    if not (WEAVIATE_URL and WEAVIATE_API_KEY):
        raise RuntimeError("WEAVIATE_URL or WEAVIATE_API_KEY is not configured.")

    return weaviate.connect_to_weaviate_cloud(
        cluster_url=WEAVIATE_URL,
        auth_credentials=weaviate.auth.AuthApiKey(WEAVIATE_API_KEY),
    )


def ensure_collection(client: weaviate.WeaviateClient) -> None:
    existing = client.collections.list_all()
    if COLLECTION_NAME in existing:
        logger.info(f"Collection {COLLECTION_NAME} already exists.")
        return

    logger.info(f"Creating collection {COLLECTION_NAME}.")
    client.collections.create(name=COLLECTION_NAME)


def load_faqs() -> List[Dict[str, str]]:
    """
    Load REZOLVE FAQ data from the bundled JSON file.

    Expects `agent/src/bot/data/faq.json` with structure:
      { "faqs": [ { "question": "...", "answer": "..." }, ... ] }
    """
    import json
    base_dir = os.path.dirname(__file__)
    faq_path = os.path.join(base_dir, "src", "bot", "data", "faq.json")

    with open(faq_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    faqs = data.get("faqs", [])
    return [
        {"question": item.get("question", ""), "answer": item.get("answer", "")}
        for item in faqs
    ]


def embed_text(client: AzureOpenAI, text: str) -> List[float]:
    if not AZURE_EMBEDDING_MODEL:
        raise RuntimeError("AZURE_EMBEDDING_MODEL is not configured.")

    resp = client.embeddings.create(
        model=AZURE_EMBEDDING_MODEL,
        input=text,
    )
    return resp.data[0].embedding


def ingest_faqs() -> None:
    azure_client = get_azure_client()
    weaviate_client = get_weaviate_client()

    try:
        ensure_collection(weaviate_client)
        collection = weaviate_client.collections.get(COLLECTION_NAME)

        faqs = load_faqs()
        logger.info(f"Ingesting {len(faqs)} FAQ items into {COLLECTION_NAME}.")

        with collection.batch.dynamic() as batch:
            for item in faqs:
                question = item.get("question", "").strip()
                answer = item.get("answer", "").strip()

                if not question or not answer:
                    logger.warning("Skipping FAQ item with missing question or answer.")
                    continue

                text_for_embedding = f"Q: {question}\nA: {answer}"

                try:
                    vector = embed_text(azure_client, text_for_embedding)
                except Exception as exc:
                    logger.error(f"Embedding failed for question '{question}': {exc}")
                    continue

                batch.add_object(
                    properties={
                        "question": question,
                        "answer": answer,
                    },
                    vector=vector,
                )

        logger.info("Finished ingesting FAQ items.")
    finally:
        try:
            weaviate_client.close()
        except Exception as exc:
            logger.warning(f"Error closing Weaviate client: {exc}")


if __name__ == "__main__":
    ingest_faqs()

