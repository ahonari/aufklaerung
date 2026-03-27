from __future__ import annotations

import json
import warnings
from datetime import datetime, timedelta
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
from telegram.warnings import PTBUserWarning

from config import get_settings
from curator import fetch_relevant_articles
from personalizer import UserPreferences, personalize_article

import asyncio


warnings.filterwarnings("ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

USERS_FILE = Path("users.json")

# Conversation states - SINGLE DEFINITION
SELECTING_MODE = 0
SELECTING_NATIVE_LANGUAGE = 1
SELECTING_DUTCH_NATIVE = 2
SELECTING_DUTCH_LEVEL = 3
SELECTING_INTENSITY = 4


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
            "intensity": 5,
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
            "intensity": 5,
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
        country_of_origin=None,
    )

async def personalize_article_with_retry(article, prefs, max_retries: int = 3) -> str:
    """Call the LLM with retry on overload"""
    for attempt in range(max_retries):
        try:
            return personalize_article(article, prefs)
        except Exception as e:
            error_msg = str(e).lower()
            # Retry only on overload/server errors (529)
            if ("overloaded" in error_msg or "529" in error_msg or "api_error" in error_msg) and attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 1, 2, 4 seconds
                print(f"Claude overloaded (attempt {attempt + 1}), retrying in {wait_time}s... Error: {e}")
                await asyncio.sleep(wait_time)
            else:
                raise
    raise Exception("Max retries exceeded")


async def send_news_digest(chat_id: int, context: CallbackContext) -> None:
    """Send news digest to user based on their intensity setting"""

def fetch_recent_articles(limit: int = 5) -> list:
    """Fetch articles from the last 24 hours."""
    articles = fetch_relevant_articles(limit=limit * 2)
    
    if not articles:
        return []
    
    cutoff_time = datetime.now() - timedelta(hours=24)
    recent_articles = []
    
    for article in articles:
        if hasattr(article, 'published') and article.published:
            published = article.published
            if published.tzinfo is not None:
                published = published.replace(tzinfo=None)
            cutoff_naive = cutoff_time.replace(tzinfo=None)
            if published >= cutoff_naive:
                recent_articles.append(article)
        else:
            return articles[:limit]
    
    return recent_articles[:limit]


async def start(update: Update, context: CallbackContext) -> int:
    """Start command - show mode selection"""
    if update.effective_chat is None:
        return ConversationHandler.END
    
    chat_id = update.effective_chat.id
    _get_or_create_user(chat_id)

    keyboard = [
        [InlineKeyboardButton("📰 Read news in my language", callback_data="mode_native")],
        [InlineKeyboardButton("🇳🇱 Learn Dutch through news", callback_data="mode_dutch")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🌍 *Welcome to StepIn!* 🌍\n\n"
        "What would you like to do?\n\n"
        "📰 *Read news in my language* — Get Dutch news translated into your native language\n\n"
        "🇳🇱 *Learn Dutch through news* — Read simplified Dutch news with vocabulary translations\n",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return SELECTING_MODE


async def mode_selected(update: Update, context: CallbackContext) -> int:
    """Handle mode selection"""
    query = update.callback_query
    if query is None or query.message is None or query.from_user is None:
        return ConversationHandler.END

    await query.answer()
    data = query.data or ""
    
    if data == "mode_native":
        context.user_data['selected_mode'] = "native"
        
        keyboard = [
            [InlineKeyboardButton("🇹🇷 Türkçe", callback_data="lang_tr")],
            [InlineKeyboardButton("🇵🇱 Polski", callback_data="lang_pl")],
            [InlineKeyboardButton("🇦🇪 العربية", callback_data="lang_ar")],
            [InlineKeyboardButton("🇺🇦 Українська", callback_data="lang_uk")],
            [InlineKeyboardButton("🇫🇷 Français", callback_data="lang_fr")],
            [InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang_fa")],
            [InlineKeyboardButton("🇮🇹 Italiano", callback_data="lang_it")],
            [InlineKeyboardButton("🇷🇴 Română", callback_data="lang_ro")],
            [InlineKeyboardButton("🇧🇬 Български", callback_data="lang_bg")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📰 *Read news in my language*\n\n"
            "Choose your preferred language:\n",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return SELECTING_NATIVE_LANGUAGE
    
    elif data == "mode_dutch":
        context.user_data['selected_mode'] = "dutch"
        
        keyboard = [
            [InlineKeyboardButton("🇹🇷 Türkçe", callback_data="dutch_native_tr")],
            [InlineKeyboardButton("🇵🇱 Polski", callback_data="dutch_native_pl")],
            [InlineKeyboardButton("🇦🇪 العربية", callback_data="dutch_native_ar")],
            [InlineKeyboardButton("🇺🇦 Українська", callback_data="dutch_native_uk")],
            [InlineKeyboardButton("🇫🇷 Français", callback_data="dutch_native_fr")],
            [InlineKeyboardButton("🇮🇷 فارسی", callback_data="dutch_native_fa")],
            [InlineKeyboardButton("🇮🇹 Italiano", callback_data="dutch_native_it")],
            [InlineKeyboardButton("🇷🇴 Română", callback_data="dutch_native_ro")],
            [InlineKeyboardButton("🇧🇬 Български", callback_data="dutch_native_bg")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🇳🇱 *Learn Dutch through news*\n\n"
            "What is your native language?\n"
            "This helps us provide vocabulary translations.\n",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return SELECTING_DUTCH_NATIVE
    
    return ConversationHandler.END


async def native_language_selected(update: Update, context: CallbackContext) -> int:
    """Handle native language selection for native mode"""
    query = update.callback_query
    if query is None or query.message is None or query.from_user is None:
        return ConversationHandler.END

    await query.answer()
    chat_id = query.from_user.id
    data = query.data or ""
    
    lang_map = {
        "lang_tr": "tr", "lang_pl": "pl", "lang_ar": "ar",
        "lang_uk": "uk", "lang_fr": "fr", "lang_fa": "fa",
        "lang_it": "it", "lang_ro": "ro", "lang_bg": "bg",
    }
    
    language = lang_map.get(data, "tr")
    lang_names = {
        "tr": "Turkish", "pl": "Polish", "ar": "Arabic",
        "uk": "Ukrainian", "fr": "French", "fa": "Farsi",
        "it": "Italian", "ro": "Romanian", "bg": "Bulgarian"
    }
    lang_name = lang_names.get(language, "your language")
    
    context.user_data['temp_language'] = language
    context.user_data['temp_lang_name'] = lang_name
    
    keyboard = [
        [InlineKeyboardButton("📄 1-2 articles per day", callback_data="intensity_2")],
        [InlineKeyboardButton("📚 3-5 articles per day", callback_data="intensity_5")],
        [InlineKeyboardButton("📰 6-10 articles per day", callback_data="intensity_10")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"✅ Language: {lang_name}\n\n"
        "How many articles would you like per day?",
        reply_markup=reply_markup
    )
    return SELECTING_INTENSITY


async def dutch_native_selected(update: Update, context: CallbackContext) -> int:
    """Handle native language selection for Dutch learner mode"""
    query = update.callback_query
    if query is None or query.message is None or query.from_user is None:
        return ConversationHandler.END

    await query.answer()
    data = query.data or ""
    
    native_map = {
        "dutch_native_tr": "tr", "dutch_native_pl": "pl", "dutch_native_ar": "ar",
        "dutch_native_uk": "uk", "dutch_native_fr": "fr", "dutch_native_fa": "fa",
        "dutch_native_it": "it", "dutch_native_ro": "ro", "dutch_native_bg": "bg",
    }
    
    native_language = native_map.get(data, "tr")
    native_names = {
        "tr": "Turkish", "pl": "Polish", "ar": "Arabic",
        "uk": "Ukrainian", "fr": "French", "fa": "Farsi",
        "it": "Italian", "ro": "Romanian", "bg": "Bulgarian"
    }
    native_name = native_names.get(native_language, "your language")
    
    context.user_data['temp_native_language'] = native_language
    context.user_data['temp_native_name'] = native_name
    
    keyboard = [
        [InlineKeyboardButton("🔵 A2 - Beginner", callback_data="level_a2")],
        [InlineKeyboardButton("🟢 B1 - Intermediate", callback_data="level_b1")],
        [InlineKeyboardButton("🟠 B2 - Advanced", callback_data="level_b2")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"✅ Native language: {native_name}\n\n"
        "What is your Dutch level?",
        reply_markup=reply_markup
    )
    return SELECTING_DUTCH_LEVEL


async def dutch_level_selected(update: Update, context: CallbackContext) -> int:
    """Handle Dutch level selection for Dutch learner mode"""
    query = update.callback_query
    if query is None or query.message is None or query.from_user is None:
        return ConversationHandler.END

    await query.answer()
    data = query.data or ""
    
    level_map = {
        "level_a2": "A2",
        "level_b1": "B1",
        "level_b2": "B2",
    }
    dutch_level = level_map.get(data, "B1")
    
    context.user_data['temp_dutch_level'] = dutch_level
    
    keyboard = [
        [InlineKeyboardButton("📄 1-2 articles per day", callback_data="intensity_2")],
        [InlineKeyboardButton("📚 3-5 articles per day", callback_data="intensity_5")],
        [InlineKeyboardButton("📰 6-10 articles per day", callback_data="intensity_10")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"✅ Dutch level: {dutch_level}\n\n"
        "How many articles would you like per day?",
        reply_markup=reply_markup
    )
    return SELECTING_INTENSITY


async def intensity_selected(update: Update, context: CallbackContext) -> int:
    """Handle intensity selection and complete setup"""
    query = update.callback_query
    if query is None or query.message is None or query.from_user is None:
        return ConversationHandler.END

    await query.answer()
    chat_id = query.from_user.id
    data = query.data or ""
    
    intensity_map = {
        "intensity_2": 2,
        "intensity_5": 5,
        "intensity_10": 10,
    }
    intensity = intensity_map.get(data, 5)
    
    selected_mode = context.user_data.get('selected_mode')
    
    if selected_mode == "native":
        language = context.user_data.get('temp_language')
        lang_name = context.user_data.get('temp_lang_name')
        
        _update_user(
            chat_id,
            language=language,
            mode="native",
            dutch_level=None,
            intensity=intensity
        )
        
        context.user_data.clear()
        
        await query.edit_message_text(
            f"✅ *Setup complete!*\n\n"
            f"Your preferences:\n"
            f"• Mode: News in your language\n"
            f"• Language: {lang_name}\n"
            f"• Intensity: {intensity} articles per day\n\n"
            "Use /news to read your first articles!\n\n"
            "Use /settings to change your preferences anytime.",
            parse_mode='Markdown'
        )
    
    elif selected_mode == "dutch":
        native_language = context.user_data.get('temp_native_language')
        native_name = context.user_data.get('temp_native_name')
        dutch_level = context.user_data.get('temp_dutch_level')
        
        _update_user(
            chat_id,
            language=native_language,
            mode="dutch",
            dutch_level=dutch_level,
            intensity=intensity
        )
        
        context.user_data.clear()
        
        await query.edit_message_text(
            f"✅ *Setup complete!*\n\n"
            f"Your preferences:\n"
            f"• Mode: Dutch learner\n"
            f"• Native language: {native_name}\n"
            f"• Dutch level: {dutch_level}\n"
            f"• Intensity: {intensity} articles per day\n\n"
            "Use /news to read your first articles!\n\n"
            "Use /settings to change your preferences anytime.",
            parse_mode='Markdown'
        )
    
    return ConversationHandler.END


async def send_news_digest(chat_id: int, context: CallbackContext) -> None:
    """Send news digest to user based on their intensity setting"""
    user_dict = _get_or_create_user(chat_id)
    
    if user_dict.get("mode") is None:
        await context.bot.send_message(
            chat_id=chat_id,
            text="⚠️ Please set up your preferences first with /start"
        )
        return
    
    intensity = user_dict.get("intensity", 5)
    articles = fetch_recent_articles(limit=intensity)
    
    if not articles:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Sorry, I couldn't find any articles from the last 24 hours. Please try again later.",
        )
        return
    
    prefs = _prefs_from_dict(chat_id, user_dict)
    
    for i, article in enumerate(articles, 1):
        try:
            personalized = personalize_article(article, prefs)
        except Exception as e:
            print(f"Error personalizing article: {e}")
            print(f"User prefs: {prefs}")
            personalized = f"{article.title}\n\n(Could not create personalized summary. Error: {str(e)})"
        
        # Build header
        if len(articles) > 1:
            if article.category:
                header = f"📰 Article {i}/{len(articles)}\n{article.category}\n\n"
            else:
                header = f"📰 Article {i}/{len(articles)}\n\n"
        else:
            if article.category:
                header = f"{article.category}\n\n"
            else:
                header = ""
        
        # Plain text message (no Markdown parsing)
        message = f"{header}{personalized}\n\n🔗 {article.link}"
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode=None  # ← Disable Markdown parsing
        )
    
    await context.bot.send_message(
        chat_id=chat_id,
        text="📌 Use /news again to refresh articles.\nUse /settings to change your preferences.",
        parse_mode=None
    )


async def news_command(update: Update, context: CallbackContext) -> None:
    """Handle /news command"""
    if update.effective_chat is None:
        return
    chat_id = update.effective_chat.id
    
    user_dict = _get_or_create_user(chat_id)
    if user_dict.get("mode") is None:
        await update.message.reply_text(
            "⚠️ Please set up your preferences first with /start"
        )
        return
        
    await send_news_digest(chat_id, context)


async def settings_command(update: Update, context: CallbackContext) -> None:
    """Handle /settings command"""
    if update.effective_chat is None:
        return
    chat_id = update.effective_chat.id
    
    user_dict = _get_or_create_user(chat_id)
    
    if user_dict.get("mode") is None:
        await update.message.reply_text(
            "⚠️ You haven't set up your preferences yet. Use /start to begin."
        )
        return
    
    mode = user_dict.get("mode", "unknown")
    intensity = user_dict.get("intensity", 5)
    
    lang_names = {
        "tr": "🇹🇷 Turkish", "pl": "🇵🇱 Polish", "ar": "🇦🇪 Arabic",
        "uk": "🇺🇦 Ukrainian", "fr": "🇫🇷 French", "fa": "🇮🇷 Farsi",
        "it": "🇮🇹 Italian", "ro": "🇷🇴 Romanian", "bg": "🇧🇬 Bulgarian"
    }
    
    if mode == "native":
        language = user_dict.get("language", "unknown")
        lang_display = lang_names.get(language, language)
        
        settings_text = (
            f"⚙️ *Your Current Settings*\n\n"
            f"📖 Mode: News in your language\n"
            f"🌐 Language: {lang_display}\n"
            f"📊 Intensity: {intensity} articles/day\n\n"
            f"To change your preferences, use /start to restart setup."
        )
    else:
        dutch_level = user_dict.get("dutch_level", "B1")
        native_lang = user_dict.get("language", "unknown")
        native_display = lang_names.get(native_lang, native_lang)
        
        settings_text = (
            f"⚙️ *Your Current Settings*\n\n"
            f"📖 Mode: Dutch learner\n"
            f"🌐 Native language: {native_display}\n"
            f"🇳🇱 Dutch level: {dutch_level}\n"
            f"📊 Intensity: {intensity} articles/day\n\n"
            f"To change your preferences, use /start to restart setup."
        )
    
    keyboard = [[InlineKeyboardButton("🔄 Start Over", callback_data="reset_preferences")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        settings_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def settings_callback(update: Update, context: CallbackContext) -> None:
    """Handle settings menu callbacks - reset and restart conversation"""
    query = update.callback_query
    if query is None or query.message is None or query.from_user is None:
        return

    await query.answer()
    chat_id = query.from_user.id
    data = query.data or ""
    
    if data == "reset_preferences":
        # Reset user preferences
        _update_user(chat_id, language=None, mode=None, dutch_level=None, intensity=5)
        
        # Clear all temporary data
        context.user_data.clear()
        
        # Clear conversation state
        if 'state' in context.chat_data:
            del context.chat_data['state']
        
        # Delete the settings message
        await query.message.delete()
        
        # Create a fake update to start the conversation fresh
        # Create a new message with the same chat_id
        await context.bot.send_message(
            chat_id=chat_id,
            text="🔄 Preferences reset. Let's set up again!"
        )
        
        # Now call start manually with a new message context
        # This is tricky - simpler: tell user to type /start
        await context.bot.send_message(
            chat_id=chat_id,
            text="Please type /start to begin setup."
        )

async def help_command(update: Update, context: CallbackContext) -> None:
    """Handle /help command"""
    help_text = (
        "📖 *StepIn Bot Help*\n\n"
        "*Commands:*\n"
        "/start or /stepin - Set up your preferences\n"
        "/news - Get today's news articles\n"
        "/settings - View and change your preferences\n"
        "/help - Show this menu\n\n"
        "*How it works:*\n"
        "1. Choose what you want to do:\n"
        "   • Read news in your language\n"
        "   • Learn Dutch through news\n"
        "2. Select your language preferences\n"
        "3. Choose how many articles per day\n"
        "4. Use /news whenever you're ready to read\n\n"
        "*Need support?*\n"
        "Contact: hello@stepin.app\n\n"
        "📌 Tip: Use /settings to restart setup anytime."
    )
    
    await update.message.reply_text(help_text, parse_mode='Markdown')


def build_application() -> Application:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not set. Please create a .env file based on .env.example."
        )

    application = Application.builder().token(settings.telegram_bot_token).build()

    # Conversation handler with clean state flow
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start), CommandHandler("stepin", start)],
        states={
            SELECTING_MODE: [
                CallbackQueryHandler(mode_selected, pattern=r"^mode_")
            ],
            SELECTING_NATIVE_LANGUAGE: [
                CallbackQueryHandler(native_language_selected, pattern=r"^lang_")
            ],
            SELECTING_DUTCH_NATIVE: [
                CallbackQueryHandler(dutch_native_selected, pattern=r"^dutch_native_")
            ],
            SELECTING_DUTCH_LEVEL: [
                CallbackQueryHandler(dutch_level_selected, pattern=r"^level_")
            ],
            SELECTING_INTENSITY: [
                CallbackQueryHandler(intensity_selected, pattern=r"^intensity_")
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("news", news_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(settings_callback, pattern=r"^reset_"))

    return application


if __name__ == "__main__":
    app = build_application()
    print("🤖 StepIn bot is starting...")
    print("Press Ctrl+C to stop")
    app.run_polling()