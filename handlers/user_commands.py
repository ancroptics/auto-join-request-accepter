import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import BOT_USERNAME, REFERRAL_REWARD_COINS

logger = logging.getLogger(__name__)

async def _get_db():
    try:
        import database as db
        return db if db.pool else None
    except Exception:
        return None

async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user.id}"
    db = await _get_db()
    referral_count = 0
    coins = 0
    if db:
        try:
            referral_count = await db.get_referral_count(user.id)
            coins = await db.get_coins(user.id)
        except Exception as e:
            logger.error(f"DB error: {e}")
    await update.message.reply_text(
        f"<b>Your Referral Link</b>\n\n"
        f"<code>{ref_link}</code>\n\n"
        f"Share this link to earn {REFERRAL_REWARD_COINS} coins per referral!\n\n"
        f"<b>Your Stats:</b>\n"
        f"Referrals: {referral_count}\n"
        f"Coins: {coins}",
        parse_mode="HTML"
    )

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db = await _get_db()
    coins = 0
    if db:
        try:
            coins = await db.get_coins(user.id)
        except Exception as e:
            logger.error(f"DB error: {e}")
    await update.message.reply_text(
        f"<b>Your Balance</b>\n\nCoins: {coins}\n\nEarn more by sharing your referral link!\nUse /referral to get your link.",
        parse_mode="HTML"
    )

async def mystats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db = await _get_db()
    stats = {"referrals": 0, "coins": 0, "rank": "N/A"}
    if db:
        try:
            stats["referrals"] = await db.get_referral_count(user.id)
            stats["coins"] = await db.get_coins(user.id)
            stats["rank"] = await db.get_user_rank(user.id)
        except Exception as e:
            logger.error(f"DB error: {e}")
    await update.message.reply_text(
        f"<b>Your Stats</b>\n\nReferrals: {stats['referrals']}\nCoins: {stats['coins']}\nRank: #{stats['rank']}\n\nKeep sharing to climb the leaderboard!",
        parse_mode="HTML"
    )

async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = await _get_db()
    text = "<b>Leaderboard - Top Referrers</b>\n\n"
    if db:
        try:
            top_users = await db.get_leaderboard(10)
            if top_users:
                for i, row in enumerate(top_users):
                    name = row.get('first_name', 'Unknown')
                    refs = row.get('referral_count', 0)
                    text += f"{i+1}. {name} - {refs} referrals\n"
            else:
                text += "No referrals yet. Be the first!\n"
        except Exception as e:
            logger.error(f"DB error: {e}")
            text += "Could not load leaderboard.\n"
    else:
        text += "Database not available.\n"
    text += "\nUse /referral to get your link!"
    await update.message.reply_text(text, parse_mode="HTML")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "<b>Bot Commands</b>\n\n/start - Start the bot\n/referral - Get your referral link\n/balance - Check your coin balance\n/mystats - View your statistics\n/leaderboard - Top referrers\n/help - Show this help\n\n<b>How it works:</b>\n1. Add me to your group/channel as admin\n2. Enable join requests\n3. I auto-approve all join requests!\n\nShare your referral link to earn coins!",
        parse_mode="HTML"
    )
