import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from config import ADMIN_IDS
import database as db

logger = logging.getLogger(__name__)

AP_GROUP_ID, AP_INTERVAL, AP_MESSAGE = range(3)


async def autoposter_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    jobs = await db.get_all_autoposter_jobs()
    text = "🤖 <b>Auto Poster</b>\n\n"
    if jobs:
        for j in jobs:
            status = "✅" if j.get("is_active") else "⏸"
            text += f"{status} Group: <code>{j['chat_id']}</code> | Every {j['interval_min']}min\n"
    else:
        text += "No auto-poster jobs configured.\n"
    text += "\nUse /addposter to create a new job.\nUse /delposter <chat_id> to remove."
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Job", callback_data="ap_add"),
         InlineKeyboardButton("📋 View Groups", callback_data="ap_groups")],
        [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]
    ])
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")


async def ap_view_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    jobs = await db.get_all_autoposter_jobs()
    if not jobs:
        await query.edit_message_text("No auto-poster groups.")
        return
    text = "📋 <b>Auto Poster Groups</b>\n\n"
    for j in jobs:
        text += (f"Chat: <code>{j['chat_id']}</code>\n"
                 f"Interval: {j['interval_min']} min\n"
                 f"Active: {'Yes' if j.get('is_active') else 'No'}\n\n")
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Auto Poster", callback_data="adm_autoposter")]
    ])
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")


async def add_poster_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        return ConversationHandler.END
    await update.message.reply_text("Send the <b>group/channel chat ID</b>:", parse_mode="HTML")
    return AP_GROUP_ID


async def ap_group_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Invalid chat ID. Send a number:")
        return AP_GROUP_ID
    context.user_data["ap_chat_id"] = chat_id
    await update.message.reply_text("Send the <b>interval in minutes</b> (e.g. 60):", parse_mode="HTML")
    return AP_INTERVAL


async def ap_interval_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        interval = int(update.message.text.strip())
        if interval < 1:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Invalid interval. Send a positive number:")
        return AP_INTERVAL
    context.user_data["ap_interval"] = interval
    await update.message.reply_text("Send the <b>message to auto-post</b> (HTML supported):", parse_mode="HTML")
    return AP_MESSAGE


async def ap_message_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.user_data.pop("ap_chat_id")
    interval = context.user_data.pop("ap_interval")
    message = update.message.text
    await db.save_autoposter_job(chat_id, interval, message)
    await update.message.reply_text(
        f"✅ Auto-poster job created!\n"
        f"Chat: <code>{chat_id}</code>\n"
        f"Interval: {interval} min",
        parse_mode="HTML"
    )
    return ConversationHandler.END


async def cancel_poster(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


async def del_poster(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text("Usage: /delposter <chat_id>")
        return
    try:
        chat_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid chat ID.")
        return
    ok = await db.delete_autoposter_job(chat_id)
    if ok:
        await update.message.reply_text(f"✅ Auto-poster for {chat_id} removed.")
    else:
        await update.message.reply_text("❌ Job not found.")


def get_autoposter_conv_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("addposter", add_poster_start)],
        states={
            AP_GROUP_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, ap_group_received)],
            AP_INTERVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ap_interval_received)],
            AP_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ap_message_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel_poster)],
    )


async def run_autoposter(app):
    while True:
        try:
            jobs = await db.get_all_autoposter_jobs()
            for job in jobs:
                if not job.get("is_active"):
                    continue
                try:
                    await app.bot.send_message(
                        chat_id=job["chat_id"],
                        text=job["message"],
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logger.error(f"Autoposter error for {job['chat_id']}: {e}")
        except Exception as e:
            logger.error(f"Autoposter loop error: {e}")
        await asyncio.sleep(60)
