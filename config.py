import os
from dataclasses import dataclass
from typing import List, Optional

from dotenv import load_dotenv


load_dotenv()


@dataclass
class Settings:
    # Telegram
    telegram_bot_token: str
    
    # OpenAI (optional now)
    openai_api_key: Optional[str]
    openai_model: str
    
    # Anthropic (added)
    anthropic_api_key: Optional[str]
    anthropic_model: str
    
    # RSS and news settings
    rss_feeds: List[str]
    keywords: List[str]


def get_settings() -> Settings:
    # Telegram
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    
    # OpenAI (optional)
    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    
    # Anthropic - using your discovered model
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")  # Default to your working model
    
    # RSS feeds
    rss_feeds = [
        "https://feeds.nos.nl/nosnieuwsalgemeen",
        "https://www.nu.nl/rss/Algemeen",
    ]
    
    # Keywords for filtering immigrant-related news
    keywords = [
        "immigrant",
        "buitenlander",
        "integratie",
        "statushouder",
        "vluchteling",
        "asielzoeker",
    ]
    
    return Settings(
        telegram_bot_token=telegram_bot_token,
        openai_api_key=openai_api_key,
        openai_model=openai_model,
        anthropic_api_key=anthropic_api_key,
        anthropic_model=anthropic_model,
        rss_feeds=rss_feeds,
        keywords=keywords,
    )