import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import BOT_USERNAME, REFERRAL_REWARD_COINS

logger = logging.getLogger(__name__)

async def _get_db():
    try:
        import database as db
        if db.pool:
            return db
    except Exception:
        pass
    return None

async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user.id}"
    db = await _get_db()
    if db:
        try:
            data = await db.get_user(user.id)
            if not data:
                await db.upsert_user(user.id, user.username, user.first_name, user.last_name)
                data = await db.get_user(user.id)
            tier = data["tier"]
            refs = data["referral_count"]
            coins = data["coins"]
            next_tier, needed = "", 0
            if refs < 5: next_tier, needed = "Silver", 5 - refs
            elif refs < 25: next_tier, needed = "Gold", 25 - refs
            elif refs < 100: next_tier, needed = "Diamond", 100 - refs
            elif refs < 500: next_tier, needed = "Legend", 500 - refs
            else: next_tier, needed = "MAX", 0
            progress = min(refs / max(needed + refs, 1) * 10, 10)
            bar_full = "" * int(progress)
            bar_empty = "" * (10 - int(progress))
            bar = bar_full + bar_empty
            next_info = f"{needed} more for {next_tier}" if needed > 0 else "Max tier reached!"
            await update.message.reply_text(
                f"<b>Your Referral Dashboard</b>\n\n"
                f"Tier: {tier}\n"
                f"[{bar}] {refs} referrals\n"
                f"{next_info}\n\n"
                f"Coins: {coins}\nTotal Referrals: {refs}\n\n"
                f"<b>Your link:</b>\n<code>{ref_link}</code>\n\n"
                f"Share it to earn {REFERRAL_REWARD_COINS} coins per join!",
                parse_mode="HTML"
            )
            return
        except Exception as e:
            logger.error(f"DB error in referral_command: {e}")
    await update.message.reply_text(
        f"<b>Your Referral Link:</b>\n<code>{ref_link}</code>\n\n"
        f"Share it to earn {REFERRAL_REWARD_COINS} coins per join!\n\n"
        f"Database temporarily unavailable - stats will show when reconnected.",
        parse_mode="HTML"
    )

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db = await _get_db()
    if db:
        try:
            data = await db.get_user(user.id)
            coins = data["coins"] if data else 0
            tier = data["tier"] if data else "Bronze"
            await update.message.reply_text(
                f"<b>Your Balance</b>\n\n"
                f"Tier: {tier}\n"
                f"Coins: {coins}",
                parse_mode="HTML"
            )
            return
        except Exception as e:
            logger.error(f"DB error in balance_command: {e}")
    await update.message.reply_text("Database temporarily unavailable. Try again later.")

async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = await _get_db()
    if db:
        try:
            rows = await db.get_leaderboard(10)
            if not rows:
                await update.message.reply_text("No referrals yet! Be the first.")
                return
            lines = []
            medals = ["", "", ""]
            for i, r in enumerate(rows):
                medal = medals[i] if i < 3 else f"{i+1}."
                name = r["first_name"] or r["username"] or str(r["user_id"])
                lines.append(f"{medal} {name} {r['referral_count']} refs ({r['coins']} coins)")
            text = "<b>Referral Leaderboard</b>\n\n" + "\n".join(lines)
            await update.message.reply_text(text, parse_mode="HTML")
            return
        except Exception as e:
            logger.error(f"DB error in leaderboard_command: {e}")
    await update.message.reply_text("Database temporarily unavailable. Try again later.")

async def mystats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db = await _get_db()
    if db:
        try:
            data = await db.get_user(user.id)
            if data:
                joined = str(data['joined_at'])[:10]
                await update.message.reply_text(
                    f"<b>Your Stats</b>\n\n"
                    f"Tier: {data['tier']}\n"
                    f"Referrals: {data['referral_count']}\n"
                    f"Coins: {data['coins']}\n"
                    f"Joined: {joined}\n"
                    f"Broadcasts received: {data['broadcasts_received']}",
                    parse_mode="HTML"
                )
                return
            await update.message.reply_text("Send /start first to register!")
            return
        except Exception as e:
            logger.error(f"DB error in mystats_command: {e}")
    await update.message.reply_text("Database temporarily unavailable. Try again later.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "<b>Bot Commands</b>\n\n"
        "/start - Start the bot\n"
        "/referral - Your referral dashboard\n"
        "/balance - Check your coins\n"
        "/leaderboard - Top referrers\n"
        "/mystats - Your statistics\n"
        "/help - This message",
        parse_mode="HTML"
    )
