import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from config import ADMIN_IDS
import database as db

logger = logging.getLogger(__name__)

TEMPLATE_CONTENT = 0

async def add_template_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return ConversationHandler.END
    args = update.message.text.split(maxsplit=1)
    if len(args) < 2:
        await update.message.reply_text("Usage: /addtemplate <name>")
        return ConversationHandler.END
    context.user_data["template_name"] = args[1].strip()
    await update.message.reply_text(
        f"\U0001f4c4 Creating template: <b>{args[1].strip()}</b>\n\nSend the template content (HTML supported).\nUse /cancel to abort.",
        parse_mode="HTML"
    )
    return TEMPLATE_CONTENT

async def add_template_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = context.user_data.get("template_name", "unnamed")
    content = update.message.text
    try:
        await db.save_template(name, content)
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Admin Panel", callback_data="admin_panel")]])
        await update.message.reply_text(f"\u2705 Template '<b>{name}</b>' saved!", parse_mode="HTML", reply_markup=kb)
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")
    return ConversationHandler.END

async def template_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END

async def del_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    args = update.message.text.split(maxsplit=1)
    if len(args) < 2:
        await update.message.reply_text("Usage: /deltemplate <name>")
        return
    name = args[1].strip()
    try:
        ok = await db.delete_template(name)
        if ok:
            await update.message.reply_text(f"\u2705 Template '{name}' deleted.")
        else:
            await update.message.reply_text(f"Template '{name}' not found.")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

def get_template_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("addtemplate", add_template_start)],
        states={TEMPLATE_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_template_content)]},
        fallbacks=[CommandHandler("cancel", template_cancel)],
        per_user=True, per_chat=True
    )
