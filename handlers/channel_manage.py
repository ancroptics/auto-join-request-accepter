import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import ADMIN_IDS
import database as db

logger = logging.getLogger(__name__)


async def handle_my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        my = update.my_chat_member
        chat = my.chat
        user = my.from_user
        new = my.new_chat_member.status
        old = my.old_chat_member.status
        if not db.pool:
            return
        if new in ("administrator", "member") and old in ("left", "kicked"):
            await db.add_channel(channel_id=chat.id, title=chat.title or "Unknown",
                                 username=chat.username, added_by=user.id)
            logger.info(f"Bot added to {chat.title} ({chat.id}) by {user.id}")
            pending_count = await db.get_pending_count_for_channel(chat.id)
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"\U0001f465 Pending Requests ({pending_count})",
                    callback_data=f"cp_pending_{chat.id}")],
                [InlineKeyboardButton("\u2699\ufe0f Channel Settings",
                    callback_data=f"cp_ch_{chat.id}")],
            ])
            try:
                await context.bot.send_message(chat_id=user.id,
                    text=(f"\u2705 <b>Connected to {chat.title}</b>\n\n"
                          f"Channel ID: <code>{chat.id}</code>\n"
                          f"Pending requests: <b>{pending_count}</b>\n\n"
                          f"I'll auto-approve new join requests.\n"
                          f"Use the buttons below to manage this channel."),
                    parse_mode="HTML", reply_markup=kb)
            except Exception as e:
                logger.warning(f"Could not DM user {user.id}: {e}")
        elif new in ("left", "kicked") and old in ("administrator", "member"):
            await db.remove_channel(chat.id)
            logger.info(f"Bot removed from {chat.title} ({chat.id})")
            try:
                await context.bot.send_message(chat_id=user.id,
                    text=f"\U0001f6ab <b>Disconnected from {chat.title}</b>\n\nI'll no longer manage join requests for this channel.",
                    parse_mode="HTML")
            except:
                pass
    except Exception as e:
        logger.error(f"handle_my_chat_member error: {e}")


async def cp_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    buttons = [
        [InlineKeyboardButton("\U0001f4cb My Channels", callback_data="cp_channels_list")],
        [InlineKeyboardButton("\U0001f465 All Pending Requests", callback_data="cp_pending_overview")],
        [InlineKeyboardButton("\u2699\ufe0f Settings", callback_data="cp_settings")],
    ]
    if user_id in ADMIN_IDS:
        buttons.append([InlineKeyboardButton("\U0001f6e0 Admin Panel", callback_data="admin_panel")])
    buttons.append([InlineKeyboardButton("\U0001f3e0 Home", callback_data="go_home")])
    await query.edit_message_text("\U0001f39b <b>Control Panel</b>\n\nManage your channels and join requests.",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))


async def cp_channels_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    try:
        if user_id in ADMIN_IDS:
            channels = await db.get_all_channels()
        else:
            channels = await db.get_channels_by_user(user_id)
        if not channels:
            await query.edit_message_text(
                "\U0001f4cb <b>My Channels</b>\n\nNo channels yet.\n\n"
                "\u27a1\ufe0f Add me as an <b>admin</b> to your channel and I'll appear here!",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="cp_main")]]))
            return
        text = "\U0001f4cb <b>My Channels</b>\n\nTap a channel to manage it:\n"
        buttons = []
        for ch in channels:
            ch_id = ch.get("channel_id")
            title = (ch.get("title") or "Unknown")[:28]
            pending = await db.get_pending_count_for_channel(ch_id)
            label = f"{title}"
            if pending > 0:
                label += f"  \u2022  {pending} pending"
            buttons.append([InlineKeyboardButton(label, callback_data=f"cp_ch_{ch_id}")])
        buttons.append([InlineKeyboardButton("\U0001f519 Back", callback_data="cp_main")])
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        logger.error(f"cp_channels_list error: {e}")
        await query.edit_message_text(f"\u274c Error: {e}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="cp_main")]]))


async def cp_channel_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, channel_id: int):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    try:
        ch = await db.get_channel(channel_id)
        if not ch:
            await query.edit_message_text("\u274c Channel not found.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="cp_channels_list")]]))
            return
        if user_id not in ADMIN_IDS and ch.get("added_by") != user_id:
            await query.edit_message_text("\u274c Access denied.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="cp_channels_list")]]))
            return
        title = ch.get("title", "Unknown")
        username = ch.get("username")
        uname_display = f"@{username}" if username else "Private"
        auto = "\u2705 On" if ch.get("auto_approve", True) else "\u274c Off"
        pending = await db.get_pending_count_for_channel(channel_id)
        text = (f"\U0001f4e2 <b>{title}</b>\n\n"
                f"ID: <code>{channel_id}</code>\n"
                f"Username: {uname_display}\n"
                f"Auto-approve: {auto}\n"
                f"Pending requests: <b>{pending}</b>")
        buttons = []
        if pending > 0:
            buttons.append([InlineKeyboardButton(f"\U0001f465 View Pending Requests ({pending})",
                callback_data=f"cp_pending_{channel_id}")])
        buttons.append([InlineKeyboardButton("\u270f\ufe0f Welcome Message", callback_data=f"cp_setwelcome_{channel_id}")])
        buttons.append([InlineKeyboardButton("\U0001f5d1 Remove Channel", callback_data=f"cp_remove_{channel_id}")])
        buttons.append([InlineKeyboardButton("\U0001f519 Back to Channels", callback_data="cp_channels_list")])
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        logger.error(f"cp_channel_detail error: {e}")
        await query.edit_message_text(f"\u274c Error: {e}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="cp_channels_list")]]))


async def cp_pending_overview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    try:
        if user_id in ADMIN_IDS:
            channels = await db.get_all_channels()
        else:
            channels = await db.get_channels_by_user(user_id)
        total = 0
        ch_data = []
        for ch in (channels or []):
            ch_id = ch.get("channel_id")
            count = await db.get_pending_count_for_channel(ch_id)
            if count > 0:
                ch_data.append({"id": ch_id, "title": ch.get("title", "Unknown"), "count": count})
                total += count
        if total == 0:
            await query.edit_message_text(
                "\U0001f465 <b>Pending Requests</b>\n\n\u2705 No pending requests across any of your channels!",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="cp_main")]]))
            return
        text = f"\U0001f465 <b>Pending Requests</b>\n\nTotal: <b>{total}</b>\n\n"
        buttons = []
        for c in ch_data:
            text += f"\u2022 <b>{c['title']}</b>: {c['count']}\n"
            buttons.append([InlineKeyboardButton(f"{c['title'][:25]}  \u2014  {c['count']} pending",
                callback_data=f"cp_pending_{c['id']}")])
        buttons.append([InlineKeyboardButton("\U0001f519 Back", callback_data="cp_main")])
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        logger.error(f"cp_pending_overview error: {e}")
        await query.edit_message_text(f"\u274c Error: {e}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="cp_main")]]))


async def cp_pending_channel(update: Update, context: ContextTypes.DEFAULT_TYPE, channel_id: int):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    try:
        ch = await db.get_channel(channel_id)
        if not ch:
            await query.edit_message_text("\u274c Channel not found.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="cp_main")]]))
            return
        if user_id not in ADMIN_IDS and ch.get("added_by") != user_id:
            await query.edit_message_text("\u274c Access denied.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="cp_channels_list")]]))
            return
        title = ch.get("title", "Unknown")
        pending = await db.get_pending_requests_for_channel(channel_id)
        count = len(pending) if pending else 0
        if count == 0:
            await query.edit_message_text(
                f"\U0001f465 <b>{title}</b>\n\n\u2705 No pending requests!",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back to Channel", callback_data=f"cp_ch_{channel_id}")]]))
            return
        text = f"\U0001f465 <b>{title}</b> \u2014 <b>{count}</b> pending\n\n"
        for i, req in enumerate(pending[:15], 1):
            uid = req.get("user_id", "?")
            text += f"{i}. User <code>{uid}</code>\n"
        if count > 15:
            text += f"\n<i>...and {count - 15} more</i>"
        text += "\n\n<b>Choose an action:</b>"
        buttons = [[InlineKeyboardButton(f"\u2705 Accept All ({count})", callback_data=f"cp_accept_all_{channel_id}")]]
        if count > 10:
            row = []
            for n in [10, 25, 50]:
                if n < count:
                    row.append(InlineKeyboardButton(f"Accept {n}", callback_data=f"cp_accept_n_{n}_{channel_id}"))
            if row:
                buttons.append(row)
        if count > 5:
            buttons.append([InlineKeyboardButton(f"\U0001f3b2 Accept Random", callback_data=f"cp_accept_random_menu_{channel_id}")])
        buttons.append([InlineKeyboardButton("\U0001f519 Back to Channel", callback_data=f"cp_ch_{channel_id}")])
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        logger.error(f"cp_pending_channel error: {e}")
        await query.edit_message_text(f"\u274c Error: {e}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data=f"cp_ch_{channel_id}")]]))


async def cp_accept_random_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, channel_id: int):
    query = update.callback_query
    await query.answer()
    count = await db.get_pending_count_for_channel(channel_id)
    text = f"\U0001f3b2 <b>Accept Random</b>\n\nThere are <b>{count}</b> pending requests.\nHow many to accept randomly?"
    buttons = []
    row = []
    for n in [5, 10, 25, 50, 100]:
        if n <= count:
            row.append(InlineKeyboardButton(str(n), callback_data=f"cp_accept_rand_{n}_{channel_id}"))
            if len(row) == 3:
                buttons.append(row)
                row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("\U0001f519 Back", callback_data=f"cp_pending_{channel_id}")])
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))


async def _do_approve(update, context, channel_id, mode, count=0):
    query = update.callback_query
    user_id = query.from_user.id
    ch = await db.get_channel(channel_id)
    if not ch:
        await query.edit_message_text("\u274c Channel not found.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="cp_main")]]))
        return
    if user_id not in ADMIN_IDS and ch.get("added_by") != user_id:
        await query.edit_message_text("\u274c Access denied.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="cp_channels_list")]]))
        return
    title = ch.get("title", "Unknown")
    pending = await db.get_pending_requests_for_channel(channel_id)
    if not pending:
        await query.edit_message_text(f"\u2705 <b>{title}</b>\n\nNo pending requests to process.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data=f"cp_ch_{channel_id}")]]))
        return
    if mode == "all":
        targets = pending
    elif mode == "first":
        targets = pending[:count]
    elif mode == "random":
        targets = random.sample(pending, min(count, len(pending)))
    else:
        targets = pending
    total = len(targets)
    await query.edit_message_text(f"\u23f3 <b>Processing {total} requests for {title}...</b>\n\nPlease wait.",
        parse_mode="HTML")
    approved = 0
    failed = 0
    for req in targets:
        uid = req.get("user_id")
        rid = req.get("id")
        try:
            await context.bot.approve_chat_join_request(chat_id=channel_id, user_id=uid)
            if rid:
                await db.update_join_request_status(rid, "approved")
            approved += 1
        except Exception as e:
            failed += 1
            if "USER_ALREADY_PARTICIPANT" in str(e) or "HIDE_REQUESTER_MISSING" in str(e):
                if rid:
                    try:
                        await db.update_join_request_status(rid, "expired")
                    except:
                        pass
            logger.warning(f"Approve failed for {uid}: {e}")
    text = f"\u2705 <b>Done \u2014 {title}</b>\n\n\u2705 Approved: <b>{approved}</b>\n"
    if failed:
        text += f"\u26a0\ufe0f Failed/Expired: <b>{failed}</b>\n"
    remaining = await db.get_pending_count_for_channel(channel_id)
    if remaining > 0:
        text += f"\n\U0001f465 Remaining: <b>{remaining}</b>"
    buttons = []
    if remaining > 0:
        buttons.append([InlineKeyboardButton(f"\U0001f465 View Remaining ({remaining})", callback_data=f"cp_pending_{channel_id}")])
    buttons.append([InlineKeyboardButton("\U0001f519 Back to Channel", callback_data=f"cp_ch_{channel_id}")])
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))


async def cp_set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE, channel_id):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if str(channel_id) == "global":
        if user_id not in ADMIN_IDS:
            await query.answer("\u274c Admin only", show_alert=True)
            return
        context.user_data["set_welcome_chat_id"] = "global"
        await query.edit_message_text(
            "\u270f\ufe0f <b>Set Global Welcome Message</b>\n\nSend me the new welcome message.\nUse /cancel to abort.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u274c Cancel", callback_data="cp_settings")]]))
        return
    ch = await db.get_channel(int(channel_id))
    if not ch:
        await query.edit_message_text("\u274c Channel not found.")
        return
    if user_id not in ADMIN_IDS and ch.get("added_by") != user_id:
        await query.edit_message_text("\u274c Access denied.")
        return
    context.user_data["set_welcome_chat_id"] = int(channel_id)
    title = ch.get("title", "Unknown")
    current = ch.get("welcome_message") or "Default"
    await query.edit_message_text(
        f"\u270f\ufe0f <b>Welcome Message \u2014 {title}</b>\n\n<b>Current:</b> {current}\n\nSend me the new message, or /cancel.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u274c Cancel", callback_data=f"cp_ch_{channel_id}")]]))


async def cp_remove_channel(update, context, channel_id):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    ch = await db.get_channel(channel_id)
    if not ch or (user_id not in ADMIN_IDS and ch.get("added_by") != user_id):
        await query.edit_message_text("\u274c Not found or access denied.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="cp_channels_list")]]))
        return
    title = ch.get("title", "Unknown")
    await query.edit_message_text(
        f"\U0001f5d1 <b>Remove {title}?</b>\n\nThe bot will stop managing join requests for this channel.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("\u2705 Yes, Remove", callback_data=f"cp_remove_yes_{channel_id}")],
            [InlineKeyboardButton("\u274c Cancel", callback_data=f"cp_ch_{channel_id}")],
        ]))


async def cp_remove_confirm(update, context, channel_id):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    ch = await db.get_channel(channel_id)
    if not ch or (user_id not in ADMIN_IDS and ch.get("added_by") != user_id):
        await query.edit_message_text("\u274c Not found or access denied.")
        return
    title = ch.get("title", "Unknown")
    await db.remove_channel(channel_id)
    await query.edit_message_text(f"\u2705 <b>{title}</b> removed.", parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back to Channels", callback_data="cp_channels_list")]]))



async def cp_pending_mine(update, context):
    """Show pending requests only for the user's own channels."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    try:
        channels = await db.get_channels_by_user(user_id)
        total = 0
        ch_data = []
        for ch in (channels or []):
            ch_id = ch.get("channel_id")
            count = await db.get_pending_count_for_channel(ch_id)
            if count > 0:
                ch_data.append({"id": ch_id, "title": ch.get("title", "Unknown"), "count": count})
                total += count
        if total == 0:
            await query.edit_message_text(
                "\U0001f465 <b>Pending Requests</b>\n\n\u2705 No pending requests across your channels!",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="cp_main")]]))
            return
        text = f"\U0001f465 <b>Pending Requests</b>\n\nTotal: <b>{total}</b>\n\n"
        buttons = []
        for c in ch_data:
            text += f"\u2022 <b>{c['title']}</b>: {c['count']}\n"
            buttons.append([InlineKeyboardButton(f"{c['title'][:25]}  \u2014  {c['count']} pending",
                callback_data=f"cp_pending_{c['id']}")])
        buttons.append([InlineKeyboardButton("\U0001f519 Back", callback_data="cp_main")])
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        logger.error(f"cp_pending_mine error: {e}")
        await query.edit_message_text(f"\u274c Error: {e}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="cp_main")]]))


async def handle_channel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    try:
        if data == "cp_main":
            await cp_main_menu(update, context)
        elif data == "cp_channels_list":
            await cp_channels_list(update, context)
        elif data == "cp_pending_overview":
            await cp_pending_overview(update, context)
        elif data == "cp_pending_mine":
            await cp_pending_mine(update, context)
        elif data == "cp_settings":
            from handlers.callbacks import show_settings
            await show_settings(update, context)
        elif data.startswith("cp_ch_"):
            ch_id = int(data[6:])
            await cp_channel_detail(update, context, ch_id)
        elif data.startswith("cp_pending_"):
            ch_id = int(data[11:])
            await cp_pending_channel(update, context, ch_id)
        elif data.startswith("cp_accept_all_"):
            ch_id = int(data[14:])
            await query.answer("Approving all...")
            await _do_approve(update, context, ch_id, "all")
        elif data.startswith("cp_accept_n_"):
            rest = data[12:]
            n_str, ch_str = rest.split("_", 1)
            await query.answer(f"Approving {n_str}...")
            await _do_approve(update, context, int(ch_str), "first", int(n_str))
        elif data.startswith("cp_accept_random_menu_"):
            ch_id = int(data[22:])
            await cp_accept_random_menu(update, context, ch_id)
        elif data.startswith("cp_accept_rand_"):
            rest = data[15:]
            n_str, ch_str = rest.split("_", 1)
            await query.answer(f"Randomly approving {n_str}...")
            await _do_approve(update, context, int(ch_str), "random", int(n_str))
        elif data.startswith("cp_setwelcome_"):
            target = data[14:]
            await cp_set_welcome(update, context, target)
        elif data.startswith("cp_remove_yes_"):
            ch_id = int(data[14:])
            await cp_remove_confirm(update, context, ch_id)
        elif data.startswith("cp_remove_"):
            ch_id = int(data[10:])
            await cp_remove_channel(update, context, ch_id)
        else:
            await query.answer("Unknown action", show_alert=True)
    except ValueError as e:
        logger.error(f"Bad callback data \'{data}\': {e}")
        try:
            await query.answer("Invalid action", show_alert=True)
        except Exception:
            pass
    except Exception as e:
        logger.error(f"Callback error \'{data}\': {e}")
        import traceback
        traceback.print_exc()
        try:
            await query.answer(f"Error: {str(e)[:80]}", show_alert=True)
        except Exception:
            pass
