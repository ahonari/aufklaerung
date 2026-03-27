import os
from dataclasses import dataclass
from typing import List, Optional

from dotenv import load_dotenv


load_dotenv()


@dataclass
class Settings:
    # Telegram
    telegram_bot_token: str
    
    # Anthropic
    anthropic_api_key: Optional[str]
    anthropic_model: str
    
    # RSS and news settings — prioritized domestic feeds
    rss_feeds: List[str]


def get_settings() -> Settings:
    # Telegram
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    
    # Anthropic
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    
    # RSS feeds — domestic-focused first
    rss_feeds = [
        "https://feeds.nos.nl/nosnieuwsbinnenland",      # NL domestic news (best)
        "https://www.nu.nl/rss/binnenland",              # NL domestic (if available)
        "https://feeds.nos.nl/nosnieuwsalgemeen",        # General (fallback)
    ]
    
    return Settings(
        telegram_bot_token=telegram_bot_token,
        anthropic_api_key=anthropic_api_key,
        anthropic_model=anthropic_model,
        rss_feeds=rss_feeds,
    )