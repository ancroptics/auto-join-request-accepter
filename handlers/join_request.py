import logging
from telegram import Update
from telegram.ext import ContextTypes
import database as db

logger = logging.getLogger(__name__)

async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    request = update.chat_join_request
    user = request.from_user
    chat = request.chat

    logger.info(f"Join request from {user.id} ({user.first_name}) for {chat.title}")

    try:
        await db.upsert_user(user.id, user.username, user.first_name)
        await db.upsert_channel(chat.id, chat.title)
    except Exception as e:
        logger.error(f"DB error saving join request: {e}")

    # Check settings
    try:
        settings = await db.get_bot_settings()
        auto_approve = settings.get("auto_approve", True)
        welcome_dm = settings.get("welcome_dm", True)
    except:
        auto_approve = True
        welcome_dm = True

    # Check channel-specific config
    ch_config = None
    try:
        ch_config = await db.get_channel_config(chat.id)
        if ch_config and not ch_config.get("auto_approve", True):
            auto_approve = False
    except:
        pass

    if auto_approve:
        try:
            await request.approve()
            logger.info(f"Approved {user.id} for {chat.title}")
        except Exception as e:
            logger.error(f"Failed to approve {user.id}: {e}")

    # Log the request
    try:
        dm_sent = False
        await db.log_join_request(user.id, chat.id, chat.title, "approved" if auto_approve else "pending", dm_sent=False)
    except Exception as e:
        logger.error(f"Failed to log join request: {e}")

    # Send welcome DM
    if welcome_dm:
        try:
            welcome_text = None
            if ch_config and ch_config.get("welcome_message"):
                welcome_text = ch_config["welcome_message"]

            if not welcome_text:
                welcome_text = (
                    f"\U0001f44b <b>Welcome, {user.first_name}!</b>\n\n"
                    f"You've been approved to join <b>{chat.title}</b>!\n\n"
                    f"Enjoy your stay! \U0001f389"
                )

            await context.bot.send_message(
                chat_id=user.id, text=welcome_text, parse_mode="HTML"
            )
            dm_sent = True
            await db.mark_dm_sent(user.id, chat.id)
            logger.info(f"Welcome DM sent to {user.id}")
        except Exception as e:
            logger.warning(f"Could not DM {user.id}: {e}")
