import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from config import ADMIN_IDS
import database as db

logger = logging.getLogger(__name__)

LOOKUP_USER = 0

async def user_mgmt_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return ConversationHandler.END
    cmd = update.message.text.split()[0]
    if cmd == "/ban":
        args = update.message.text.split(maxsplit=1)
        if len(args) < 2:
            await update.message.reply_text("Usage: /ban <user_id>")
            return ConversationHandler.END
        try:
            uid = int(args[1])
            await db.set_user_banned(uid, True)
            await update.message.reply_text(f"\u2705 User {uid} banned.")
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")
        return ConversationHandler.END
    elif cmd == "/unban":
        args = update.message.text.split(maxsplit=1)
        if len(args) < 2:
            await update.message.reply_text("Usage: /unban <user_id>")
            return ConversationHandler.END
        try:
            uid = int(args[1])
            await db.set_user_banned(uid, False)
            await update.message.reply_text(f"\u2705 User {uid} unbanned.")
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")
        return ConversationHandler.END
    elif cmd == "/userinfo":
        args = update.message.text.split(maxsplit=1)
        if len(args) < 2:
            await update.message.reply_text("Usage: /userinfo <user_id>")
            return ConversationHandler.END
        try:
            uid = int(args[1])
            user = await db.get_user(uid)
            if user:
                text = (
                    f"\U0001f464 <b>User Info</b>\n\n"
                    f"ID: <code>{user['user_id']}</code>\n"
                    f"Name: {user.get('first_name', 'N/A')}\n"
                    f"Username: @{user.get('username', 'N/A')}\n"
                    f"Joined: {user.get('joined_at', 'N/A')}\n"
                    f"Referrals: {user.get('referral_count', 0)}\n"
                    f"Coins: {user.get('coins', 0)}\n"
                    f"Banned: {user.get('is_banned', False)}"
                )
            else:
                text = f"User {uid} not found."
            await update.message.reply_text(text, parse_mode="HTML")
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")
        return ConversationHandler.END
    return ConversationHandler.END

def get_user_mgmt_handler():
    return ConversationHandler(
        entry_points=[
            CommandHandler("ban", user_mgmt_start),
            CommandHandler("unban", user_mgmt_start),
            CommandHandler("userinfo", user_mgmt_start),
        ],
        states={},
        fallbacks=[],
        per_user=True, per_chat=True
    )
