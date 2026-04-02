import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import ADMIN_IDS
import database as db

logger = logging.getLogger(__name__)

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        if update.callback_query:
            await update.callback_query.answer("Not authorized", show_alert=True)
        return
    if update.callback_query:
        await update.callback_query.answer()

    kb = [
        [InlineKeyboardButton("\U0001f4ca Stats", callback_data="stats_panel"),
         InlineKeyboardButton("\U0001f4e2 Broadcast", callback_data="broadcast_panel")],
        [InlineKeyboardButton("\U0001f517 Join Requests", callback_data="joinreq_panel"),
         InlineKeyboardButton("\U0001f4fa Channels", callback_data="channels_panel")],
        [InlineKeyboardButton("\U0001f4c4 Templates", callback_data="templates_panel"),
         InlineKeyboardButton("\u23f0 Auto-Poster", callback_data="autoposter_panel")],
        [InlineKeyboardButton("\U0001f465 User Mgmt", callback_data="usermgmt_panel"),
         InlineKeyboardButton("\u2699\ufe0f Settings", callback_data="settings_panel")],
    ]
    text = (
        "\U0001f6e0 <b>Admin Panel</b>\n\n"
        "Select an option below:"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))


async def stats_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        if not db.pool:
            raise Exception("DB not connected")
        total = await db.get_user_count()
        active_24h = await db.get_active_24h()
        active_7d = await db.get_active_7d()
        channels = await db.get_all_channels()
        text = (
            "\U0001f4ca <b>Bot Statistics</b>\n\n"
            f"\U0001f465 Total Users: {total}\n"
            f"\U0001f7e2 Active (24h): {active_24h}\n"
            f"\U0001f535 Active (7d): {active_7d}\n"
            f"\U0001f4fa Channels: {len(channels)}\n"
        )
    except Exception as e:
        logger.error(f"DB error in stats_panel: {e}")
        text = "\U0001f4ca <b>Stats</b>\n\n\u26a0\ufe0f Database not connected. Stats unavailable."
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="admin_panel")]])
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)


async def broadcast_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    kb = [
        [InlineKeyboardButton("\U0001f4e2 All Users", callback_data="broadcast_all"),
         InlineKeyboardButton("\U0001f195 New Users (7d)", callback_data="broadcast_new")],
        [InlineKeyboardButton("\U0001f7e2 Active Users", callback_data="broadcast_active")],
        [InlineKeyboardButton("\U0001f519 Back", callback_data="admin_panel")],
    ]
    await query.edit_message_text(
        "\U0001f4e2 <b>Broadcast</b>\n\nSelect target audience:",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb)
    )


async def joinreq_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        settings = await db.get_settings() if db.pool else {}
    except:
        settings = {}
    auto_approve = settings.get("auto_approve", True)
    status = "\u2705 ON" if auto_approve else "\u274c OFF"
    kb = [
        [InlineKeyboardButton(f"Auto-Approve: {status}", callback_data="toggle_auto_approve")],
        [InlineKeyboardButton("\u270f\ufe0f Edit Welcome Msg", callback_data="edit_welcome_msg")],
        [InlineKeyboardButton("\U0001f519 Back", callback_data="admin_panel")],
    ]
    await query.edit_message_text(
        "\U0001f517 <b>Join Request Settings</b>\n\n"
        f"Auto-Approve: {status}\n"
        "Configure how join requests are handled.",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb)
    )


async def channels_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        channels = await db.get_all_channels() if db.pool else []
    except:
        channels = []
    if channels:
        text = "\U0001f4fa <b>Channels</b>\n\n"
        for ch in channels:
            text += f"\u2022 <code>{ch['channel_id']}</code> - {ch.get('title', 'Unknown')}\n"
        text += "\nUse /addchannel &lt;chat_id&gt; to add\nUse /removechannel &lt;chat_id&gt; to remove"
    else:
        text = "\U0001f4fa <b>Channels</b>\n\nNo channels configured.\nUse /addchannel &lt;chat_id&gt; to add one."
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="admin_panel")]])
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)


async def templates_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        templates = await db.get_all_templates() if db.pool else []
    except:
        templates = []
    if not templates:
        text = "\U0001f4c4 <b>Templates</b>\n\nNo templates yet.\nUse /addtemplate &lt;name&gt; to create one."
    else:
        text = "\U0001f4c4 <b>Templates</b>\n\n"
        for t in templates:
            text += f"\u2022 <b>{t['name']}</b>: {t['content'][:50]}...\n"
        text += "\nUse /addtemplate &lt;name&gt; to add\nUse /deltemplate &lt;name&gt; to remove"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="admin_panel")]])
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)


async def autoposter_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        jobs = await db.get_all_autoposter_jobs() if db.pool else []
    except:
        jobs = []
    if not jobs:
        text = "\u23f0 <b>Auto-Poster</b>\n\nNo auto-post jobs configured.\nUse /addposter to create one."
    else:
        text = "\u23f0 <b>Auto-Poster Jobs</b>\n\n"
        for j in jobs:
            status = "\u2705" if j.get('active') else "\u274c"
            text += f"{status} <code>{j['channel_id']}</code> every {j.get('interval_minutes', '?')}min\n"
        text += "\nUse /addposter to add\nUse /delposter &lt;chat_id&gt; to remove"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="admin_panel")]])
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)


async def usermgmt_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    kb = [
        [InlineKeyboardButton("\U0001f50d Lookup User", callback_data="lookup_user"),
         InlineKeyboardButton("\U0001f6ab Ban User", callback_data="ban_user")],
        [InlineKeyboardButton("\U0001f4e5 Export Users", callback_data="export_users")],
        [InlineKeyboardButton("\U0001f519 Back", callback_data="admin_panel")],
    ]
    await query.edit_message_text(
        "\U0001f465 <b>User Management</b>\n\n"
        "Commands:\n"
        "/userinfo &lt;id&gt; - User details\n"
        "/ban &lt;id&gt; - Ban user\n"
        "/unban &lt;id&gt; - Unban user",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb)
    )


async def settings_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        settings = await db.get_settings() if db.pool else {}
    except:
        settings = {}
    lang = settings.get("language", "en")
    mc = settings.get("mandatory_channels", 0)
    text = (
        "\u2699\ufe0f <b>Settings</b>\n\n"
        f"Language: {lang}\n"
        f"Mandatory Channels: {mc}\n"
        f"DB Connected: {'\u2705' if db.pool else '\u274c'}\n"
    )
    kb = [
        [InlineKeyboardButton("\U0001f310 Language", callback_data="set_language"),
         InlineKeyboardButton("\U0001f517 Mandatory CH", callback_data="set_mandatory")],
        [InlineKeyboardButton("\U0001f519 Back", callback_data="admin_panel")],
    ]
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))


async def toggle_auto_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        settings = await db.get_settings() if db.pool else {}
        current = settings.get("auto_approve", True)
        await db.update_setting("auto_approve", not current)
        await query.answer(f"Auto-approve {'disabled' if current else 'enabled'}!", show_alert=True)
    except Exception as e:
        await query.answer(f"Error: {e}", show_alert=True)
    await joinreq_panel(update, context)


async def export_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Exporting...")
    try:
        users = await db.get_all_users_for_export()
        if not users:
            await query.edit_message_text("No users to export.")
            return
        import io, csv
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=users[0].keys())
        writer.writeheader()
        writer.writerows(users)
        output.seek(0)
        buf = io.BytesIO(output.getvalue().encode())
        buf.name = "users_export.csv"
        await query.message.reply_document(buf, caption="\U0001f4e5 User export")
    except Exception as e:
        await query.edit_message_text(f"Export error: {e}")


async def edit_welcome_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["set_welcome_chat_id"] = "global"
    try:
        current = await db.get_bot_setting("welcome_message", "Not set")
    except:
        current = "Not set"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Cancel", callback_data="joinreq_panel")]])
    try:
        await query.edit_message_text(
            f"\U0001f4dd <b>Edit Welcome Message</b>\n\n"
            f"<b>Current:</b>\n{current}\n\n"
            f"Send me the new welcome message, or /cancel",
            parse_mode="HTML", reply_markup=kb
        )
    except:
        await query.message.reply_text(
            f"\U0001f4dd <b>Edit Welcome Message</b>\n\n"
            f"<b>Current:</b>\n{current}\n\n"
            f"Send me the new welcome message, or /cancel",
            parse_mode="HTML", reply_markup=kb
        )


async def lookup_user_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="usermgmt_panel")]])
    await query.edit_message_text(
        "\U0001f50d <b>Lookup User</b>\n\n"
        "Send a command:\n"
        "<code>/userinfo &lt;user_id&gt;</code>\n\n"
        "Example: <code>/userinfo 123456789</code>",
        parse_mode="HTML", reply_markup=kb
    )


async def ban_user_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="usermgmt_panel")]])
    await query.edit_message_text(
        "\U0001f6ab <b>Ban User</b>\n\n"
        "Send a command:\n"
        "<code>/ban &lt;user_id&gt;</code> - Ban a user\n"
        "<code>/unban &lt;user_id&gt;</code> - Unban a user\n\n"
        "Example: <code>/ban 123456789</code>",
        parse_mode="HTML", reply_markup=kb
    )


async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route all admin panel callbacks."""
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    if user_id not in ADMIN_IDS:
        await query.answer("Not authorized", show_alert=True)
        return

    routes = {
        "admin_panel": admin_panel,
        "stats_panel": stats_panel,
        "broadcast_panel": broadcast_panel,
        "joinreq_panel": joinreq_panel,
        "channels_panel": channels_panel,
        "templates_panel": templates_panel,
        "autoposter_panel": autoposter_panel,
        "usermgmt_panel": usermgmt_panel,
        "settings_panel": settings_panel,
        "toggle_auto_approve": toggle_auto_approve,
        "export_users": export_users,
        "edit_welcome_msg": edit_welcome_msg,
        "lookup_user": lookup_user_cb,
        "ban_user": ban_user_cb,
    }

    handler = routes.get(data)
    if handler:
        try:
            await handler(update, context)
        except Exception as e:
            logger.error(f"Admin callback error '{data}': {e}")
            import traceback
            traceback.print_exc()
            try:
                await query.answer(f"Error: {str(e)[:80]}", show_alert=True)
            except Exception:
                pass
    else:
        try:
            await query.answer("Unknown admin action", show_alert=True)
        except Exception:
            pass
