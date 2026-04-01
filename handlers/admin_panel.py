import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import ADMIN_IDS
import database as db

logger = logging.getLogger(__name__)

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        return
    buttons = [
        [InlineKeyboardButton("\U0001f4ca Stats", callback_data="admin_stats"),
         InlineKeyboardButton("\U0001f4dd Join Requests", callback_data="admin_join_requests")],
        [InlineKeyboardButton("\U0001f4e1 Channels", callback_data="admin_channels"),
         InlineKeyboardButton("\U0001f4e2 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("\U0001f4c4 Templates", callback_data="admin_templates"),
         InlineKeyboardButton("\U0001f916 Auto-Poster", callback_data="admin_autoposter")],
        [InlineKeyboardButton("\U0001f465 User Mgmt", callback_data="admin_user_mgmt"),
         InlineKeyboardButton("\u2699\ufe0f Settings", callback_data="admin_settings")],
        [InlineKeyboardButton("\U0001f517 Referrals", callback_data="admin_referrals"),
         InlineKeyboardButton("\U0001f4e5 Export Users", callback_data="admin_export")],
        [InlineKeyboardButton("\U0001f519 Home", callback_data="go_home")]
    ]
    text = "\U0001f6e0 <b>Admin Panel</b>\n\nSelect an option:"
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        total = await db.get_user_count()
        active = await db.get_active_24h()
        today = await db.get_today_joins()
        week = await db.get_week_joins()
        month = await db.get_month_joins()
        blocked = await db.get_blocked_count()
        jr = await db.get_join_request_stats()
        bc = await db.get_broadcast_count()
        text = (
            f"\U0001f4ca <b>Bot Statistics</b>\n\n"
            f"\U0001f465 Total Users: <b>{total}</b>\n"
            f"\U0001f7e2 Active (24h): <b>{active}</b>\n"
            f"\U0001f4c5 Today: <b>{today}</b>\n"
            f"\U0001f4c6 This Week: <b>{week}</b>\n"
            f"\U0001f4c5 This Month: <b>{month}</b>\n"
            f"\U0001f6ab Blocked: <b>{blocked}</b>\n\n"
            f"\U0001f4dd <b>Join Requests</b>\n"
            f"Total: {jr['total']} | Approved: {jr['approved']}\n"
            f"DMs Sent: {jr['dm_sent']} | Pending: {jr['pending']}\n"
            f"Today: {jr['today']}\n\n"
            f"\U0001f4e2 Broadcasts Sent: <b>{bc}</b>"
        )
    except Exception as e:
        text = f"\u26a0\ufe0f Stats error: {e}"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="admin_panel")]])
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)

async def show_join_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        stats = await db.get_join_request_stats()
        recent = await db.get_recent_join_requests(5)
        text = (
            f"\U0001f4dd <b>Join Requests</b>\n\n"
            f"Total: {stats['total']} | Approved: {stats['approved']}\n"
            f"DMs Sent: {stats['dm_sent']} | Pending: {stats['pending']}\n"
            f"Today: {stats['today']}\n\n"
            f"<b>Recent:</b>\n"
        )
        for r in recent:
            name = r.get('first_name', 'Unknown')
            status = r.get('status', '?')
            text += f"  \u2022 {name} - {status}\n"
        if not recent:
            text += "  No requests yet.\n"
    except Exception as e:
        text = f"Error: {e}"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="admin_panel")]])
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)

async def show_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        channels = await db.get_all_channels()
        if not channels:
            text = "\U0001f4e1 <b>Channels</b>\n\nNo channels added yet.\nAdd the bot to a channel/group as admin to see it here."
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="admin_panel")]])
        else:
            text = f"\U0001f4e1 <b>Channels ({len(channels)})</b>\n\n"
            buttons = []
            for ch in channels:
                title = ch.get('chat_title', 'Unknown')
                auto = '\u2705' if ch.get('auto_approve') else '\u274c'
                welcome = '\U0001f4ac' if ch.get('welcome_message') else ''
                text += f"\u2022 {title} {auto} {welcome}\n"
                cid = ch['chat_id']
                buttons.append([
                    InlineKeyboardButton(f"\u2699 {title}", callback_data=f"ch_toggle_{cid}"),
                    InlineKeyboardButton("\U0001f4ac Welcome", callback_data=f"ch_welcome_{cid}"),
                    InlineKeyboardButton("\U0001f5d1", callback_data=f"ch_delete_{cid}")
                ])
            buttons.append([InlineKeyboardButton("\U0001f519 Back", callback_data="admin_panel")])
            kb = InlineKeyboardMarkup(buttons)
    except Exception as e:
        text = f"Error: {e}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="admin_panel")]])
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)

async def show_templates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        templates = await db.get_all_templates()
        if not templates:
            text = "\U0001f4c4 <b>Templates</b>\n\nNo templates yet.\nUse /addtemplate <name> to create one."
        else:
            text = f"\U0001f4c4 <b>Templates ({len(templates)})</b>\n\n"
            for t in templates:
                text += f"\u2022 <b>{t['name']}</b>: {t['content'][:50]}...\n"
            text += "\nUse /addtemplate <name> to add\nUse /deltemplate <name> to remove"
    except Exception as e:
        text = f"Error: {e}"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="admin_panel")]])
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)

async def show_autoposter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        jobs = await db.get_all_autoposter_jobs()
        if not jobs:
            text = "\U0001f916 <b>Auto-Poster</b>\n\nNo auto-poster jobs.\nUse /addposter to create one."
        else:
            text = f"\U0001f916 <b>Auto-Poster ({len(jobs)} jobs)</b>\n\n"
            for j in jobs:
                status = '\u2705' if j.get('is_active') else '\u23f8'
                text += f"{status} Chat: {j['chat_id']} every {j['interval_min']}min\n"
            text += "\nUse /addposter to add\nUse /delposter <chat_id> to remove"
    except Exception as e:
        text = f"Error: {e}"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="admin_panel")]])
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)

async def show_user_mgmt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        stats = await db.get_user_stats()
        text = (
            f"\U0001f465 <b>User Management</b>\n\n"
            f"Total: {stats['total']}\n"
            f"Active (24h): {stats['active_24h']}\n"
            f"Banned: {stats['banned']}\n\n"
            f"Commands:\n"
            f"/ban <user_id> - Ban user\n"
            f"/unban <user_id> - Unban user\n"
            f"/userinfo <user_id> - User info"
        )
    except Exception as e:
        text = f"Error: {e}"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="admin_panel")]])
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)

async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        settings = await db.get_bot_settings()
        auto_approve = settings.get('auto_approve', True)
        welcome_dm = settings.get('welcome_dm', True)
        text = (
            f"\u2699\ufe0f <b>Bot Settings</b>\n\n"
            f"Auto-Approve: {'\u2705 ON' if auto_approve else '\u274c OFF'}\n"
            f"Welcome DM: {'\u2705 ON' if welcome_dm else '\u274c OFF'}\n"
            f"Referral Reward: {settings.get('referral_reward', 10)} coins"
        )
    except Exception as e:
        text = f"Error: {e}"
        auto_approve = True
        welcome_dm = True
    buttons = [
        [InlineKeyboardButton(f"{'\u2705' if auto_approve else '\u274c'} Auto-Approve", callback_data="toggle_setting_auto_approve"),
         InlineKeyboardButton(f"{'\u2705' if welcome_dm else '\u274c'} Welcome DM", callback_data="toggle_setting_welcome_dm")],
        [InlineKeyboardButton("\U0001f519 Back", callback_data="admin_panel")]
    ]
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
