import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import ADMIN_IDS, BOT_USERNAME, REFERRAL_REWARD_COINS

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    referrer_id = None
    if context.args and context.args[0].startswith("ref_"):
        try:
            referrer_id = int(context.args[0][4:])
            if referrer_id == user.id:
                referrer_id = None
        except ValueError:
            pass
    try:
        import database as db
        if db.pool:
            existing = await db.get_user(user.id)
            await db.upsert_user(
                user_id=user.id, username=user.username,
                first_name=user.first_name, referrer_id=referrer_id if not existing else None
            )
            if referrer_id and not existing:
                await db.increment_referral(referrer_id)
                await db.add_coins(referrer_id, REFERRAL_REWARD_COINS)
                try:
                    await context.bot.send_message(
                        chat_id=referrer_id,
                        text=f"\U0001f389 <b>New Referral!</b>\n\n{user.first_name} joined via your link!\n+{REFERRAL_REWARD_COINS} coins earned!",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass
    except Exception as e:
        logger.error(f"DB error in start: {e}")
    buttons = [
        [InlineKeyboardButton("\U0001f517 My Referral Link", callback_data="my_referral"),
         InlineKeyboardButton("\U0001f4ca My Stats", callback_data="my_stats")],
        [InlineKeyboardButton("\U0001f39b Control Panel", callback_data="cp_main")],
    ]
    if user.id in ADMIN_IDS:
        buttons.append([InlineKeyboardButton("\U0001f6e0 Admin Panel", callback_data="admin_panel")])
    text = (
        f"\U0001f44b <b>Welcome, {user.first_name}!</b>\n\n"
        f"I automatically approve join requests for your channels and groups.\n\n"
        f"\U0001f517 Share your referral link to earn <b>{REFERRAL_REWARD_COINS} coins</b> per invite!\n\n"
        f"Use the buttons below to get started:"
    )
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
