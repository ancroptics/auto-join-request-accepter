import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import ADMIN_IDS
import database as db

logger = logging.getLogger(__name__)


async def handle_my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detects when bot is added/removed from a channel."""
    my_chat_member = update.my_chat_member
    if not my_chat_member:
        return

    chat = my_chat_member.chat
    user = my_chat_member.from_user
    old_status = my_chat_member.old_chat_member.status
    new_status = my_chat_member.new_chat_member.status

    if new_status in ("administrator", "member") and old_status in ("left", "kicked"):
        logger.info(f"Bot added to {chat.type} '{chat.title}' (ID: {chat.id}) by user {user.id}")
        if db.pool:
            try:
                await db.upsert_channel(chat.id, chat.title or "Unknown", auto_approve=True)
            except Exception as e:
                logger.error(f"Failed to save channel: {e}")
        try:
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("\U0001f4cb My Channels", callback_data="cp_channels_list")],
                [InlineKeyboardButton("\U0001f465 Pending Requests", callback_data="cp_pending_all")],
                [InlineKeyboardButton("\u2699\ufe0f Settings", callback_data="cp_settings")],
            ])
            await context.bot.send_message(
                chat_id=user.id,
                text=(
                    f"\U0001f389 <b>Bot Added Successfully!</b>\n\n"
                    f"You added me to <b>{chat.title}</b>!\n\n"
                    f"\U0001f4e1 <b>Channel:</b> <code>{chat.id}</code>\n"
                    f"\U0001f464 <b>Added by:</b> {user.first_name}\n\n"
                    f"Use the control panel below to manage your channels "
                    f"and approve join requests."
                ),
                parse_mode="HTML",
                reply_markup=kb
            )
        except Exception as e:
            logger.warning(f"Could not DM user {user.id}: {e}")

    elif new_status in ("left", "kicked") and old_status in ("administrator", "member"):
        logger.info(f"Bot removed from '{chat.title}' (ID: {chat.id})")
        if db.pool:
            try:
                await db.delete_channel(chat.id)
            except Exception as e:
                logger.error(f"Failed to remove channel: {e}")
        try:
            await context.bot.send_message(
                chat_id=user.id,
                text=f"\U0001f614 <b>Bot Removed</b>\n\nI was removed from <b>{chat.title}</b>.",
                parse_mode="HTML"
            )
        except:
            pass


async def cp_channels_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not db.pool:
        await query.edit_message_text("\u26a0\ufe0f Database not connected.")
        return
    channels = await db.get_all_channels()
    if not channels:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f504 Refresh", callback_data="cp_channels_list")]])
        await query.edit_message_text("\U0001f4cb <b>My Channels</b>\n\nNo channels found. Add me as admin to a channel!", parse_mode="HTML", reply_markup=kb)
        return
    text = "\U0001f4cb <b>My Channels</b>\n\n"
    buttons = []
    for ch in channels:
        title = ch.get("chat_title", "Unknown")[:25]
        chat_id = ch["chat_id"]
        pending = await db.get_pending_count_for_channel(chat_id)
        auto = "\u2705" if ch.get("auto_approve", True) else "\u274c"
        text += f"\U0001f4e1 <b>{title}</b>\n   ID: <code>{chat_id}</code> | Auto: {auto} | Pending: {pending}\n\n"
        buttons.append([InlineKeyboardButton(f"\U0001f4e1 {title} ({pending} pending)", callback_data=f"cp_ch_{chat_id}")])
    buttons.append([InlineKeyboardButton("\U0001f504 Refresh", callback_data="cp_channels_list")])
    buttons.append([InlineKeyboardButton("\U0001f519 Control Panel", callback_data="cp_main")])
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))


async def cp_channel_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    query = update.callback_query
    await query.answer()
    channel = await db.get_channel(chat_id)
    if not channel:
        await query.edit_message_text("Channel not found.")
        return
    title = channel.get("chat_title", "Unknown")
    auto = "\u2705 ON" if channel.get("auto_approve", True) else "\u274c OFF"
    pending = await db.get_pending_count_for_channel(chat_id)
    pending_requests = await db.get_pending_requests_for_channel(chat_id, limit=50)
    text = f"\U0001f4e1 <b>{title}</b>\n\n\U0001f194 Chat ID: <code>{chat_id}</code>\n\u26a1 Auto-Approve: {auto}\n\u23f3 Pending Requests: <b>{pending}</b>\n"
    if pending_requests:
        text += "\n<b>Recent Pending:</b>\n"
        for i, req in enumerate(pending_requests[:10], 1):
            name = req.get("first_name", req.get("username", f"User {req['user_id']}"))
            text += f"  {i}. {name} (<code>{req['user_id']}</code>)\n"
        if pending > 10:
            text += f"  ... and {pending - 10} more\n"
    kb = []
    if pending > 0:
        kb.append([InlineKeyboardButton(f"\u2705 Accept ALL ({pending})", callback_data=f"cp_approve_all_{chat_id}")])
        kb.append([InlineKeyboardButton("\u2705 Accept First N", callback_data=f"cp_approve_n_{chat_id}"), InlineKeyboardButton("\U0001f3b2 Accept Random N", callback_data=f"cp_approve_rand_{chat_id}")])
    kb.append([InlineKeyboardButton(f"\u26a1 Toggle Auto-Approve ({auto})", callback_data=f"cp_toggle_{chat_id}")])
    kb.append([InlineKeyboardButton("\U0001f4cb Back to Channels", callback_data="cp_channels_list")])
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))


async def cp_approve_all(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    query = update.callback_query
    await query.answer("Approving all requests...")
    pending = await db.get_pending_requests_for_channel(chat_id, limit=9999)
    if not pending:
        await query.answer("No pending requests!", show_alert=True)
        return
    approved = 0
    failed = 0
    for req in pending:
        try:
            await context.bot.approve_chat_join_request(chat_id=chat_id, user_id=req["user_id"])
            await db.update_join_request_status(req["user_id"], chat_id, "approved")
            approved += 1
        except Exception as e:
            logger.warning(f"Failed to approve {req['user_id']}: {e}")
            await db.update_join_request_status(req["user_id"], chat_id, "failed")
            failed += 1
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f4e1 Back to Channel", callback_data=f"cp_ch_{chat_id}")]])
    await query.edit_message_text(f"\u2705 <b>Approval Complete!</b>\n\n\u2705 Approved: {approved}\n\u274c Failed: {failed}\n\U0001f4ca Total: {approved + failed}", parse_mode="HTML", reply_markup=kb)


async def cp_approve_n_ask(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    query = update.callback_query
    await query.answer()
    pending = await db.get_pending_count_for_channel(chat_id)
    options = [InlineKeyboardButton(f"{n}", callback_data=f"cp_do_approve_n_{chat_id}_{n}") for n in [5, 10, 25, 50, 100] if n <= pending]
    kb = []
    if options:
        kb.append(options[:3])
        if len(options) > 3:
            kb.append(options[3:])
    kb.append([InlineKeyboardButton("\U0001f4e1 Back", callback_data=f"cp_ch_{chat_id}")])
    await query.edit_message_text(f"\u2705 <b>Accept First N Users</b>\n\nPending: <b>{pending}</b>\nChoose how many to approve (first come, first served):", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))


async def cp_approve_rand_ask(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    query = update.callback_query
    await query.answer()
    pending = await db.get_pending_count_for_channel(chat_id)
    options = [InlineKeyboardButton(f"\U0001f3b2 {n}", callback_data=f"cp_do_approve_rand_{chat_id}_{n}") for n in [5, 10, 25, 50, 100] if n <= pending]
    kb = []
    if options:
        kb.append(options[:3])
        if len(options) > 3:
            kb.append(options[3:])
    kb.append([InlineKeyboardButton("\U0001f4e1 Back", callback_data=f"cp_ch_{chat_id}")])
    await query.edit_message_text(f"\U0001f3b2 <b>Accept Random N Users</b>\n\nPending: <b>{pending}</b>\nChoose how many random users to approve:", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))


async def cp_do_approve_n(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int, count: int):
    query = update.callback_query
    await query.answer(f"Approving first {count}...")
    pending = await db.get_pending_requests_for_channel(chat_id, limit=count)
    approved = 0
    failed = 0
    for req in pending:
        try:
            await context.bot.approve_chat_join_request(chat_id=chat_id, user_id=req["user_id"])
            await db.update_join_request_status(req["user_id"], chat_id, "approved")
            approved += 1
        except Exception as e:
            logger.warning(f"Failed to approve {req['user_id']}: {e}")
            await db.update_join_request_status(req["user_id"], chat_id, "failed")
            failed += 1
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f4e1 Back to Channel", callback_data=f"cp_ch_{chat_id}")]])
    await query.edit_message_text(f"\u2705 <b>Approved First {count}!</b>\n\n\u2705 Approved: {approved}\n\u274c Failed: {failed}", parse_mode="HTML", reply_markup=kb)


async def cp_do_approve_rand(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int, count: int):
    query = update.callback_query
    await query.answer(f"Approving {count} random...")
    all_pending = await db.get_pending_requests_for_channel(chat_id, limit=9999)
    selected = random.sample(all_pending, min(count, len(all_pending)))
    approved = 0
    failed = 0
    for req in selected:
        try:
            await context.bot.approve_chat_join_request(chat_id=chat_id, user_id=req["user_id"])
            await db.update_join_request_status(req["user_id"], chat_id, "approved")
            approved += 1
        except Exception as e:
            logger.warning(f"Failed to approve {req['user_id']}: {e}")
            await db.update_join_request_status(req["user_id"], chat_id, "failed")
            failed += 1
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f4e1 Back to Channel", callback_data=f"cp_ch_{chat_id}")]])
    await query.edit_message_text(f"\U0001f3b2 <b>Approved {count} Random Users!</b>\n\n\u2705 Approved: {approved}\n\u274c Failed: {failed}", parse_mode="HTML", reply_markup=kb)


async def cp_toggle_auto(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    query = update.callback_query
    new_val = await db.toggle_channel_auto_approve(chat_id)
    status = "ON \u2705" if new_val else "OFF \u274c"
    await query.answer(f"Auto-approve: {status}")
    await cp_channel_detail(update, context, chat_id)


async def cp_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("\U0001f4cb My Channels", callback_data="cp_channels_list")],
        [InlineKeyboardButton("\U0001f465 All Pending Requests", callback_data="cp_pending_all")],
        [InlineKeyboardButton("\u2699\ufe0f Settings", callback_data="cp_settings")],
    ])
    await query.edit_message_text("\U0001f39b <b>Control Panel</b>\n\nManage your channels, approve join requests, and configure settings.", parse_mode="HTML", reply_markup=kb)


async def cp_pending_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not db.pool:
        await query.edit_message_text("\u26a0\ufe0f Database not connected.")
        return
    channels = await db.get_all_channels()
    text = "\U0001f465 <b>Pending Requests Overview</b>\n\n"
    total_pending = 0
    buttons = []
    for ch in channels:
        chat_id = ch["chat_id"]
        title = ch.get("chat_title", "Unknown")[:25]
        pending = await db.get_pending_count_for_channel(chat_id)
        total_pending += pending
        text += f"\U0001f4e1 <b>{title}</b>: {pending} pending\n"
        if pending > 0:
            buttons.append([InlineKeyboardButton(f"\u2705 Approve {title} ({pending})", callback_data=f"cp_ch_{chat_id}")])
    text += f"\n\U0001f4ca <b>Total Pending: {total_pending}</b>"
    buttons.append([InlineKeyboardButton("\U0001f504 Refresh", callback_data="cp_pending_all")])
    buttons.append([InlineKeyboardButton("\U0001f519 Control Panel", callback_data="cp_main")])
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))


async def cp_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    settings = await db.get_bot_settings() if db.pool else {}
    auto = "\u2705 ON" if settings.get("auto_approve", True) else "\u274c OFF"
    welcome = "\u2705 ON" if settings.get("welcome_dm", True) else "\u274c OFF"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"\u26a1 Auto-Approve: {auto}", callback_data="cp_toggle_global_auto")],
        [InlineKeyboardButton(f"\U0001f4ac Welcome DM: {welcome}", callback_data="cp_toggle_welcome_dm")],
        [InlineKeyboardButton("\U0001f519 Control Panel", callback_data="cp_main")],
    ])
    await query.edit_message_text(f"\u2699\ufe0f <b>Settings</b>\n\n\u26a1 Auto-Approve: {auto}\n\U0001f4ac Welcome DM: {welcome}", parse_mode="HTML", reply_markup=kb)

async def cp_toggle_global_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not db.pool:
        await query.answer("DB offline", show_alert=True)
        return
    settings = await db.get_bot_settings()
    new_val = not settings.get("auto_approve", True)
    await db.update_bot_setting("auto_approve", new_val)
    status = "ON" if new_val else "OFF"
    await query.answer(f"Global Auto-Approve: {status}")
    await cp_settings(update, context)


async def cp_toggle_welcome_dm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not db.pool:
        await query.answer("DB offline", show_alert=True)
        return
    settings = await db.get_bot_settings()
    new_val = not settings.get("welcome_dm", True)
    await db.update_bot_setting("welcome_dm", new_val)
    status = "ON" if new_val else "OFF"
    await query.answer(f"Welcome DM: {status}")
    await cp_settings(update, context)
