import logging
from datetime import datetime, timedelta
import database as db

logger = logging.getLogger(__name__)


async def get_dashboard_stats():
    stats = await db.get_user_stats()
    join_stats = await db.get_join_request_stats()
    return {
        "total_users": stats.get("total", 0),
        "active_24h": stats.get("active_24h", 0),
        "new_today": stats.get("new_today", 0),
        "banned": stats.get("banned", 0),
        "total_join_requests": join_stats.get("total", 0),
        "approved_today": join_stats.get("approved_today", 0),
        "pending": join_stats.get("pending", 0),
    }


async def get_growth_report(days=7):
    daily = await db.get_daily_user_growth(days)
    return daily


async def get_referral_leaderboard(limit=10):
    return await db.get_top_referrers(limit)


def format_dashboard(stats):
    return (
        "\U0001f4ca <b>Dashboard Statistics</b>\n\n"
        f"\U0001f465 Total Users: <b>{stats['total_users']}</b>\n"
        f"\U0001f525 Active (24h): <b>{stats['active_24h']}</b>\n"
        f"\U0001f195 New Today: <b>{stats['new_today']}</b>\n"
        f"\U0001f6ab Banned: <b>{stats['banned']}</b>\n\n"
        f"\U0001f4e5 <b>Join Requests</b>\n"
        f"Total: <b>{stats['total_join_requests']}</b>\n"
        f"Approved Today: <b>{stats['approved_today']}</b>\n"
        f"Pending: <b>{stats['pending']}</b>\n"
    )


def format_leaderboard(users):
    if not users:
        return "No referral data yet."
    medals = ["\U0001f947", "\U0001f948", "\U0001f949"] + ["  "] * 7
    text = "\U0001f3c6 <b>Referral Leaderboard</b>\n\n"
    for i, u in enumerate(users):
        medal = medals[i] if i < len(medals) else "  "
        name = u.get("first_name", "Unknown")[:20]
        count = u.get("referral_count", 0)
        text += f"{medal} {i+1}. {name} — <b>{count}</b> referrals\n"
    return text
