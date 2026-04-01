import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import BOT_USERNAME, REFERRAL_REWARD_COINS
import database as db

logger = logging.getLogger(__name__)

async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = await db.get_user(user.id)
    if not data:
        await db.upsert_user(user.id, user.username, user.first_name, user.last_name)
        data = await db.get_user(user.id)
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user.id}"
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
    bar = "\u2593" * int(progress) + "\u2591" * (10 - int(progress))
    await update.message.reply_text(
        f"\ud83d\udd17 <b>Your Referral Dashboard</b>\n\n"
        f"\ud83c\udfc5 Tier: {tier}\n"
        f"[{bar}] {refs} referrals\n"
        f"{'\ud83d\udcc8 ' + str(needed) + ' more for ' + next_tier if needed > 0 else '\ud83c\udf89 Max tier reached!'}\n\n"
        f"\ud83d\udcb0 Coins: {coins}\n\ud83d\udc65 Total Referrals: {refs}\n\n"
        f"\ud83d\udd17 <b>Your link:</b>\n<code>{ref_link}</code>\n\n"
        f"Share it to earn {REFERRAL_REWARD_COINS} coins per join!",
        parse_mode="HTML"
    )

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = await db.get_user(user.id)
    coins = data["coins"] if data else 0
    tier = data["tier"] if data else "\ud83e\udd49 Bronze"
    await update.message.reply_text(
        f"\ud83d\udcb0 <b>Your Balance</b>\n\n\ud83c\udfc5 Tier: {tier}\n\ud83d\udcb0 Coins: {coins}",
        parse_mode="HTML"
    )

async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    leaders = await db.get_leaderboard(10)
    if not leaders:
        await update.message.reply_text("\ud83d\udcca No referrals yet!")
        return
    medals = ["\ud83e\udd47", "\ud83e\udd48", "\ud83e\udd49"] + ["\ud83c\udfc5"] * 7
    lines = []
    for i, row in enumerate(leaders):
        name = row["first_name"] or row["username"] or "Unknown"
        lines.append(f"{medals[i]} <b>{name}</b> \u2014 {row['referral_count']} referrals ({row['coins']} coins)")
    await update.message.reply_text(
        f"\ud83c\udfc6 <b>Top Referrers</b>\n\n" + "\n".join(lines), parse_mode="HTML"
    )

async def mystats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = await db.get_user(user.id)
    if not data:
        await update.message.reply_text("No data yet! Use /start first.")
        return
    await update.message.reply_text(
        f"\ud83d\udcca <b>Your Stats</b>\n\n"
        f"\ud83d\udc64 {data['first_name']}\n\ud83c\udfc5 Tier: {data['tier']}\n"
        f"\ud83d\udcb0 Coins: {data['coins']}\n\ud83d\udc65 Referrals: {data['referral_count']}\n"
        f"\ud83d\udce8 Broadcasts received: {data['broadcasts_received']}\n"
        f"\ud83d\udcc5 Joined: {data['joined_at'].strftime('%Y-%m-%d') if data['joined_at'] else 'N/A'}",
        parse_mode="HTML"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "\ud83d\udcd6 <b>Bot Commands</b>\n\n"
        "/start \u2014 Start the bot\n/referral \u2014 Get your referral link\n"
        "/balance \u2014 Check your coins\n/leaderboard \u2014 Top referrers\n"
        "/mystats \u2014 Your statistics\n/help \u2014 This message\n\n"
        "<b>How it works:</b>\nAdd me as admin to your group/channel with invite permission. "
        "I auto-approve all join requests and DM new members!",
        parse_mode="HTML"
    )
