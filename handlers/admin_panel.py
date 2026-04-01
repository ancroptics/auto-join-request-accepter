import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import ADMIN_IDS
import database as db

logger = logging.getLogger(__name__)

def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            if update.callback_query:
                await update.callback_query.answer("\u26d4 Admin only!", show_alert=True)
            return
        return await func(update, context)
    return wrapper

@admin_only
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total = await db.get_user_count()
    active = await db.get_active_count()
    today = await db.get_today_joins()
    buttons = [
        [InlineKeyboardButton("\ud83d\udcca Statistics", callback_data="adm_stats"),
         InlineKeyboardButton("\ud83d\udce2 Broadcast", callback_data="adm_broadcast")],
        [InlineKeyboardButton("\ud83d\udccb Join Requests", callback_data="adm_join_requests"),
         InlineKeyboardButton("\ud83d\udce1 Channels", callback_data="adm_channels")],
        [InlineKeyboardButton("\ud83d\udcdd Templates", callback_data="adm_templates"),
         InlineKeyboardButton("\ud83e\udd16 Auto Poster", callback_data="adm_autoposter")],
        [InlineKeyboardButton("\ud83d\udc65 User Mgmt", callback_data="adm_users"),
         InlineKeyboardButton("\u2699\ufe0f Settings", callback_data="adm_settings")],
    ]
    text = f"\u2699\ufe0f <b>Admin Panel</b>\n\n\ud83d\udc65 Total Users: {total:,}\n\u2705 Active: {active:,}\n\ud83d\udcc8 Today: +{today:,}\n"
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

@admin_only
async def stats_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total = await db.get_user_count()
    active = await db.get_active_count()
    blocked = await db.get_blocked_count()
    today = await db.get_today_joins()
    week = await db.get_week_joins()
    month = await db.get_month_joins()
    active_24h = await db.get_active_24h()
    active_7d = await db.get_active_7d()
    jr_stats = await db.get_join_request_stats()
    total_refs = await db.get_total_referrals()
    top_ref = await db.get_top_referrer()
    bc_count = await db.get_broadcast_count()
    top_name = f"@{top_ref['username']}" if top_ref and top_ref["username"] else "N/A"
    top_count = top_ref["referral_count"] if top_ref else 0
    dm_rate = (jr_stats["dm_sent"] / max(jr_stats["approved"], 1) * 100)
    daily = await db.get_daily_stats(7)
    chart_lines = []
    if daily:
        max_val = max(r["new_users"] for r in daily) or 1
        for r in reversed(daily):
            bars = int(r["new_users"] / max_val * 12)
            chart_lines.append(f"{r['stat_date'].strftime('%m/%d')} {'\u2593' * bars}{'\u2591' * (12-bars)} {r['new_users']}")
    chart = "\n".join(chart_lines) if chart_lines else "No data yet"
    text = (
        f"\ud83d\udcca <b>GROWTH ENGINE ANALYTICS</b>\n\n"
        f"\u2501\u2501\u2501 \ud83d\udc65 USERS \u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        f"Total: {total:,}\nActive: {active:,}\nBlocked: {blocked:,}\n\n"
        f"\u2501\u2501\u2501 \ud83d\udcc8 GROWTH \u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        f"Today: +{today:,}\nThis Week: +{week:,}\nThis Month: +{month:,}\n\n"
        f"\u2501\u2501\u2501 \ud83d\udd25 ENGAGEMENT \u2501\u2501\u2501\u2501\u2501\n"
        f"Active 24h: {active_24h:,} ({active_24h/max(total,1)*100:.1f}%)\n"
        f"Active 7d: {active_7d:,} ({active_7d/max(total,1)*100:.1f}%)\n\n"
        f"\u2501\u2501\u2501 \ud83d\udccb JOIN REQUESTS \u2501\u2501\u2501\n"
        f"Total: {jr_stats['total']:,}\nApproved: {jr_stats['approved']:,}\n"
        f"DMs Sent: {jr_stats['dm_sent']:,}\nDM Rate: {dm_rate:.1f}%\n\n"
        f"\u2501\u2501\u2501 \ud83d\udd17 REFERRALS \u2501\u2501\u2501\u2501\u2501\u2501\n"
        f"Total: {total_refs:,}\nTop: {top_name} ({top_count})\n\n"
        f"\u2501\u2501\u2501 \ud83d\udce2 BROADCASTS \u2501\u2501\u2501\u2501\u2501\n"
        f"Total: {bc_count:,}\n\n"
        f"\u2501\u2501\u2501 7-DAY CHART \u2501\u2501\u2501\n<code>{chart}</code>"
    )
    buttons = [[InlineKeyboardButton("\ud83d\udd19 Admin Panel", callback_data="admin_panel")]]
    await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
