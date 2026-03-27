from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from anthropic import Anthropic

from config import get_settings
from curator import Article


# Updated language codes to match bot
LanguageCode = Literal["tr", "pl", "ar", "uk", "fr", "fa", "it", "ro", "bg", "es"]
Mode = Literal["native", "dutch"]


@dataclass
class UserPreferences:
    chat_id: int
    language: Optional[LanguageCode] = None  # For native language
    mode: Optional[Mode] = None              # None means not set yet
    dutch_level: Optional[str] = None        # A2, B1, B2
    country_of_origin: Optional[str] = None  # Not used in MVP


def _build_prompt(article: Article, prefs: UserPreferences) -> str:
    """Build the appropriate prompt based on user preferences"""
    
    # Map language codes to full names
    lang_names = {
        "tr": "Turkish",
        "pl": "Polish",
        "ar": "Arabic",
        "uk": "Ukrainian",
        "fr": "French",
        "fa": "Farsi/Persian",
        "it": "Italian",
        "ro": "Romanian",
        "bg": "Bulgarian",
        "es": "Spanish",
    }
    
    if prefs.mode == "native":
        # Safety check
        if not prefs.language:
            raise ValueError("Native mode selected but no language specified")
            
        lang_name = lang_names.get(prefs.language, prefs.language)
        
        return (
            "You are an assistant helping immigrants in the Netherlands understand news.\n"
            f"The user's native language is {lang_name}.\n"
            "Task: Summarize the Dutch news article below in the user's native language.\n"
            "Requirements:\n"
            "- Use simple, clear language.\n"
            "- 2-3 sentences.\n"
            "- Add short cultural/context notes in parentheses when useful.\n\n"
            f"ARTICLE TITLE: {article.title}\n"
            f"ARTICLE TEXT: {article.summary}\n"
        )
    
    elif prefs.mode == "dutch":
        # Safety checks
        if not prefs.dutch_level:
            raise ValueError("Dutch mode selected but no level specified")
        if not prefs.language:
            raise ValueError("Dutch mode selected but no native language for vocabulary")
            
        level = prefs.dutch_level
        native_lang = prefs.language
        lang_name = lang_names.get(native_lang, native_lang)
        
        return (
            "You are an assistant helping immigrants learn Dutch through news.\n"
            f"The user's native language is {lang_name}.\n"
            f"The user is learning Dutch at level {level}.\n\n"
            "Task: Create a Dutch learning resource from the article below.\n\n"
            "Your response MUST have this EXACT format:\n\n"
            "📰 [DUTCH SUMMARY]\n"
            "(Write 2-3 sentences in simplified Dutch at the specified level)\n\n"
            "💡 **Nieuwe woorden:**\n"
            "- **[Dutch word/phrase]** = [translation in user's native language]\n"
            "- **[Dutch word/phrase]** = [translation in user's native language]\n"
            "- **[Dutch word/phrase]** = [translation in user's native language]\n\n"
            "Requirements:\n"
            f"- Dutch summary: Use CEFR level {level} (simple sentences, common words)\n"
            "- Vocabulary: Pick 3-5 important words from the article\n"
            f"- Translations: Provide accurate translations in {lang_name}\n"
            "- Include a mix of individual words and short phrases\n"
            "- Make sure vocabulary words appear in the Dutch summary\n\n"
            f"ARTICLE TITLE: {article.title}\n"
            f"ARTICLE TEXT: {article.summary}\n"
        )
    
    else:
        raise ValueError(f"Invalid mode: {prefs.mode}")


def personalize_article(article: Article, prefs: UserPreferences) -> str:
    """Call the LLM to personalize/simplify an article."""
    
    # Validate preferences
    if not prefs.mode:
        raise ValueError("User has not selected a mode yet")
    
    settings = get_settings()

    # Initialize Anthropic client
    client = Anthropic(
        api_key=settings.anthropic_api_key,
        default_headers={
            "anthropic-version": "2023-06-01"
        }
    )

    prompt = _build_prompt(article, prefs)

    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=500,
        temperature=0.4,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )

    return response.content[0].text.strip()