# Aufklärung - AI News Curator for Immigrants & Dutch Learners

A Telegram bot that helps immigrants in the Netherlands stay informed while learning Dutch. The bot delivers daily news summaries about immigration-related topics, personalized to each user's language preferences and Dutch proficiency level.

## 🎯 Core Functionality

Two AI agents working together:

**Agent 1: News Curator**
- Fetches RSS feeds from Dutch news sources (NOS.nl and NU.nl)
- Filters articles using keywords related to immigration and integration
- Returns top 3 most relevant articles from the last 24 hours

**Agent 2: Personalizer/Translator** (using Claude AI)
- Takes each article and user preferences
- Two modes of operation:
  - **Native Language Mode**: Summarizes articles in user's native language (Turkish/Arabic/Farsi) with cultural context notes
  - **Dutch Learning Mode**: Rewrites articles in simplified Dutch at A2/B1/B2 levels with vocabulary explanations
- Adds cultural context notes in parentheses where helpful for integration

## 🤖 Bot Features

### User Flow
1. User sends `/start` command
2. Bot presents a single keyboard with all options:
   - 🇹🇷 Türkçe (Turkish)
   - 🇦🇪 العربية (Arabic)
   - 🇮🇷 فارسی (Farsi)
   - 🇳🇱 Nederlands - A2 (Beginner)
   - 🇳🇱 Nederlands - B1 (Intermediate)
   - 🇳🇱 Nederlands - B2 (Advanced)

3. Based on selection:
   - **Native languages**: News summaries in chosen language
   - **Dutch levels**: News summaries in simplified Dutch at the selected CEFR level

4. Bot sends 3 most relevant news items, each with:
   - Simplified headline/summary (in chosen language/level)
   - Original article link for further reading

### Additional Commands
- `/news` - Get a fresh digest immediately
- The bot automatically remembers user preferences

## 🛠 Technical Stack

- **Python 3.12+**
- **python-telegram-bot** (v20+) - Telegram integration
- **feedparser** - RSS feed fetching
- **Anthropic Claude API** - Text summarization and translation
- **python-dotenv** - Environment variable management
- **JSON file** - Simple user preference storage
