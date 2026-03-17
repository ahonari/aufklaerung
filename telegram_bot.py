from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
)

from config import get_settings
from curator import fetch_relevant_articles
from personalizer import LanguageCode, Mode, UserPreferences, personalize_article


USERS_FILE = Path("users.json")


def _load_users() -> Dict[str, Dict]:
    if not USERS_FILE.exists():
        return {}
    try:
        with USERS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        return {}
    return {}


def _save_users(data: Dict[str, Dict]) -> None:
    with USERS_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _get_or_create_user(chat_id: int) -> Dict:
    users = _load_users()
    key = str(chat_id)
    if key not in users:
        users[key] = {
            "language": "tr",
            "mode": "native",
            "dutch_level": "B1",
            "country_of_origin": None,
        }
        _save_users(users)
    return users[key]


def _update_user(chat_id: int, **fields) -> Dict:
    users = _load_users()
    key = str(chat_id)
    user = users.get(
        key,
        {
            "language": "tr",
            "mode": "native",
            "dutch_level": "B1",
            "country_of_origin": None,
        },
    )
    user.update(fields)
    users[key] = user
    _save_users(users)
    return user


def _prefs_from_dict(chat_id: int, data: Dict) -> UserPreferences:
    language: LanguageCode = data.get("language", "tr")  # type: ignore[assignment]
    mode: Mode = data.get("mode", "native")  # type: ignore[assignment]
    return UserPreferences(
        chat_id=chat_id,
        language=language,
        mode=mode,
        dutch_level=data.get("dutch_level", "B1"),
        country_of_origin=data.get("country_of_origin"),
    )


async def start(update: Update, context: CallbackContext) -> None:
    if update.effective_chat is None:
        return
    chat_id = update.effective_chat.id
    _get_or_create_user(chat_id)

    keyboard = [
        [
            InlineKeyboardButton("Türkçe", callback_data="lang_tr"),
            InlineKeyboardButton("العربية", callback_data="lang_ar"),
            InlineKeyboardButton("فارسی", callback_data="lang_fa"),  # Changed from Polski to Farsi
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Welkom! Kies je taal / Choose your language:", reply_markup=reply_markup
    )


async def language_chosen(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    if query is None or query.message is None or query.from_user is None:
        return

    await query.answer()
    chat_id = query.from_user.id

    data = query.data or ""
    if data == "lang_tr":
        language: LanguageCode = "tr"
    elif data == "lang_ar":
        language = "ar"
    elif data == "lang_fa":  # Changed from "lang_pl" to "lang_fa"
        language = "fa"
    else:
        language = "tr"

    _update_user(chat_id, language=language)

    await query.edit_message_text(
        "Bedankt! Ik zal nu een dagelijks overzicht sturen van belangrijke nieuwsartikelen over immigratie.\n"
        "Je kunt op elk moment /news sturen om een nieuw overzicht te krijgen."
    )

    await send_news_digest(chat_id, context)


async def send_news_digest(chat_id: int, context: CallbackContext) -> None:
    user_dict = _get_or_create_user(chat_id)
    prefs = _prefs_from_dict(chat_id, user_dict)

    await context.bot.send_message(chat_id=chat_id, text="Even kijken naar het laatste nieuws...")

    articles = fetch_relevant_articles(limit=3)
    if not articles:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Sorry, ik kon geen geschikte artikelen vinden in de laatste 24 uur.",
        )
        return

    for article in articles:
        try:
            personalized = personalize_article(article, prefs)
        except Exception:
            personalized = f"{article.title}\n\n(Kan persoonlijke samenvatting niet maken.)"

        message = f"{personalized}\n\n🔗 {article.link}"
        await context.bot.send_message(chat_id=chat_id, text=message)


async def news_command(update: Update, context: CallbackContext) -> None:
    if update.effective_chat is None:
        return
    chat_id = update.effective_chat.id
    await send_news_digest(chat_id, context)


def build_application() -> Application:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not set. Please create a .env file based on .env.example."
        )

    application = Application.builder().token(settings.telegram_bot_token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("news", news_command))
    application.add_handler(CallbackQueryHandler(language_chosen, pattern=r"^lang_(tr|ar|fa)$"))

    return application

if __name__ == "__main__":
    # Create the application
    app = build_application()
    
    # Print a message so you know it's starting
    print("🤖 Aufklärung bot is starting...")
    print("Press Ctrl+C to stop")
    
    # Start the bot (this keeps it running)
    app.run_polling()