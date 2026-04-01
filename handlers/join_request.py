import logging
import asyncio
from telegram import Update, ChatJoinRequest
from telegram.ext import ContextTypes
from config import ADMIN_IDS, AUTO_APPROVE_ENABLED, WELCOME_DM_ENABLED, BOT_USERNAME
import database as db

logger = logging.getLogger(__name__)

DEFAULT_WELCOME = (
    "Hey {first_name}! \n\n"
    "Welcome to <b>{channel_name}</b>! \n\n"
    "You've been approved to join our community.\n\n"
    "Want to earn rewards? Share your referral link:\n"
    "<code>{referral_link}</code>\n\n"
    "You'll earn coins for every friend who joins!\n\n"
    "Current Balance: {coins} coins"
)

async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    join_request: ChatJoinRequest = update.chat_join_request
    user = join_request.from_user
    chat = join_request.chat
    try:
        if AUTO_APPROVE_ENABLED:
            await join_request.approve()
            logger.info(f"Approved: {user.first_name} ({user.id}) for {chat.title}")
        await db.upsert_user(
            user_id=user.id, username=user.username,
            first_name=user.first_name, last_name=user.last_name,
            source="join_request", created_via="join_request"
        )
        await db.log_join_request(user.id, chat.id, chat.title, "approved", True)
        await db.upsert_channel(chat.id, chat.title)
        if WELCOME_DM_ENABLED:
            await asyncio.sleep(0.5)
            channel_cfg = await db.get_channel_config(chat.id)
            welcome_msg = (channel_cfg["welcome_message"] if channel_cfg and channel_cfg["welcome_message"] else DEFAULT_WELCOME)
            user_data = await db.get_user(user.id)
            coins = user_data["coins"] if user_data else 0
            ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user.id}"
            text = welcome_msg.format(
                first_name=user.first_name or "there",
                username=f"@{user.username}" if user.username else "N/A",
                user_id=user.id, referral_link=ref_link,
                channel_name=chat.title or "the channel", coins=coins
            )
            try:
                msg = await context.bot.send_message(chat_id=user.id, text=text, parse_mode="HTML")
                await db.mark_dm_sent(user.id, chat.id, msg.message_id)
            except Exception as e:
                logger.warning(f"Could not DM {user.id}: {e}")
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"<b>Join Request Approved</b>\n{user.first_name} (ID: <code>{user.id}</code>)\n{chat.title}",
                    parse_mode="HTML"
                )
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Error handling join request from {user.id}: {e}")
