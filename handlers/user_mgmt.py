import logging
import io
import csv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from config import ADMIN_IDS
import database as db
from utils.helpers import format_number, get_tier, escape_html

logger = logging.getLogger(__name__)

FIND_USER_ID = range(1)


async def users_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    stats = await db.get_user_stats()
    total = stats.get("total", 0)
    active = stats.get("active_24h", 0)
    banned = stats.get("banned", 0)
    text = (
        "👥 <b>User Management</b>\n\n"
        f"Total users: <b>{format_number(total)}</b>\n"
        f"Active (24h): <b>{format_number(active)}</b>\n"
        f"Banned: <b>{format_number(banned)}</b>\n"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Find User", callback_data="um_find"),
         InlineKeyboardButton("🚫 Ban User", callback_data="um_ban")],
        [InlineKeyboardButton("✅ Unban User", callback_data="um_unban"),
         InlineKeyboardButton("📤 Export CSV", callback_data="um_export")],
        [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")],
    ])
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")


async def export_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Generating CSV...")
    users = await db.get_all_users_for_export()
    if not users:
        await query.edit_message_text("No users to export.")
        return
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["user_id", "username", "first_name", "joined_at", "referral_count", "is_banned"])
    for u in users:
        writer.writerow([
            u.get("user_id"),
            u.get("username", ""),
            u.get("first_name", ""),
            u.get("joined_at", ""),
            u.get("referral_count", 0),
            u.get("is_banned", False),
        ])
    output.seek(0)
    bio = io.BytesIO(output.getvalue().encode("utf-8"))
    bio.name = "users_export.csv"
    await context.bot.send_document(chat_id=query.message.chat_id, document=bio, caption=f"📤 Exported {len(users)} users")


async def ban_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text("Usage: /ban <user_id>")
        return
    try:
        target = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid user ID.")
        return
    await db.set_user_banned(target, True)
    await update.message.reply_text(f"🚫 User {target} banned.")


async def unban_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text("Usage: /unban <user_id>")
        return
    try:
        target = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid user ID.")
        return
    await db.set_user_banned(target, False)
    await update.message.reply_text(f"✅ User {target} unbanned.")


async def find_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text("Usage: /finduser <user_id>")
        return
    try:
        target = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid user ID.")
        return
    user = await db.get_user(target)
    if not user:
        await update.message.reply_text("User not found.")
        return
    tier = get_tier(user.get("referral_count", 0))
    text = (
        f"👤 <b>User Info</b>\n\n"
        f"ID: <code>{user['user_id']}</code>\n"
        f"Name: {escape_html(user.get('first_name', 'N/A'))}\n"
        f"Username: @{user.get('username', 'N/A')}\n"
        f"Tier: {tier}\n"
        f"Referrals: {user.get('referral_count', 0)}\n"
        f"Banned: {'Yes' if user.get('is_banned') else 'No'}\n"
        f"Joined: {user.get('joined_at', 'N/A')}\n"
    )
    await update.message.reply_text(text, parse_mode="HTML")
