import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import ADMIN_IDS, BOT_USERNAME, REFERRAL_REWARD_COINS

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    referrer_id = None
    source = "organic"
    if args and args[0].startswith("ref_"):
        try:
            referrer_id = int(args[0][4:])
            source = "referral"
        except ValueError:
            pass

    try:
        import database as db
        if db.pool:
            existing = await db.get_user(user.id)
            if not existing:
                await db.add_user(
                    user_id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    source=source,
                    referrer_id=referrer_id
                )
                if referrer_id:
                    await db.add_referral(referrer_id, user.id)
                    await db.add_coins(referrer_id, REFERRAL_REWARD_COINS)
                    try:
                        await context.bot.send_message(
                            chat_id=referrer_id,
                            text=f"\U0001f389 <b>{user.first_name}</b> joined via your link! +{REFERRAL_REWARD_COINS} coins",
                            parse_mode="HTML"
                        )
                    except Exception:
                        pass
    except Exception as e:
        logger.error(f"DB error in start_command: {e}")

    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user.id}"
    buttons = []
    if user.id in ADMIN_IDS:
        buttons.append([InlineKeyboardButton("\u2699\ufe0f Admin Panel", callback_data="admin_panel")])
    buttons.append([InlineKeyboardButton("\U0001f517 My Referral Link", callback_data="my_referral")])
    buttons.append([InlineKeyboardButton("\U0001f4ca My Stats", callback_data="my_stats")])
    await update.message.reply_text(
        f"\U0001f916 <b>Welcome, {user.first_name}!</b>\n\n"
        f"I automatically approve join requests for groups and channels.\n\n"
        f"<b>How to use:</b>\n"
        f"1\ufe0f\u20e3 Add me to your group/channel as admin\n"
        f"2\ufe0f\u20e3 Give me permission to invite users\n"
        f"3\ufe0f\u20e3 Enable join requests\n"
        f"4\ufe0f\u20e3 I auto-approve all join requests!\n\n"
        f"\U0001f381 <b>Earn rewards!</b> Share your referral link:\n"
        f"<code>{ref_link}</code>\n\n"
        f"Commands: /referral /balance /leaderboard /mystats /help",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
