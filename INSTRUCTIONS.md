# aufklearung - AI News Curator for Immigrants

I want to build a Python application with these specifications:

## CORE FUNCTIONALITY
Two AI agents working together:

**Agent 1: News Curator**
- Fetches RSS feeds from Dutch news sources (start with nos.nl and nu.nl)
- Filters articles using keywords: ['immigrant', 'buitenlander', 'integratie', 'statushouder', 'vluchteling', 'asielzoeker']
- Returns top 5 most relevant articles from last 24 hours

**Agent 2: Personalizer/Translator**
- Takes each article and user preferences (country of origin, Dutch language level)
- If user chooses native language: Summarize article in their language (Turkish/Arabic/Polish/etc.)
- If user chooses Dutch learning: Rewrite article at B1/B2 level with simplified Dutch
- Add cultural context notes in parentheses where helpful

## TECHNICAL REQUIREMENTS
- Use feedparser library for RSS
- Use python-telegram-bot for Telegram integration
- Store user preferences in simple JSON file (start simple)
- Environment variables for API keys

## FILE STRUCTURE
Create:
- main.py (orchestrator)
- curator.py (Agent 1 - RSS fetching and filtering)
- personalizer.py (Agent 2 - LLM prompts)
- telegram_bot.py (Telegram interface)
- config.py (settings and environment variables)
- requirements.txt (dependencies)
- .env.example (template for API keys)
- users.json (simple storage for user preferences)

## FIRST VERSION
Start with a Telegram bot that:
1. User sends /start and chooses language (Turkish/Arabic/Polish)
2. Bot sends daily digest of 3 simplified news items
3. Each item has: Headline (simplified), 2-3 sentence summary, original link

Please generate all files with working code.