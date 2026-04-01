import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import ADMIN_IDS
import database as db
import asyncio

logger = logging.getLogger(__name__)

BROADCAST_MSG = 0

async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return ConversationHandler.END
    target = "all"
    if update.callback_query:
        data = update.callback_query.data
        if data == "broadcast_new":
            target = "new"
        elif data == "broadcast_active":
            target = "active"
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            f"\U0001f4e2 <b>Broadcast to: {target}</b>\n\nSend the message to broadcast.\nUse /cancel to abort.",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            "\U0001f4e2 <b>Broadcast</b>\n\nSend the message to broadcast to all users.\nUse /cancel to abort.",
            parse_mode="HTML"
        )
    context.user_data["broadcast_target"] = target
    return BROADCAST_MSG

async def broadcast_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return ConversationHandler.END
    message = update.message
    target = context.user_data.get("broadcast_target", "all")

    try:
        if target == "new":
            user_ids = await db.get_new_user_ids(7)
        elif target == "active":
            user_ids = await db.get_active_user_ids(30)
        else:
            user_ids = await db.get_all_user_ids()
    except Exception as e:
        await message.reply_text(f"Error getting users: {e}")
        return ConversationHandler.END

    total = len(user_ids)
    progress = await message.reply_text(f"\U0001f4e4 Broadcasting to {total} users...")

    sent, failed, blocked = 0, 0, 0
    for i, uid in enumerate(user_ids):
        try:
            await message.copy(chat_id=uid)
            sent += 1
        except Exception as e:
            err = str(e).lower()
            if "blocked" in err or "deactivated" in err:
                blocked += 1
            else:
                failed += 1
        if (i + 1) % 25 == 0:
            await asyncio.sleep(1)
            try:
                await progress.edit_text(f"\U0001f4e4 Progress: {i+1}/{total} (sent: {sent})")
            except:
                pass

    try:
        await db.log_broadcast(update.effective_user.id, total, sent, failed, blocked)
    except:
        pass

    kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Admin Panel", callback_data="admin_panel")]])
    await progress.edit_text(
        f"\u2705 <b>Broadcast Complete</b>\n\n"
        f"Target: {target}\n"
        f"Total: {total}\n"
        f"\u2705 Sent: {sent}\n"
        f"\u274c Failed: {failed}\n"
        f"\U0001f6ab Blocked: {blocked}",
        parse_mode="HTML", reply_markup=kb
    )
    return ConversationHandler.END

async def broadcast_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Admin Panel", callback_data="admin_panel")]])
    await update.message.reply_text("Broadcast cancelled.", reply_markup=kb)
    return ConversationHandler.END

def get_broadcast_handler():
    return ConversationHandler(
        entry_points=[
            CommandHandler("broadcast", broadcast_start),
            CallbackQueryHandler(broadcast_start, pattern="^broadcast_(all|new|active)$")
        ],
        states={
            BROADCAST_MSG: [MessageHandler(filters.ALL & ~filters.COMMAND, broadcast_receive)]
        },
        fallbacks=[CommandHandler("cancel", broadcast_cancel)],
        per_user=True, per_chat=True
    )
