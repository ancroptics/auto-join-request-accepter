import time
from datetime import datetime, timedelta


def format_number(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def format_duration(seconds):
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    return f"{seconds // 3600}h {(seconds % 3600) // 60}m"


def progress_bar(current, total, length=10):
    if total == 0:
        return "░" * length
    filled = int(length * current / total)
    return "▓" * filled + "░" * (length - filled)


def get_tier(referral_count):
    if referral_count >= 500:
        return "👑 Legend"
    if referral_count >= 100:
        return "💎 Diamond"
    if referral_count >= 25:
        return "🥇 Gold"
    if referral_count >= 5:
        return "🥈 Silver"
    return "🥉 Bronze"


def next_tier_info(referral_count):
    tiers = [(5, "🥈 Silver"), (25, "🥇 Gold"), (100, "💎 Diamond"), (500, "👑 Legend")]
    for threshold, name in tiers:
        if referral_count < threshold:
            return name, threshold
    return "👑 Legend", referral_count


def truncate_text(text, max_len=4000):
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


def escape_html(text):
    if not text:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
