import logging
import io
import csv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import ADMIN_IDS
import database as db
from utils.helpers import format_number, get_tier, escape_html

logger = logging.getLogger(__name__)

UM_FIND, UM_BAN, UM_UNBAN = range(3)


async def users_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        stats = await db.get_user_stats()
        total = stats.get("total", 0)
        active = stats.get("active_24h", 0)
        banned = stats.get("banned", 0)
    except Exception:
        total = active = banned = 0
    text = (
        "\U0001f465 <b>User Management</b>\n\n"
        f"Total users: <b>{format_number(total)}</b>\n"
        f"Active (24h): <b>{format_number(active)}</b>\n"
        f"Banned: <b>{format_number(banned)}</b>\n"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("\U0001f50d Find User", callback_data="um_find"),
         InlineKeyboardButton("\U0001f6ab Ban User", callback_data="um_ban")],
        [InlineKeyboardButton("\u2705 Unban User", callback_data="um_unban"),
         InlineKeyboardButton("\U0001f4e4 Export CSV", callback_data="um_export")],
        [InlineKeyboardButton("\U0001f519 Admin Panel", callback_data="admin_panel")],
    ])
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")


async def export_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Generating CSV...")
    try:
        users = await db.get_all_users_for_export()
    except Exception:
        users = []
    if not users:
        await query.edit_message_text("No users to export.")
        return
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["user_id", "username", "first_name", "joined_at", "referral_count", "is_banned"])
    for u in users:
        writer.writerow([u.get("user_id"), u.get("username", ""), u.get("first_name", ""),
                         u.get("joined_at", ""), u.get("referral_count", 0), u.get("is_banned", False)])
    output.seek(0)
    bio = io.BytesIO(output.getvalue().encode("utf-8"))
    bio.name = "users_export.csv"
    await context.bot.send_document(chat_id=query.message.chat_id, document=bio, caption=f"Exported {len(users)} users")


async def find_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id not in ADMIN_IDS:
        return ConversationHandler.END
    await query.edit_message_text("Send the <b>user ID</b> to find:", parse_mode="HTML")
    return UM_FIND


async def find_user_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Invalid user ID.")
        return ConversationHandler.END
    try:
        user = await db.get_user(target)
    except Exception:
        user = None
    if not user:
        await update.message.reply_text("User not found.")
        return ConversationHandler.END
    tier = get_tier(user.get("referral_count", 0))
    text = (
        f"\U0001f464 <b>User Info</b>\n\n"
        f"ID: <code>{user['user_id']}</code>\n"
        f"Name: {escape_html(user.get('first_name', 'N/A'))}\n"
        f"Username: @{user.get('username', 'N/A')}\n"
        f"Tier: {tier}\n"
        f"Referrals: {user.get('referral_count', 0)}\n"
        f"Banned: {'Yes' if user.get('is_banned') else 'No'}\n"
        f"Joined: {user.get('joined_at', 'N/A')}\n"
    )
    await update.message.reply_text(text, parse_mode="HTML")
    return ConversationHandler.END


async def ban_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id not in ADMIN_IDS:
        return ConversationHandler.END
    await query.edit_message_text("Send the <b>user ID</b> to ban:", parse_mode="HTML")
    return UM_BAN


async def ban_user_exec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Invalid user ID.")
        return ConversationHandler.END
    try:
        await db.set_user_banned(target, True)
        await update.message.reply_text(f"\U0001f6ab User {target} banned.")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")
    return ConversationHandler.END


async def unban_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id not in ADMIN_IDS:
        return ConversationHandler.END
    await query.edit_message_text("Send the <b>user ID</b> to unban:", parse_mode="HTML")
    return UM_UNBAN


async def unban_user_exec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Invalid user ID.")
        return ConversationHandler.END
    try:
        await db.set_user_banned(target, False)
        await update.message.reply_text(f"\u2705 User {target} unbanned.")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")
    return ConversationHandler.END


def get_user_mgmt_handler():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(find_user_start, pattern="^um_find$"),
            CallbackQueryHandler(ban_user_start, pattern="^um_ban$"),
            CallbackQueryHandler(unban_user_start, pattern="^um_unban$"),
        ],
        states={
            UM_FIND: [MessageHandler(filters.TEXT & ~filters.COMMAND, find_user_result)],
            UM_BAN: [MessageHandler(filters.TEXT & ~filters.COMMAND, ban_user_exec)],
            UM_UNBAN: [MessageHandler(filters.TEXT & ~filters.COMMAND, unban_user_exec)],
        },
        fallbacks=[],
        per_message=False,
    )
