import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import ADMIN_IDS
import database as db

logger = logging.getLogger(__name__)

TEMPLATE_NAME, TEMPLATE_CONTENT = range(2)


async def templates_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    templates = await db.get_all_templates()
    text = "\U0001f4dd <b>Message Templates</b>\n\n"
    if templates:
        for i, t in enumerate(templates, 1):
            text += f"{i}. <b>{t['name']}</b>\n"
    else:
        text += "No templates yet.\n"
    text += "\nUse /addtemplate to create a new template.\nUse /deltemplate <name> to delete."
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("\u2795 Add Template", callback_data="tpl_add")],
        [InlineKeyboardButton("\U0001f519 Admin Panel", callback_data="admin_panel")]
    ])
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")


async def add_template_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        return ConversationHandler.END
    await update.message.reply_text("Send the <b>template name</b>:", parse_mode="HTML")
    return TEMPLATE_NAME


async def template_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["tpl_name"] = update.message.text.strip()
    await update.message.reply_text(
        "Now send the <b>template content</b> (HTML supported).\n"
        "Placeholders: {first_name}, {user_id}, {username}",
        parse_mode="HTML"
    )
    return TEMPLATE_CONTENT


async def template_content_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = context.user_data.pop("tpl_name", "unnamed")
    content = update.message.text
    await db.save_template(name, content)
    await update.message.reply_text(f"\u2705 Template <b>{name}</b> saved!", parse_mode="HTML")
    return ConversationHandler.END


async def cancel_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


async def del_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        return
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /deltemplate <name>")
        return
    name = " ".join(args)
    ok = await db.delete_template(name)
    if ok:
        await update.message.reply_text(f"\u2705 Template '{name}' deleted.")
    else:
        await update.message.reply_text(f"\u274c Template '{name}' not found.")


def get_template_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("addtemplate", add_template_start)],
        states={
            TEMPLATE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, template_name_received)],
            TEMPLATE_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, template_content_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel_template)],
    )
