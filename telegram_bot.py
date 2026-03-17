from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
)

from config import get_settings
from curator import fetch_relevant_articles
from personalizer import LanguageCode, Mode, UserPreferences, personalize_article


USERS_FILE = Path("users.json")

# Conversation states
SELECTING_DUTCH_LEVEL, SELECTING_NATIVE_LANG = range(2)


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
            "language": None,
            "mode": None,
            "dutch_level": None,
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
            "language": None,
            "mode": None,
            "dutch_level": None,
            "country_of_origin": None,
        },
    )
    user.update(fields)
    users[key] = user
    _save_users(users)
    return user


def _prefs_from_dict(chat_id: int, data: Dict) -> UserPreferences:
    return UserPreferences(
        chat_id=chat_id,
        language=data.get("language"),
        mode=data.get("mode"),
        dutch_level=data.get("dutch_level"),
        country_of_origin=data.get("country_of_origin"),
    )


async def start(update: Update, context: CallbackContext) -> None:
    """Start command - shows all options in one keyboard"""
    if update.effective_chat is None:
        return
    chat_id = update.effective_chat.id
    _get_or_create_user(chat_id)

    # Main menu keyboard
    keyboard = [
        [InlineKeyboardButton("🇹🇷 Türkçe (Turkish)", callback_data="lang_tr")],
        [InlineKeyboardButton("🇦🇪 العربية (Arabic)", callback_data="lang_ar")],
        [InlineKeyboardButton("🇮🇷 فارسی (Farsi)", callback_data="lang_fa")],
        [InlineKeyboardButton("🇳🇱 Nederlands - A2 (Beginner)", callback_data="dutch_a2")],
        [InlineKeyboardButton("🇳🇱 Nederlands - B1 (Intermediate)", callback_data="dutch_b1")],
        [InlineKeyboardButton("🇳🇱 Nederlands - B2 (Advanced)", callback_data="dutch_b2")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🌍 Welkom! Kies hoe je het nieuws wilt lezen:\n"
        "Welcome! Choose how you want to read the news:",
        reply_markup=reply_markup
    )
    
    return ConversationHandler.END


async def option_chosen(update: Update, context: CallbackContext) -> int:
    """Handle initial selections"""
    query = update.callback_query
    if query is None or query.message is None or query.from_user is None:
        return ConversationHandler.END

    await query.answer()
    chat_id = query.from_user.id

    data = query.data or ""
    
    # Handle language selection (native mode)
    if data == "lang_tr":
        _update_user(chat_id, language="tr", mode="native", dutch_level=None)
        await query.edit_message_text(
            "✅ Je krijgt nu nieuws in het Turks.\n"
            "You'll now receive news in Turkish.\n\n"
            "Even kijken naar het laatste nieuws..."
        )
        await send_news_digest(chat_id, context)
        return ConversationHandler.END
        
    elif data == "lang_ar":
        _update_user(chat_id, language="ar", mode="native", dutch_level=None)
        await query.edit_message_text(
            "✅ Je krijgt nu nieuws in het Arabisch.\n"
            "You'll now receive news in Arabic.\n\n"
            "Even kijken naar het laatste nieuws..."
        )
        await send_news_digest(chat_id, context)
        return ConversationHandler.END
        
    elif data == "lang_fa":
        _update_user(chat_id, language="fa", mode="native", dutch_level=None)
        await query.edit_message_text(
            "✅ Je krijgt nu nieuws in het Perzisch (Farsi).\n"
            "You'll now receive news in Farsi.\n\n"
            "Even kijken naar het laatste nieuws..."
        )
        await send_news_digest(chat_id, context)
        return ConversationHandler.END
    
    # Handle Dutch level selection - now ask for native language
    elif data in ["dutch_a2", "dutch_b1", "dutch_b2"]:
        # Store the selected level temporarily
        level = data.replace("dutch_", "").upper()
        context.user_data['temp_dutch_level'] = level
        
        # Ask for native language
        keyboard = [
            [InlineKeyboardButton("🇹🇷 Türkçe (Turkish)", callback_data="native_tr")],
            [InlineKeyboardButton("🇦🇪 العربية (Arabic)", callback_data="native_ar")],
            [InlineKeyboardButton("🇮🇷 فارسی (Farsi)", callback_data="native_fa")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🇳🇱 Je hebt gekozen voor Nederlands op {level}-niveau.\n\n"
            "Wat is je moedertaal? (Dit helpt ons om woordvertalingen te geven)\n"
            f"What is your native language? (This helps us provide word translations)",
            reply_markup=reply_markup
        )
        return SELECTING_NATIVE_LANG
    
    return ConversationHandler.END


async def native_language_chosen(update: Update, context: CallbackContext) -> int:
    """Handle native language selection for Dutch learners"""
    query = update.callback_query
    if query is None or query.message is None or query.from_user is None:
        return ConversationHandler.END

    await query.answer()
    chat_id = query.from_user.id

    data = query.data or ""
    
    # Get the stored Dutch level
    dutch_level = context.user_data.get('temp_dutch_level', 'B1')
    
    # Map native language selection
    if data == "native_tr":
        native_lang = "tr"
        lang_name = "Turks"
    elif data == "native_ar":
        native_lang = "ar"
        lang_name = "Arabisch"
    elif data == "native_fa":
        native_lang = "fa"
        lang_name = "Perzisch (Farsi)"
    else:
        native_lang = "tr"
        lang_name = "Turks"
    
    # Save all preferences
    _update_user(
        chat_id, 
        language=native_lang,
        mode="dutch", 
        dutch_level=dutch_level
    )
    
    # Clear temporary data
    context.user_data.pop('temp_dutch_level', None)
    
    await query.edit_message_text(
        f"✅ Je krijgt nu nieuws in eenvoudig Nederlands ({dutch_level}-niveau).\n"
        f"We geven ook vertalingen van moeilijke woorden in het {lang_name}.\n\n"
        f"You'll now receive news in simple Dutch ({dutch_level} level).\n"
        f"We'll also provide translations of difficult words in {lang_name}.\n\n"
        "Even kijken naar het laatste nieuws..."
    )
    
    await send_news_digest(chat_id, context)
    return ConversationHandler.END


async def send_news_digest(chat_id: int, context: CallbackContext) -> None:
    """Send news digest to user"""
    user_dict = _get_or_create_user(chat_id)
    
    # Check if user has made a selection yet
    if user_dict.get("mode") is None:
        await context.bot.send_message(
            chat_id=chat_id,
            text="⚠️ Je moet eerst een taal kiezen met /start\nYou need to choose a language first with /start"
        )
        return
    
    prefs = _prefs_from_dict(chat_id, user_dict)

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
        except Exception as e:
            print(f"Error personalizing article: {e}")
            personalized = f"{article.title}\n\n(Kan persoonlijke samenvatting niet maken.)"

        message = f"{personalized}\n\n🔗 {article.link}"
        await context.bot.send_message(chat_id=chat_id, text=message)


async def news_command(update: Update, context: CallbackContext) -> None:
    """Handle /news command"""
    if update.effective_chat is None:
        return
    chat_id = update.effective_chat.id
    
    user_dict = _get_or_create_user(chat_id)
    if user_dict.get("mode") is None:
        await update.message.reply_text(
            "⚠️ Je moet eerst een taal kiezen met /start\nYou need to choose a language first with /start"
        )
        return
        
    await send_news_digest(chat_id, context)


def build_application() -> Application:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not set. Please create a .env file based on .env.example."
        )

    application = Application.builder().token(settings.telegram_bot_token).build()

    # Conversation handler for Dutch learners flow
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(option_chosen, pattern=r"^(lang_|dutch_)")],
        states={
            SELECTING_NATIVE_LANG: [
                CallbackQueryHandler(native_language_chosen, pattern=r"^native_")
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("news", news_command))
    application.add_handler(conv_handler)

    return application


if __name__ == "__main__":
    # Create the application
    app = build_application()
    
    # Print a message so you know it's starting
    print("🤖 Aufklärung bot is starting...")
    print("Press Ctrl+C to stop")
    
    # Start the bot (this keeps it running)
    app.run_polling()