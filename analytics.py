from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any

ANALYTICS_FILE = Path("analytics.json")


def _load_analytics() -> Dict[str, Any]:
    """Load analytics data"""
    if not ANALYTICS_FILE.exists():
        return {
            "total_users": 0,
            "active_users": [],  # Use list for JSON serialization
            "commands": {},
            "articles_delivered": 0,
            "preferences": {
                "native": 0,
                "dutch": 0,
                "languages": {},
                "intensities": {},
                "dutch_levels": {"A2": 0, "B1": 0, "B2": 0}
            },
            "daily_activity": {},
            "first_seen": {},
            "last_seen": {}
        }
    
    try:
        with ANALYTICS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure intensities dict has proper format
            if "preferences" in data and "intensities" not in data["preferences"]:
                data["preferences"]["intensities"] = {}
            return data
    except Exception:
        return {
            "total_users": 0,
            "active_users": [],
            "commands": {},
            "articles_delivered": 0,
            "preferences": {
                "native": 0,
                "dutch": 0,
                "languages": {},
                "intensities": {},
                "dutch_levels": {"A2": 0, "B1": 0, "B2": 0}
            },
            "daily_activity": {},
            "first_seen": {},
            "last_seen": {}
        }


def _save_analytics(data: Dict[str, Any]) -> None:
    """Save analytics data"""
    with ANALYTICS_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def track_user_seen(chat_id: int) -> None:
    """Track when a user interacts with the bot"""
    data = _load_analytics()
    chat_id_str = str(chat_id)
    today = datetime.now().strftime("%Y-%m-%d")
    
    # First seen
    if chat_id_str not in data["first_seen"]:
        data["first_seen"][chat_id_str] = datetime.now().isoformat()
        data["total_users"] += 1
    
    # Last seen
    data["last_seen"][chat_id_str] = datetime.now().isoformat()
    
    # Active users (users who used in last 30 days) - store as list
    if chat_id_str not in data["active_users"]:
        data["active_users"].append(chat_id_str)
    
    # Daily activity
    if today not in data["daily_activity"]:
        data["daily_activity"][today] = {
            "users": [],  # Use list instead of set
            "commands": {},
            "articles": 0
        }
    
    # Add user to daily activity if not already there
    if chat_id_str not in data["daily_activity"][today]["users"]:
        data["daily_activity"][today]["users"].append(chat_id_str)
    
    _save_analytics(data)


def track_command(chat_id: int, command: str) -> None:
    """Track command usage"""
    data = _load_analytics()
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Global command count
    if command not in data["commands"]:
        data["commands"][command] = 0
    data["commands"][command] += 1
    
    # Daily command count
    if today not in data["daily_activity"]:
        data["daily_activity"][today] = {
            "users": [],
            "commands": {},
            "articles": 0
        }
    
    if command not in data["daily_activity"][today]["commands"]:
        data["daily_activity"][today]["commands"][command] = 0
    data["daily_activity"][today]["commands"][command] += 1
    
    _save_analytics(data)


def track_articles_delivered(chat_id: int, count: int) -> None:
    """Track articles delivered to users"""
    data = _load_analytics()
    today = datetime.now().strftime("%Y-%m-%d")
    
    data["articles_delivered"] += count
    
    if today not in data["daily_activity"]:
        data["daily_activity"][today] = {
            "users": [],
            "commands": {},
            "articles": 0
        }
    
    data["daily_activity"][today]["articles"] += count
    
    _save_analytics(data)


def track_preferences(chat_id: int, mode: str, language: str = None, intensity: int = None, dutch_level: str = None) -> None:
    """Track user preferences for aggregated stats"""
    data = _load_analytics()
    
    # Mode tracking
    if mode == "native":
        data["preferences"]["native"] += 1
        if language:
            if language not in data["preferences"]["languages"]:
                data["preferences"]["languages"][language] = 0
            data["preferences"]["languages"][language] += 1
    elif mode == "dutch":
        data["preferences"]["dutch"] += 1
        if dutch_level:
            data["preferences"]["dutch_levels"][dutch_level] += 1
    
    # Intensity tracking
    if intensity is not None:
        intensity_key = str(intensity)
        if intensity_key not in data["preferences"]["intensities"]:
            data["preferences"]["intensities"][intensity_key] = 0
        data["preferences"]["intensities"][intensity_key] += 1
    
    _save_analytics(data)


def get_analytics_summary() -> Dict[str, Any]:
    """Get a summary of analytics for display"""
    data = _load_analytics()
    
    today = datetime.now().strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    # Calculate weekly active users
    weekly_users = set()
    for date, activity in data["daily_activity"].items():
        if date >= week_ago:
            for user_id in activity.get("users", []):
                weekly_users.add(user_id)
    
    # Convert active_users list to set for counting
    active_users_30d = len(set(data.get("active_users", [])))
    
    # Get top commands
    top_commands = sorted(data["commands"].items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Ensure intensities are properly formatted for display
    intensities = data["preferences"].get("intensities", {})
    
    return {
        "total_users": data["total_users"],
        "active_users_30d": active_users_30d,
        "active_users_7d": len(weekly_users),
        "total_articles_delivered": data["articles_delivered"],
        "daily_avg_articles": data["articles_delivered"] / max(len(data["daily_activity"]), 1),
        "top_commands": top_commands,
        "preferences": {
            "native": data["preferences"].get("native", 0),
            "dutch": data["preferences"].get("dutch", 0),
            "languages": data["preferences"].get("languages", {}),
            "intensities": intensities,
            "dutch_levels": data["preferences"].get("dutch_levels", {"A2": 0, "B1": 0, "B2": 0})
        },
        "today": data["daily_activity"].get(today, {"users": [], "commands": {}, "articles": 0})
    }


# Optional: Clean up old activity data (keep last 90 days)
def cleanup_old_activity() -> None:
    """Remove activity data older than 90 days"""
    data = _load_analytics()
    cutoff = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    
    # Remove old daily activity
    old_dates = [date for date in data["daily_activity"] if date < cutoff]
    for date in old_dates:
        del data["daily_activity"][date]
    
    # Clean up active_users list (only keep users who were active in last 30 days)
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    recent_users = set()
    for date, activity in data["daily_activity"].items():
        if date >= thirty_days_ago:
            for user_id in activity.get("users", []):
                recent_users.add(user_id)
    
    data["active_users"] = list(recent_users)
    
    _save_analytics(data)