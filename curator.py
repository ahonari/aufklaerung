from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, List

import feedparser

from config import get_settings


@dataclass
class Article:
    title: str
    summary: str
    link: str
    published: datetime | None
    source: str


def _entry_published(entry) -> datetime | None:
    published_parsed = getattr(entry, "published_parsed", None)
    if published_parsed is None:
        return None
    return datetime(*published_parsed[:6], tzinfo=timezone.utc)


def _contains_keyword(text: str, keywords: Iterable[str]) -> bool:
    lower = text.lower()
    return any(kw.lower() in lower for kw in keywords)


def fetch_relevant_articles(limit: int = 5) -> List[Article]:
    """Fetch and filter articles from configured RSS feeds."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=1)

    collected: List[Article] = []

    for feed_url in settings.rss_feeds:
        parsed = feedparser.parse(feed_url)
        source_title = parsed.feed.get("title", feed_url) if hasattr(parsed, "feed") else feed_url

        for entry in parsed.entries:
            published = _entry_published(entry)
            if published is not None and published < cutoff:
                continue

            title = getattr(entry, "title", "")
            summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
            link = getattr(entry, "link", "")
            text_for_filter = f"{title}\n{summary}"

            if not _contains_keyword(text_for_filter, settings.keywords):
                continue

            collected.append(
                Article(
                    title=title,
                    summary=summary,
                    link=link,
                    published=published,
                    source=source_title,
                )
            )

    collected.sort(
        key=lambda a: a.published or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    return collected[:limit]

