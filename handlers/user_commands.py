import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import BOT_USERNAME, REFERRAL_REWARD_COINS
import database as db

logger = logging.getLogger(__name__)

async def _reply(update, text, **kwargs):
    """Reply via message or edit callback query message."""
    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.edit_message_text(text, **kwargs)
        except Exception:
            await update.callback_query.message.reply_text(text, **kwargs)
    else:
        await update.message.reply_text(text, **kwargs)

async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
    try:
        refs = await db.get_referral_count(user_id)
        coins = await db.get_coins(user_id)
    except:
        refs, coins = 0, 0
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="go_home")]])
    text = (
        f"\U0001f517 <b>Your Referral Link</b>\n\n"
        f"<code>{link}</code>\n\n"
        f"Referrals: {refs} | Coins: {coins}\n"
        f"Earn <b>{REFERRAL_REWARD_COINS} coins</b> per invite!"
    )
    await _reply(update, text, parse_mode="HTML", reply_markup=kb)

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        coins = await db.get_coins(update.effective_user.id)
    except:
        coins = 0
    await _reply(update, f"\U0001f4b0 Your balance: <b>{coins} coins</b>", parse_mode="HTML")

async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        board = await db.get_leaderboard(10)
    except:
        board = []
    if not board:
        await _reply(update, "No leaderboard data yet.")
        return
    text = "\U0001f3c6 <b>Referral Leaderboard</b>\n\n"
    medals = ["\U0001f947", "\U0001f948", "\U0001f949"]
    for i, u in enumerate(board):
        prefix = medals[i] if i < 3 else f"{i+1}."
        name = u.get("first_name", "Unknown")
        text += f"{prefix} {name} - {u.get('referral_count', 0)} refs ({u.get('coins', 0)} coins)\n"
    await _reply(update, text, parse_mode="HTML")

async def mystats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    try:
        refs = await db.get_referral_count(uid)
        coins = await db.get_coins(uid)
        rank = await db.get_user_rank(uid)
    except:
        refs, coins, rank = 0, 0, "N/A"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="go_home")]])
    text = (
        f"\U0001f4ca <b>Your Stats</b>\n\n"
        f"\U0001f465 Referrals: {refs}\n"
        f"\U0001f4b0 Coins: {coins}\n"
        f"\U0001f3c6 Rank: #{rank}"
    )
    await _reply(update, text, parse_mode="HTML", reply_markup=kb)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "\U0001f4d6 <b>Bot Commands</b>\n\n"
        "/start - Start the bot\n"
        "/referral - Get your referral link\n"
        "/balance - Check your coins\n"
        "/leaderboard - Top referrers\n"
        "/mystats - Your statistics\n"
        "/help - This help message"
    )
    await _reply(update, text, parse_mode="HTML")
