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
            if refs < 5: next_tier, needed = "\ud83e\udd48 Silver", 5 - refs
            elif refs < 25: next_tier, needed = "\ud83e\udd47 Gold", 25 - refs
            elif refs < 100: next_tier, needed = "\ud83d\udc8e Diamond", 100 - refs
            elif refs < 500: next_tier, needed = "\ud83d\udc51 Legend", 500 - refs
            else: next_tier, needed = "\ud83d\udc51 MAX", 0
            progress = min(refs / max(needed + refs, 1) * 10, 10)
            bar_full = "\u2593" * int(progress)
            bar_empty = "\u2591" * (10 - int(progress))
            bar = bar_full + bar_empty
            next_info = f"\ud83d\udcc8 {needed} more for {next_tier}" if needed > 0 else "\ud83c\udf89 Max tier reached!"
            await update.message.reply_text(
                f"\ud83d\udd17 <b>Your Referral Dashboard</b>\n\n"
                f"\ud83c\udfc5 Tier: {tier}\n"
                f"[{bar}] {refs} referrals\n"
                f"{next_info}\n\n"
                f"\ud83d\udcb0 Coins: {coins}\n\ud83d\udc65 Total Referrals: {refs}\n\n"
                f"\ud83d\udd17 <b>Your link:</b>\n<code>{ref_link}</code>\n\n"
                f"Share it to earn {REFERRAL_REWARD_COINS} coins per join!",
                parse_mode="HTML"
            )
            return
        except Exception as e:
            logger.error(f"DB error in referral_command: {e}")
    await update.message.reply_text(
        f"\ud83d\udd17 <b>Your Referral Link:</b>\n<code>{ref_link}</code>\n\n"
        f"Share it to earn {REFERRAL_REWARD_COINS} coins per join!\n\n"
        f"\u26a0\ufe0f Database temporarily unavailable - stats will show when reconnected.",
        parse_mode="HTML"
    )

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db = await _get_db()
    if db:
        try:
            data = await db.get_user(user.id)
            coins = data["coins"] if data else 0
            tier = data["tier"] if data else "\ud83e\udd49 Bronze"
            await update.message.reply_text(
                f"\ud83d\udcb0 <b>Your Balance</b>\n\n"
                f"\ud83c\udfc5 Tier: {tier}\n"
                f"\ud83e\ude99 Coins: {coins}",
                parse_mode="HTML"
            )
            return
        except Exception as e:
            logger.error(f"DB error in balance_command: {e}")
    await update.message.reply_text("\u26a0\ufe0f Database temporarily unavailable. Try again later.")

async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = await _get_db()
    if db:
        try:
            rows = await db.get_leaderboard(10)
            if not rows:
                await update.message.reply_text("\ud83c\udfc6 No referrals yet! Be the first.")
                return
            lines = []
            medals = ["\ud83e\udd47", "\ud83e\udd48", "\ud83e\udd49"]
            for i, r in enumerate(rows):
                medal = medals[i] if i < 3 else f"{i+1}."
                name = r["first_name"] or r["username"] or str(r["user_id"])
                lines.append(f"{medal} {name} \u2014 {r['referral_count']} refs ({r['coins']} coins)")
            text = "\ud83c\udfc6 <b>Referral Leaderboard</b>\n\n" + "\n".join(lines)
            await update.message.reply_text(text, parse_mode="HTML")
            return
        except Exception as e:
            logger.error(f"DB error in leaderboard_command: {e}")
    await update.message.reply_text("\u26a0\ufe0f Database temporarily unavailable. Try again later.")

async def mystats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db = await _get_db()
    if db:
        try:
            data = await db.get_user(user.id)
            if data:
                joined = str(data['joined_at'])[:10]
                await update.message.reply_text(
                    f"\ud83d\udcca <b>Your Stats</b>\n\n"
                    f"\ud83c\udfc5 Tier: {data['tier']}\n"
                    f"\ud83d\udc65 Referrals: {data['referral_count']}\n"
                    f"\ud83e\ude99 Coins: {data['coins']}\n"
                    f"\ud83d\udcc5 Joined: {joined}\n"
                    f"\ud83d\udce8 Broadcasts received: {data['broadcasts_received']}",
                    parse_mode="HTML"
                )
                return
            await update.message.reply_text("Send /start first to register!")
            return
        except Exception as e:
            logger.error(f"DB error in mystats_command: {e}")
    await update.message.reply_text("\u26a0\ufe0f Database temporarily unavailable. Try again later.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "\ud83e\udd16 <b>Bot Commands</b>\n\n"
        "/start - Start the bot\n"
        "/referral - Your referral dashboard\n"
        "/balance - Check your coins\n"
        "/leaderboard - Top referrers\n"
        "/mystats - Your statistics\n"
        "/help - This message",
        parse_mode="HTML"
    )
