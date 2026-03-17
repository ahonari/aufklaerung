from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from anthropic import Anthropic  # Changed from openai

from config import get_settings
from curator import Article


LanguageCode = Literal["tr", "ar", "fa"]
Mode = Literal["native", "dutch_learning"]


@dataclass
class UserPreferences:
    chat_id: int
    language: LanguageCode
    mode: Mode = "native"
    dutch_level: str = "B1"
    country_of_origin: str | None = None


def _build_prompt(article: Article, prefs: UserPreferences) -> str:
    if prefs.mode == "native":
        return (
            "You are an assistant helping immigrants in the Netherlands understand news.\n"
            f"User native language code: {prefs.language}.\n"
            "Task: Summarize the Dutch news article below in the user's native language.\n"
            "Requirements:\n"
            "- Use simple, clear language.\n"
            "- 2-3 sentences.\n"
            "- Add short cultural/context notes in parentheses when useful.\n\n"
            f"ARTICLE TITLE: {article.title}\n"
            f"ARTICLE TEXT: {article.summary}\n"
        )

    level = prefs.dutch_level or "B1"
    return (
        "You are an assistant helping Dutch learners (immigrants) understand news.\n"
        f"The user is learning Dutch at level {level}.\n"
        "Task: Rewrite the Dutch news article below in simplified Dutch at the given level.\n"
        "Requirements:\n"
        "- 2-3 sentences.\n"
        "- Use clear, short sentences.\n"
        "- Avoid complex idioms.\n"
        "- Add short cultural/context notes in parentheses when helpful.\n\n"
        f"ARTICLE TITLE: {article.title}\n"
        f"ARTICLE TEXT: {article.summary}\n"
    )


def personalize_article(article: Article, prefs: UserPreferences) -> str:
    """Call the LLM to personalize/simplify an article."""
    settings = get_settings()

    # Initialize Anthropic client with correct API version
    client = Anthropic(
        api_key=settings.anthropic_api_key,  # Make sure this is in your settings
        default_headers={
            "anthropic-version": "2023-06-01"  # Critical for your account!
        }
    )

    prompt = _build_prompt(article, prefs)

    # Using Claude Sonnet 4.6 (latest model from your list)
    response = client.messages.create(
        model="claude-sonnet-4-6",  # Your specific available model
        max_tokens=350,
        temperature=0.4,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )

    return response.content[0].text.strip()