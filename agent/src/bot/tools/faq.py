"""FAQ related tools for Rezolve Hotels, New York."""

import os
from langchain_core.tools import tool
from loguru import logger
from .base import get_weaviate_client, openai_client, PRODUCT_CLASS, extract_clean_answer


@tool
def get_faq_answer(query: str):
    """
    Fetch the FAQ answer for Rezolve Hotel, New York.

    This tool retrieves curated FAQ content from the Rezolve_FAQ knowledge base, which is
    populated from `faq.json`. Answers are written in the Rezolve concierge style and
    should normally be returned directly to the guest without re-writing.

    Use this tool for queries about:
    - Hotel policies (check-in/out, pets, parking, spa, etc.)
    - Experiences and services at The Pierre
    - Nearby attractions and how to reach the hotel
    
    Args:
        query (str): The guest's FAQ query in natural language.
                    Examples: "check-in time", "pet policy", "parking available", 
                    "cancellation policy"
    
    Returns:
        str: The best matching FAQ answer from the Rezolve_FAQ collection, lightly cleaned
             for clarity while preserving Rezolve / The Pierre branding and tone.
    """

    logger.info(f"Starting FAQ search for query: {query}")
    
    try:
        client = get_weaviate_client()
        if client is None:
            logger.error("Weaviate client could not be created")
            return {"error": "Weaviate client could not be created."}

        faq_collection = client.collections.get(PRODUCT_CLASS)
        logger.info(f"Retrieved FAQ collection: {PRODUCT_CLASS}")

        # Step 1: BM25 search
        logger.info("Starting BM25 search")
        response = faq_collection.query.bm25(
            query=query,
            limit=1,
        )
        
        logger.info(f"BM25 search returned {len(response.objects)} results")
        
        if response.objects:
            obj = response.objects[0]
            logger.info("BM25 found result, extracting answer")
            if obj.properties:
                raw_answer = obj.properties.get("answer")
                logger.info(f"Raw BM25 answer: {raw_answer}")
                cleaned_answer = extract_clean_answer(raw_answer)
                logger.info(f"Cleaned BM25 answer: {cleaned_answer}")
                return cleaned_answer
            else:
                logger.warning("BM25 result has no properties")

        # Step 2: Fallback to similarity search
        logger.info("BM25 returned no results. Falling back to similarity search")

        embedding = openai_client.embeddings.create(
            model=os.getenv("AZURE_EMBEDDING_MODEL"),
            input=query
        ).data[0].embedding
        
        logger.info("Generated embedding for vector search")

        vector_response = faq_collection.query.near_vector(
            embedding,
            limit=1,
        )
        
        logger.info(f"Vector search returned {len(vector_response.objects)} results")

        if vector_response.objects:
            obj = vector_response.objects[0]
            logger.info("Vector search found result, extracting answer")
            if obj.properties:
                raw_answer = obj.properties.get("answer")
                logger.info(f"Raw vector answer: {raw_answer}")
                cleaned_answer = extract_clean_answer(raw_answer)
                logger.info(f"Cleaned vector answer: {cleaned_answer}")
                return cleaned_answer
            else:
                logger.warning("Vector search result has no properties")

        logger.info("No results found in either BM25 or vector search")
        return None

    except Exception as e:
        logger.error(f"Error in FAQ retrieval: {e}")
        return {"error": str(e)}
    finally:
        try:
            if 'client' in locals():
                client.close()
                logger.info("Weaviate client closed")
        except Exception as e:
            logger.warning(f"Error closing client: {e}")
