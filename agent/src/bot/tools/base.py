"""Base configuration and shared utilities for tools."""

import os
import datetime
from loguru import logger
from dotenv import load_dotenv
from openai import AzureOpenAI
import weaviate

load_dotenv()

# Current datetime in New York timezone
Current_datetime_NY = {
    datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=-4))
    ).strftime("%A, %m/%d/%Y")
}

openai_client = AzureOpenAI(
    api_key=os.getenv("AZURE_EMBEDDING_API_KEY"),
    azure_endpoint=os.getenv("AZURE_EMBEDDING_ENDPOINT"),
    api_version=os.getenv("AZURE_EMBEDDING_API_VERSION"),
)

PRODUCT_CLASS = "REZOLVE_FAQ"
OFFER_CLASS = "OfferV1"


def get_weaviate_client():
    """Get a Weaviate client instance (v4)."""
    try:
        client = weaviate.connect_to_weaviate_cloud(
            cluster_url=os.getenv("WEAVIATE_URL"),
            auth_credentials=weaviate.auth.AuthApiKey(
                os.getenv("WEAVIATE_API_KEY")),
        )
        return client
    except Exception as e:
        logger.error(f"Error creating Weaviate client: {e}")
        return None

def extract_clean_answer(content: str) -> str:
    """Extract only the direct answer, removing any reasoning or meta-commentary."""
    logger.info(f"Starting to clean content: {content}")
    
    try:
        if content:
            import re
            fallback = content
            
            fallback = re.sub(r'\blbs?\b', 'pounds', fallback, flags=re.IGNORECASE)
            fallback = re.sub(r'\bsqft\b', 'square feet', fallback, flags=re.IGNORECASE)
            fallback = re.sub(r'\$(\d+)', r'\1 dollars', fallback)
            
            fallback = re.sub(r'(\d{1,2}):00\s*(AM|PM)', r'\1 \2', fallback, flags=re.IGNORECASE)
            
            lines = fallback.split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith(('#', '-', '*')):
                    logger.info(f"Using cleaned response: {line}")
                    return line
        
        return content if content else "I don't have information about that."
        
    except Exception as e:
        logger.error(f"Error cleaning response - {type(e).__name__}: {str(e)}")
        logger.info("Falling back to original content")
        return content if content else "I don't have information about that."