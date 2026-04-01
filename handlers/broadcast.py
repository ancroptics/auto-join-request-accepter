import logging
import time
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from telegram.error import Forbidden, BadRequest, RetryAfter
from config import ADMIN_IDS, BROADCAST_RATE_LIMIT
import database as db

logger = logging.getLogger(__name__)
CONTENT, CONFIRM = range(2)

async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return ConversationHandler.END
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "<b>Broadcast</b>\n\nSend me the message to broadcast (text, photo, video, or document).\n\nSend /cancel to abort.",
        parse_mode="HTML"
    )
    return CONTENT

async def broadcast_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["broadcast_message"] = update.message
    users = await db.get_all_active_users()
    count = len(users)
    est_time = count / BROADCAST_RATE_LIMIT
    buttons = [
        [InlineKeyboardButton("SEND NOW", callback_data="bc_confirm"),
         InlineKeyboardButton("Cancel", callback_data="bc_cancel")]
    ]
    await update.message.reply_text(
        f"<b>Broadcast Preview</b>\n\nTarget: {count:,} users\nEst. time: {est_time:.0f}s\n\nReady to send?",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons)
    )
    return CONFIRM

async def broadcast_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("Broadcasting...")
    msg = context.user_data.get("broadcast_message")
    users = await db.get_all_active_users()
    sent, failed, blocked = 0, 0, 0
    start_time = time.time()
    for i, row in enumerate(users):
        uid = row["user_id"]
        try:
            await msg.copy(chat_id=uid)
            sent += 1
            await db.increment_broadcasts_received(uid)
        except Forbidden:
            blocked += 1
            await db.ban_user(uid)
        except BadRequest:
            failed += 1
        except RetryAfter as e:
            await asyncio.sleep(e.retry_after)
            try:
                await msg.copy(chat_id=uid)
                sent += 1
            except Exception:
                failed += 1
        except Exception:
            failed += 1
        if (i + 1) % 100 == 0:
            try:
                await update.callback_query.edit_message_text(
                    f"Broadcasting... {i+1}/{len(users)}\n{sent} | {failed} | {blocked}"
                )
            except Exception:
                pass
        await asyncio.sleep(1 / BROADCAST_RATE_LIMIT)
    duration = time.time() - start_time
    await db.log_broadcast(update.effective_user.id, len(users), sent, failed, blocked, duration)
    speed = sent / max(duration, 1)
    await update.callback_query.edit_message_text(
        f"<b>Broadcast Complete</b>\n\nSent: {sent:,}\nFailed: {failed:,}\nBlocked: {blocked:,}\nDuration: {duration:.0f}s\nSpeed: {speed:.1f} msg/sec",
        parse_mode="HTML"
    )
    return ConversationHandler.END

async def broadcast_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Broadcast cancelled.")
    else:
        await update.message.reply_text("Broadcast cancelled.")
    return ConversationHandler.END

def get_broadcast_handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(broadcast_start, pattern="^adm_broadcast$")],
        states={
            CONTENT: [MessageHandler(filters.ALL & ~filters.COMMAND, broadcast_content)],
            CONFIRM: [
                CallbackQueryHandler(broadcast_confirm, pattern="^bc_confirm$"),
                CallbackQueryHandler(broadcast_cancel, pattern="^bc_cancel$"),
            ],
        },
        fallbacks=[MessageHandler(filters.Regex("^/cancel$"), broadcast_cancel)],
        per_message=False,
    )
