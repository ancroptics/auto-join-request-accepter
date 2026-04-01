import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from config import ADMIN_IDS
import database as db

logger = logging.getLogger(__name__)

AP_CHAT, AP_INTERVAL, AP_MESSAGE = range(3)

async def add_poster_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return ConversationHandler.END
    await update.message.reply_text("\U0001f916 <b>Add Auto-Poster</b>\n\nSend the chat ID to post to:", parse_mode="HTML")
    return AP_CHAT

async def ap_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = int(update.message.text.strip())
        context.user_data["ap_chat_id"] = chat_id
        await update.message.reply_text("Send the interval in minutes (e.g., 60):")
        return AP_INTERVAL
    except ValueError:
        await update.message.reply_text("Invalid chat ID. Send a number or /cancel:")
        return AP_CHAT

async def ap_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        mins = int(update.message.text.strip())
        if mins < 1:
            raise ValueError
        context.user_data["ap_interval"] = mins
        await update.message.reply_text("Send the message to auto-post:")
        return AP_MESSAGE
    except ValueError:
        await update.message.reply_text("Invalid interval. Send a positive number or /cancel:")
        return AP_INTERVAL

async def ap_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.user_data["ap_chat_id"]
    interval = context.user_data["ap_interval"]
    message = update.message.text
    try:
        await db.save_autoposter_job(chat_id, interval, message)
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Admin Panel", callback_data="admin_panel")]])
        await update.message.reply_text(
            f"\u2705 Auto-poster created!\nChat: {chat_id}\nInterval: {interval}min",
            reply_markup=kb
        )
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")
    return ConversationHandler.END

async def ap_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END

async def del_poster(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    args = update.message.text.split(maxsplit=1)
    if len(args) < 2:
        await update.message.reply_text("Usage: /delposter <chat_id>")
        return
    try:
        chat_id = int(args[1])
        ok = await db.delete_autoposter_job(chat_id)
        if ok:
            await update.message.reply_text(f"\u2705 Auto-poster for {chat_id} deleted.")
        else:
            await update.message.reply_text("Job not found.")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

def get_autoposter_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("addposter", add_poster_start)],
        states={
            AP_CHAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ap_chat)],
            AP_INTERVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ap_interval)],
            AP_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ap_message)],
        },
        fallbacks=[CommandHandler("cancel", ap_cancel)],
        per_user=True, per_chat=True
    )
