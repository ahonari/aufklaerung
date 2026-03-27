from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import feedparser

from config import get_settings


@dataclass
class Article:
    title: str
    summary: str
    link: str
    published: datetime | None
    source: str
    category: Optional[str] = None


CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    '🪪 Integration': [  # Priority 1 - most relevant to immigrants
        'inburgering', 'inburgeren', 'inburgeringscursus', 'inburgeringsexamen',
        'statushouder', 'asiel', 'asielzoeker', 'vluchteling', 'immigrant',
        'migrant', 'integratie', 'naturalisatie', 'verblijfsvergunning', 'ind',
        'taal', 'taalcursus', 'nt2', 'nederlands leren', 'inburgeringsplicht'
    ],
    '🏠 Housing': [  # Priority 2
        'woning', 'woningmarkt', 'huur', 'huurwoning', 'huurprijs', 'huurverhoging',
        'koop', 'koopwoning', 'hypotheek', 'sociale huur', 'woningcorporatie',
        'huisvesting', 'woningnood', 'starterslening', 'huurtoeslag'
    ],
    '💼 Work & Economy': [
        'werk', 'baan', 'werkloosheid', 'werkloos', 'vacature', 'solliciteren',
        'salaris', 'loon', 'minimumloon', 'cao', 'contract', 'ontslag',
        'zzp', 'freelance', 'ondernemer', 'economie', 'inflatie', 'belasting',
        'arbeidsmarkt', 'werknemer', 'werkgever'
    ],
    '🏛️ Politics': [
        'kamer', 'wet', 'gemeenteraad', 'verkiezingen', 'beleid', 'minister',
        'kabinet', 'partij', 'stemmen', 'politiek', 'tweede kamer'
    ],
    '📚 Education': [
        'school', 'basisschool', 'middelbare school', 'vmbo', 'havo', 'vwo',
        'mbo', 'hbo', 'universiteit', 'student', 'studie', 'diploma',
        'opleiding', 'cursus', 'volwasseneneducatie', 'nt2'
    ],
    '🏥 Health': [
        'zorg', 'huisarts', 'ziekenhuis', 'ggd', 'zorgverzekering', 
        'zorgverzekeraar', 'eigen risico', 'apotheek', 'medicijn'
    ],
    '🌍 Culture': [
        'feest', 'traditie', 'vrijwilliger', 'sport', 'evenement',
        'koningsdag', 'sinterklaas', 'cultuur', 'festival', 'museum'
    ],
    '🚆 Transport': [  # Priority lowest
        'ov', 'ns', 'trein', 'bus', 'tram', 'metro', 'ov-chipkaart',
        'rijbewijs', 'cbr', 'auto', 'verkeer', 'spoor', 'wegwerkzaamheden'
    ],
}


def _get_category(text: str) -> Optional[str]:
    """Determine article category based on keyword matching."""
    lower_text = text.lower()
    
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in lower_text:
                return category
    
    return None


def _entry_published(entry) -> datetime | None:
    published_parsed = getattr(entry, "published_parsed", None)
    if published_parsed is None:
        return None
    return datetime(*published_parsed[:6], tzinfo=timezone.utc)


def _is_relevant_to_netherlands(text: str) -> bool:
    """Filter out purely international news."""
    lower_text = text.lower()
    
    dutch_keywords = [
        # Places & Government
        'nederland', 'nederlands', 'amsterdam', 'rotterdam', 'den haag', 
        'utrecht', 'eindhoven', 'groningen', 'maastricht', 'tilburg',
        'gemeente', 'provincie', 'minister', 'kamer', 'parlement', 
        'wet', 'regel', 'beleid', 'burgemeester', 'wethouder',
        
        # Integration
        'inburgering', 'inburgeren', 'inburgeringscursus', 'inburgeringsexamen',
        'statushouder', 'asiel', 'asielzoeker', 'vluchteling', 'immigrant', 
        'migrant', 'integratie', 'naturalisatie', 'paspoort', 'verblijfsvergunning',
        'verblijfsdocument', 'vreemdeling', 'ind', 'immigratie',
        'taal', 'taalcursus', 'nt2', 'nederlands leren',
        
        # Housing
        'woning', 'woningmarkt', 'huur', 'huurwoning', 'huurprijs', 'huurverhoging',
        'koop', 'koopwoning', 'hypotheek', 'sociale huur', 'woningcorporatie',
        'huisvesting', 'woningnood', 'starterslening', 'huurtoeslag',
        
        # Work & Economy
        'werk', 'baan', 'werkloosheid', 'werkloos', 'vacature', 'solliciteren',
        'salaris', 'loon', 'minimumloon', 'cao', 'contract', 'ontslag',
        'zzp', 'freelance', 'ondernemer', 'economie', 'inflatie',
        'belasting', 'toeslag', 'zorgtoeslag', 'huurtoeslag', 'kinderopvangtoeslag',
        
        # Education
        'school', 'basisschool', 'middelbare school', 'vmbo', 'havo', 'vwo',
        'mbo', 'hbo', 'universiteit', 'student', 'studie', 'diploma', 
        'opleiding', 'cursus', 'volwasseneneducatie', 'rocin',
        
        # Healthcare
        'zorg', 'huisarts', 'ziekenhuis', 'ggd', 'zorgverzekering', 
        'zorgverzekeraar', 'eigen risico', 'apotheek', 'medicijn', 'ggz',
        
        # Transport
        'ov', 'ns', 'trein', 'bus', 'tram', 'metro', 'ov-chipkaart',
        'rijbewijs', 'cbr', 'auto', 'verkeer', 'file',
        
        # Culture
        'koningsdag', 'sinterklaas', 'kerst', 'pasen', 'bevrijdingsdag',
        'cultuur', 'traditie', 'feest', 'vrijwilliger', 'sport', 'voetbal',
        
        # Domestic context
        'nederlandse', 'nederlands', 'in nederland', 'voor nederland',
        'nieuwkomers', 'expat', 'arbeidsmigrant', 'kennismigrant',
    ]
    
    for keyword in dutch_keywords:
        if keyword in lower_text:
            return True
    
    return False


def fetch_relevant_articles(limit: int = 5) -> List[Article]:
    """Fetch articles with deduplication"""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=1)

    articles: List[Article] = []
    seen_links = set()  # Track seen URLs

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
            
            if not title or not summary:
                continue
            if link in seen_links:  # Skip duplicates
                continue
            
            text_to_check = f"{title} {summary}"
            
            if not _is_relevant_to_netherlands(text_to_check):
                continue
            
            category = _get_category(text_to_check)
            seen_links.add(link)

            article = Article(
                title=title,
                summary=summary,
                link=link,
                published=published,
                source=source_title,
                category=category,
            )
            articles.append(article)

    articles.sort(
        key=lambda x: x.published or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    
    return articles[:limit]