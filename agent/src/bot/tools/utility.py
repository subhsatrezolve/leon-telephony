"""Utility and helper tools for the ElevenLabs HTTP API."""

import os
import textwrap
from typing import List, Dict

import requests
from langchain_core.tools import tool
from loguru import logger


@tool
def web_search(query: str) -> str:
    """
    Search the web for information when FAQ data is uncertain, using SerpAPI
    with Google Search results as the backend.

    Configuration:
    - Requires environment variable:
        SERPAPI_API_KEY : SerpAPI key for Google Search
    """
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        logger.error("SERPAPI_API_KEY is not set")
        return (
            "I tried to look this up online, but my live web search service "
            "is not configured at the moment."
        )

    try:
        params = {
            "engine": "google",
            "q": query,
            "api_key": api_key,
        }
        resp = requests.get(
            "https://serpapi.com/search.json",
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        organic_results = data.get("organic_results") or []
        if not organic_results:
            logger.warning(f"SerpAPI returned no organic_results for query: {query!r}")
            return (
                "I tried searching online but could not find clear results for that query."
            )

        top_results = organic_results[:3]
        snippets = []
        for item in top_results:
            title = str(item.get("title") or "").strip()
            snippet = str(item.get("snippet") or "").strip()
            link = str(item.get("link") or "").strip()

            parts = []
            if title:
                parts.append(title)
            if snippet:
                parts.append(snippet)
            if link:
                parts.append(f"More details: {link}")

            if parts:
                snippets.append(" - " + " ".join(parts))

        if not snippets:
            logger.warning(f"SerpAPI results had no usable snippets for query: {query!r}")
            return (
                "I searched the web but could not extract a clear answer from the results."
            )

        joined = "\n".join(snippets)
        return (
            "Here’s what I found from a quick Google search powered by SerpAPI:\n"
            f"{joined}"
        )
    except Exception as exc:
        logger.error(f"SerpAPI web search failed for query {query!r}: {exc}")
        return (
            "I tried to look this up online, but there was an error reaching "
            "my live web search service."
        )

@tool
def get_travel_places(query: str) -> str:
    """
    Retrieve nearby places (restaurants, attractions, venues) using Google Places.

    This tool is ideal when the guest asks about specific nearby places,
    such as restaurants, cafes, museums, or attractions.

    Implementation details:
    - Uses the Google Places Text Search API.
    - Requires environment variable:
        GOOGLE_PLACES_API_KEY : Google Maps/Places API key
    - Optionally, you can include location keywords in the query itself
      (e.g. "best pizza near The Pierre New York").
    """
    api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    if not api_key:
        logger.error("GOOGLE_PLACES_API_KEY is not set")
        return (
            "I’d love to recommend nearby places, but I’m currently unable to reach my live places service. "
            "Please check with the concierge team for tailored local suggestions."
        )

    try:
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": (
                "places.displayName,places.formattedAddress,"
                "places.rating,places.id,places.googleMapsUri"
            ),
        }
        body: Dict = {
            "textQuery": query,
        }

        resp = requests.post(
            "https://places.googleapis.com/v1/places:searchText",
            headers=headers,
            json=body,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        error = data.get("error")
        if error:
            logger.error(
                f"Google Places API error for query {query!r}: "
                f"code={error.get('code')} message={error.get('message')}"
            )
            return (
                "I tried checking nearby places, but my live places service reported an error. "
                "Please check with the concierge team for tailored local suggestions."
            )

        places: List[Dict] = data.get("places", []) or []

        if not places:
            logger.info(f"No Google Places results for query: {query!r}")
            return (
                "I checked nearby places but didn’t find anything matching that request. "
                "If you’d like, I can suggest some popular spots around the hotel instead."
            )

        top_results = places[:3]
        entries = []
        for place in top_results:
            display_name = place.get("displayName") or {}
            name = str(display_name.get("text", "")).strip()
            address = str(place.get("formattedAddress", "")).strip()
            rating = place.get("rating")
            rating_text = f" (rating {rating}/5)" if rating is not None else ""

            maps_link = str(place.get("googleMapsUri", "")).strip()

            addr_short = textwrap.shorten(address, width=80, placeholder="...")
            if maps_link:
                entry = f"{name}{rating_text}, at {addr_short}. More details at {maps_link}."
            else:
                entry = f"{name}{rating_text}, at {addr_short}."
            entries.append(entry)

        joined = " ".join(entries)
        return (
            f"Here are a few nearby places that match what you asked for: {joined} "
            f"If any of these sound appealing, I can help you choose one."
        )

    except Exception as e:
        logger.error(f"Error while calling Google Places for query {query!r}: {e}")
        return (
            "I’m having trouble reaching my live places service at the moment. "
            "Let me connect you with the hotel team so they can suggest nearby options."
        )
