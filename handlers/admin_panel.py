import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import ADMIN_IDS

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
    try:
        import database as db
        if not db.pool:
            raise Exception("DB not connected")
        total = await db.get_user_count()
        active = await db.get_active_count()
        today = await db.get_today_joins()
    except Exception:
        total, active, today = 0, 0, 0
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
    try:
        import database as db
        if not db.pool:
            raise Exception("DB not connected")
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
        text = (
            f"\ud83d\udcca <b>Detailed Statistics</b>\n\n"
            f"<b>Users:</b>\n"
            f"\ud83d\udc65 Total: {total:,}\n"
            f"\u2705 Active: {active:,}\n"
            f"\u274c Blocked: {blocked:,}\n"
            f"\ud83d\udfe2 Active 24h: {active_24h:,}\n"
            f"\ud83d\udfe1 Active 7d: {active_7d:,}\n\n"
            f"<b>Growth:</b>\n"
            f"\ud83d\udcc8 Today: +{today:,}\n"
            f"\ud83d\udcc8 This week: +{week:,}\n"
            f"\ud83d\udcc8 This month: +{month:,}\n\n"
            f"<b>Join Requests:</b>\n"
            f"\ud83d\udccb Total: {jr_stats['total']:,}\n"
            f"\u2705 Approved: {jr_stats['approved']:,}\n"
            f"\ud83d\udce8 DMs sent: {jr_stats['dm_sent']:,} ({dm_rate:.1f}%)\n\n"
            f"<b>Referrals:</b>\n"
            f"\ud83d\udd17 Total: {total_refs:,}\n"
            f"\ud83c\udfc6 Top: {top_name} ({top_count})\n\n"
            f"<b>Broadcasts:</b> {bc_count:,}"
        )
    except Exception as e:
        logger.error(f"DB error in stats_panel: {e}")
        text = "\u26a0\ufe0f Database temporarily unavailable. Stats cannot be shown."
    buttons = [[InlineKeyboardButton("\u25c0\ufe0f Back", callback_data="admin_panel")]]
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
