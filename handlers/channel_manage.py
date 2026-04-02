import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import ADMIN_IDS

logger = logging.getLogger(__name__)


async def handle_my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle bot being added/removed from channels/groups."""
    try:
        my_member = update.my_chat_member
        chat = my_member.chat
        user = my_member.from_user
        new_status = my_member.new_chat_member.status
        old_status = my_member.old_chat_member.status

        import database as db
        if not db.pool:
            return

        if new_status in ("administrator", "member") and old_status in ("left", "kicked"):
            await db.add_channel(
                channel_id=chat.id,
                title=chat.title or "Unknown",
                username=chat.username,
                chat_type=chat.type,
                added_by=user.id
            )
            logger.info(f"Bot added to {chat.title} ({chat.id}) by user {user.id}")

            try:
                buttons = [
                    [InlineKeyboardButton("\U0001f4cb My Channels", callback_data="cp_channels_list")],
                    [InlineKeyboardButton("\U0001f465 Pending Requests", callback_data=f"cp_pending_{chat.id}")],
                    [InlineKeyboardButton("\u2705 Accept All Pending", callback_data=f"cp_approve_all_{chat.id}")],
                    [InlineKeyboardButton("\U0001f3e0 Home", callback_data="go_home")],
                ]
                await context.bot.send_message(
                    chat_id=user.id,
                    text=f"\u2705 <b>Bot added to {chat.title}!</b>\n\n"
                         f"Channel ID: <code>{chat.id}</code>\n"
                         f"Type: {chat.type}\n\n"
                         f"I'll automatically approve join requests for this channel.\n"
                         f"Use the buttons below to manage it:",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
            except Exception as e:
                logger.warning(f"Could not DM user {user.id}: {e}")

        elif new_status in ("left", "kicked") and old_status in ("administrator", "member"):
            await db.remove_channel(chat.id)
            logger.info(f"Bot removed from {chat.title} ({chat.id})")

            try:
                await context.bot.send_message(
                    chat_id=user.id,
                    text=f"\U0001f6ab <b>Bot removed from {chat.title}</b>\n\n"
                         f"Channel ID: <code>{chat.id}</code>\n"
                         f"I will no longer manage join requests for this channel.",
                    parse_mode="HTML"
                )
            except Exception:
                pass

    except Exception as e:
        logger.error(f"Error in handle_my_chat_member: {e}")


async def cp_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the main control panel menu."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    is_admin = user_id in ADMIN_IDS

    buttons = [
        [InlineKeyboardButton("\U0001f4cb My Channels", callback_data="cp_channels_list")],
        [InlineKeyboardButton("\U0001f465 Pending Requests", callback_data="cp_pending_mine")],
        [InlineKeyboardButton("\u2699\ufe0f Settings", callback_data="cp_settings")],
    ]
    if is_admin:
        buttons.insert(2, [InlineKeyboardButton("\U0001f465 All Pending (Admin)", callback_data="cp_pending_all")])
    buttons.append([InlineKeyboardButton("\U0001f3e0 Home", callback_data="go_home")])

    await query.edit_message_text(
        "\U0001f39b <b>Control Panel</b>\n\n"
        "Manage your channels, approve join requests, and configure settings.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def cp_channels_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show list of channels the user owns (or all channels for admins)."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    is_admin = user_id in ADMIN_IDS

    try:
        import database as db
        if is_admin:
            channels = await db.get_all_channels()
        else:
            channels = await db.get_user_channels(user_id)

        if not channels:
            text = "\U0001f4cb <b>My Channels</b>\n\nNo channels found.\n\nAdd me as an admin to your channel to get started!"
            buttons = [[InlineKeyboardButton("\U0001f519 Back to Panel", callback_data="cp_main")]]
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
            return

        text = "\U0001f4cb <b>My Channels</b>\n\nSelect a channel to manage:"
        buttons = []
        for ch in channels:
            title = ch.get("title", "Unknown")[:30]
            ch_id = ch.get("channel_id") or ch.get("chat_id")
            if ch_id:
                buttons.append([InlineKeyboardButton(f"\U0001f4e2 {title}", callback_data=f"cp_ch_{ch_id}")])

        buttons.append([InlineKeyboardButton("\U0001f519 Back to Panel", callback_data="cp_main")])
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

    except Exception as e:
        logger.error(f"Error in cp_channels_list: {e}")
        await query.edit_message_text(f"\u274c Error loading channels: {e}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="cp_main")]]))


async def cp_channel_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, channel_id: int):
    """Show details and actions for a specific channel."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    is_admin = user_id in ADMIN_IDS

    try:
        import database as db
        ch = await db.get_channel(channel_id)
        if not ch:
            await query.edit_message_text("\u274c Channel not found.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="cp_channels_list")]]))
            return

        if not is_admin and ch.get("added_by") != user_id:
            await query.edit_message_text("\u274c You don't have access to this channel.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="cp_channels_list")]]))
            return

        title = ch.get("title", "Unknown")
        ch_type = ch.get("chat_type", "unknown")
        username = ch.get("username", "N/A")
        if username and not username.startswith("@"):
            username = f"@{username}"

        pending = await db.get_pending_requests(channel_id)
        pending_count = len(pending) if pending else 0

        text = (
            f"\U0001f4e2 <b>{title}</b>\n\n"
            f"ID: <code>{channel_id}</code>\n"
            f"Type: {ch_type}\n"
            f"Username: {username or 'N/A'}\n"
            f"Pending requests: <b>{pending_count}</b>\n"
        )

        buttons = []
        if pending_count > 0:
            buttons.append([InlineKeyboardButton(f"\U0001f465 View Pending ({pending_count})", callback_data=f"cp_pending_{channel_id}")])
            buttons.append([InlineKeyboardButton("\u2705 Accept All", callback_data=f"cp_approve_all_{channel_id}")])
            if pending_count > 5:
                buttons.append([
                    InlineKeyboardButton("Accept First 5", callback_data=f"cp_approve_first_5_{channel_id}"),
                    InlineKeyboardButton("Accept First 10", callback_data=f"cp_approve_first_10_{channel_id}")
                ])
            if pending_count > 10:
                buttons.append([
                    InlineKeyboardButton("Accept First 25", callback_data=f"cp_approve_first_25_{channel_id}"),
                    InlineKeyboardButton("Accept First 50", callback_data=f"cp_approve_first_50_{channel_id}")
                ])
            if pending_count > 5:
                buttons.append([
                    InlineKeyboardButton("\U0001f3b2 Random 5", callback_data=f"cp_approve_rand_5_{channel_id}"),
                    InlineKeyboardButton("\U0001f3b2 Random 10", callback_data=f"cp_approve_rand_10_{channel_id}")
                ])
        buttons.append([InlineKeyboardButton("\u270f\ufe0f Set Welcome Message", callback_data=f"cp_setwelcome_{channel_id}")])
        buttons.append([InlineKeyboardButton("\U0001f5d1 Remove Channel", callback_data=f"cp_remove_{channel_id}")])
        buttons.append([InlineKeyboardButton("\U0001f519 Back to Channels", callback_data="cp_channels_list")])

        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

    except Exception as e:
        logger.error(f"Error in cp_channel_detail: {e}")
        await query.edit_message_text(f"\u274c Error: {e}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="cp_channels_list")]]))


async def cp_pending_requests(update: Update, context: ContextTypes.DEFAULT_TYPE, channel_id: int = None, show_all: bool = False):
    """Show pending join requests for a channel or all channels."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    is_admin = user_id in ADMIN_IDS

    try:
        import database as db

        if show_all and is_admin:
            channels = await db.get_all_channels()
            all_pending = []
            for ch in (channels or []):
                ch_id = ch.get("channel_id") or ch.get("chat_id")
                if ch_id:
                    pending = await db.get_pending_requests(ch_id)
                    if pending:
                        for p in pending:
                            p["_channel_title"] = ch.get("title", "Unknown")
                            p["_channel_id"] = ch_id
                        all_pending.extend(pending)
            total = len(all_pending)
            text = f"\U0001f465 <b>All Pending Requests</b>\n\nTotal: <b>{total}</b>\n\n"
            if total == 0:
                text += "No pending requests across any channel."
            else:
                by_channel = {}
                for p in all_pending:
                    cid = p["_channel_id"]
                    if cid not in by_channel:
                        by_channel[cid] = {"title": p["_channel_title"], "count": 0}
                    by_channel[cid]["count"] += 1
                for cid, info in by_channel.items():
                    text += f"\U0001f4e2 <b>{info['title']}</b>: {info['count']} pending\n"
            buttons = []
            if total > 0:
                for cid, info in by_channel.items():
                    buttons.append([InlineKeyboardButton(f"\u2705 Accept All \u2014 {info['title'][:20]}", callback_data=f"cp_approve_all_{cid}")])
            buttons.append([InlineKeyboardButton("\U0001f519 Back to Panel", callback_data="cp_main")])
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
            return

        if channel_id is None:
            if is_admin:
                channels = await db.get_all_channels()
            else:
                channels = await db.get_user_channels(user_id)
            all_pending = []
            for ch in (channels or []):
                ch_id = ch.get("channel_id") or ch.get("chat_id")
                if ch_id:
                    pending = await db.get_pending_requests(ch_id)
                    if pending:
                        for p in pending:
                            p["_channel_title"] = ch.get("title", "Unknown")
                            p["_channel_id"] = ch_id
                        all_pending.extend(pending)
            total = len(all_pending)
            text = f"\U0001f465 <b>My Pending Requests</b>\n\nTotal: <b>{total}</b>\n\n"
            if total == 0:
                text += "No pending requests for your channels."
                buttons = [[InlineKeyboardButton("\U0001f519 Back to Panel", callback_data="cp_main")]]
            else:
                by_channel = {}
                for p in all_pending:
                    cid = p["_channel_id"]
                    if cid not in by_channel:
                        by_channel[cid] = {"title": p["_channel_title"], "count": 0}
                    by_channel[cid]["count"] += 1
                for cid, info in by_channel.items():
                    text += f"\U0001f4e2 <b>{info['title']}</b>: {info['count']} pending\n"
                buttons = []
                for cid, info in by_channel.items():
                    buttons.append([InlineKeyboardButton(f"Manage {info['title'][:20]} ({info['count']})", callback_data=f"cp_pending_{cid}")])
                buttons.append([InlineKeyboardButton("\U0001f519 Back to Panel", callback_data="cp_main")])
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
            return

        ch = await db.get_channel(channel_id)
        if not ch:
            await query.edit_message_text("\u274c Channel not found.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="cp_main")]]))
            return

        if not is_admin and ch.get("added_by") != user_id:
            await query.edit_message_text("\u274c Access denied.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="cp_channels_list")]]))
            return

        title = ch.get("title", "Unknown")
        pending = await db.get_pending_requests(channel_id)
        count = len(pending) if pending else 0

        text = f"\U0001f465 <b>Pending Requests \u2014 {title}</b>\n\nTotal: <b>{count}</b>\n\n"

        if count == 0:
            text += "No pending requests for this channel."
            buttons = [[InlineKeyboardButton("\U0001f519 Back to Channel", callback_data=f"cp_ch_{channel_id}")]]
        else:
            shown = pending[:20]
            for i, p in enumerate(shown, 1):
                name = p.get("first_name") or p.get("username") or str(p.get("user_id", "?"))
                text += f"{i}. {name}\n"
            if count > 20:
                text += f"\n... and {count - 20} more"

            buttons = [
                [InlineKeyboardButton(f"\u2705 Accept All ({count})", callback_data=f"cp_approve_all_{channel_id}")],
            ]
            if count > 5:
                buttons.append([
                    InlineKeyboardButton("First 5", callback_data=f"cp_approve_first_5_{channel_id}"),
                    InlineKeyboardButton("First 10", callback_data=f"cp_approve_first_10_{channel_id}")
                ])
            if count > 25:
                buttons.append([
                    InlineKeyboardButton("First 25", callback_data=f"cp_approve_first_25_{channel_id}"),
                    InlineKeyboardButton("First 50", callback_data=f"cp_approve_first_50_{channel_id}")
                ])
            if count > 100:
                buttons.append([InlineKeyboardButton("First 100", callback_data=f"cp_approve_first_100_{channel_id}")])
            if count > 5:
                buttons.append([
                    InlineKeyboardButton("\U0001f3b2 Random 5", callback_data=f"cp_approve_rand_5_{channel_id}"),
                    InlineKeyboardButton("\U0001f3b2 Random 10", callback_data=f"cp_approve_rand_10_{channel_id}")
                ])
            if count > 25:
                buttons.append([
                    InlineKeyboardButton("\U0001f3b2 Random 25", callback_data=f"cp_approve_rand_25_{channel_id}"),
                    InlineKeyboardButton("\U0001f3b2 Random 50", callback_data=f"cp_approve_rand_50_{channel_id}")
                ])
            buttons.append([InlineKeyboardButton("\U0001f519 Back to Channel", callback_data=f"cp_ch_{channel_id}")])

        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

    except Exception as e:
        logger.error(f"Error in cp_pending_requests: {e}")
        back_cb = f"cp_ch_{channel_id}" if channel_id else "cp_main"
        await query.edit_message_text(f"\u274c Error: {e}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data=back_cb)]]))


async def cp_approve_requests(update: Update, context: ContextTypes.DEFAULT_TYPE, channel_id: int, mode: str = "all", count: int = 0):
    """Approve join requests. mode: 'all', 'first', 'random'. count: number to approve (0=all)."""
    query = update.callback_query
    await query.answer("Processing approvals...")
    user_id = query.from_user.id
    is_admin = user_id in ADMIN_IDS

    try:
        import database as db
        ch = await db.get_channel(channel_id)
        if not ch:
            await query.edit_message_text("\u274c Channel not found.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="cp_main")]]))
            return

        if not is_admin and ch.get("added_by") != user_id:
            await query.edit_message_text("\u274c Access denied.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="cp_channels_list")]]))
            return

        title = ch.get("title", "Unknown")
        pending = await db.get_pending_requests(channel_id)
        if not pending:
            await query.edit_message_text(
                f"\u2705 No pending requests for <b>{title}</b>.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back to Channel", callback_data=f"cp_ch_{channel_id}")]])
            )
            return

        import random as rand_mod
        if mode == "all":
            to_approve = pending
        elif mode == "first":
            to_approve = pending[:count]
        elif mode == "random":
            to_approve = rand_mod.sample(pending, min(count, len(pending)))
        else:
            to_approve = pending

        total = len(to_approve)
        approved = 0
        failed = 0

        await query.edit_message_text(
            f"\u23f3 Approving {total} requests for <b>{title}</b>...\n\nPlease wait.",
            parse_mode="HTML"
        )

        for req in to_approve:
            try:
                req_user_id = req.get("user_id")
                if req_user_id:
                    await context.bot.approve_chat_join_request(
                        chat_id=channel_id,
                        user_id=req_user_id
                    )
                    await db.approve_join_request(channel_id, req_user_id)
                    approved += 1
            except Exception as e:
                failed += 1
                logger.warning(f"Failed to approve {req.get('user_id')} for {channel_id}: {e}")
                if "USER_ALREADY_PARTICIPANT" in str(e) or "HIDE_REQUESTER_MISSING" in str(e):
                    try:
                        await db.approve_join_request(channel_id, req.get("user_id"))
                    except:
                        pass

        result_text = (
            f"\u2705 <b>Approval Complete \u2014 {title}</b>\n\n"
            f"\u2705 Approved: <b>{approved}</b>\n"
        )
        if failed > 0:
            result_text += f"\u274c Failed/Expired: <b>{failed}</b>\n"
        result_text += f"\nTotal processed: {approved + failed} / {total}"

        buttons = [
            [InlineKeyboardButton("\U0001f519 Back to Channel", callback_data=f"cp_ch_{channel_id}")],
            [InlineKeyboardButton("\U0001f519 Back to Panel", callback_data="cp_main")],
        ]
        await query.edit_message_text(result_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

    except Exception as e:
        logger.error(f"Error in cp_approve_requests: {e}")
        await query.edit_message_text(f"\u274c Error during approval: {e}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data=f"cp_ch_{channel_id}")]]))


async def cp_set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE, channel_id: int):
    """Prompt user to set a welcome message for a channel."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    is_admin = user_id in ADMIN_IDS

    try:
        import database as db
        ch = await db.get_channel(channel_id)
        if not ch:
            await query.edit_message_text("\u274c Channel not found.")
            return
        if not is_admin and ch.get("added_by") != user_id:
            await query.edit_message_text("\u274c Access denied.")
            return

        context.user_data["set_welcome_chat_id"] = channel_id
        title = ch.get("title", "Unknown")
        current_welcome = ch.get("welcome_message", "")

        text = (
            f"\u270f\ufe0f <b>Set Welcome Message \u2014 {title}</b>\n\n"
            f"Send me the new welcome message for this channel.\n"
            f"Use /cancel to abort.\n"
        )
        if current_welcome:
            text += f"\n<b>Current message:</b>\n{current_welcome}"

        buttons = [[InlineKeyboardButton("\u274c Cancel", callback_data=f"cp_ch_{channel_id}")]]
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

    except Exception as e:
        logger.error(f"Error in cp_set_welcome: {e}")
        await query.edit_message_text(f"\u274c Error: {e}")


async def cp_remove_channel(update: Update, context: ContextTypes.DEFAULT_TYPE, channel_id: int):
    """Confirm and remove a channel."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    is_admin = user_id in ADMIN_IDS

    try:
        import database as db
        ch = await db.get_channel(channel_id)
        if not ch:
            await query.edit_message_text("\u274c Channel not found.")
            return
        if not is_admin and ch.get("added_by") != user_id:
            await query.edit_message_text("\u274c Access denied.")
            return

        title = ch.get("title", "Unknown")
        buttons = [
            [InlineKeyboardButton("\u2705 Yes, Remove", callback_data=f"cp_remove_confirm_{channel_id}")],
            [InlineKeyboardButton("\u274c Cancel", callback_data=f"cp_ch_{channel_id}")],
        ]
        await query.edit_message_text(
            f"\U0001f5d1 <b>Remove {title}?</b>\n\n"
            f"This will stop managing join requests for this channel.\n"
            f"The bot will remain in the channel but won't process requests.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        logger.error(f"Error in cp_remove_channel: {e}")
        await query.edit_message_text(f"\u274c Error: {e}")


async def cp_remove_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, channel_id: int):
    """Actually remove the channel from the database."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    is_admin = user_id in ADMIN_IDS

    try:
        import database as db
        ch = await db.get_channel(channel_id)
        if not ch:
            await query.edit_message_text("\u274c Channel not found.")
            return
        if not is_admin and ch.get("added_by") != user_id:
            await query.edit_message_text("\u274c Access denied.")
            return

        title = ch.get("title", "Unknown")
        await db.remove_channel(channel_id)

        buttons = [[InlineKeyboardButton("\U0001f519 Back to Channels", callback_data="cp_channels_list")]]
        await query.edit_message_text(
            f"\u2705 <b>{title}</b> has been removed.\n\nThe bot will no longer manage join requests for this channel.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        logger.error(f"Error in cp_remove_confirm: {e}")
        await query.edit_message_text(f"\u274c Error: {e}")


async def handle_channel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route all cp_ prefixed callbacks to the appropriate handler."""
    query = update.callback_query
    data = query.data

    try:
        if data == "cp_main":
            await cp_main_menu(update, context)
        elif data == "cp_channels_list":
            await cp_channels_list(update, context)
        elif data == "cp_pending_all":
            await cp_pending_requests(update, context, channel_id=None, show_all=True)
        elif data == "cp_pending_mine":
            await cp_pending_requests(update, context, channel_id=None, show_all=False)
        elif data.startswith("cp_ch_"):
            ch_id = int(data.replace("cp_ch_", ""))
            await cp_channel_detail(update, context, ch_id)
        elif data.startswith("cp_pending_"):
            ch_id = int(data.replace("cp_pending_", ""))
            await cp_pending_requests(update, context, channel_id=ch_id)
        elif data.startswith("cp_approve_all_"):
            ch_id = int(data.replace("cp_approve_all_", ""))
            await cp_approve_requests(update, context, ch_id, mode="all")
        elif data.startswith("cp_approve_first_"):
            parts = data.replace("cp_approve_first_", "").split("_", 1)
            n = int(parts[0])
            ch_id = int(parts[1])
            await cp_approve_requests(update, context, ch_id, mode="first", count=n)
        elif data.startswith("cp_approve_rand_"):
            parts = data.replace("cp_approve_rand_", "").split("_", 1)
            n = int(parts[0])
            ch_id = int(parts[1])
            await cp_approve_requests(update, context, ch_id, mode="random", count=n)
        elif data.startswith("cp_setwelcome_"):
            target = data.replace("cp_setwelcome_", "")
            if target == "global":
                context.user_data["set_welcome_chat_id"] = "global"
                await query.answer()
                await query.edit_message_text(
                    "\u270f\ufe0f <b>Set Global Welcome Message</b>\n\nSend me the new global welcome message.\nUse /cancel to abort.",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u274c Cancel", callback_data="cp_settings")]])
                )
            else:
                ch_id = int(target)
                await cp_set_welcome(update, context, ch_id)
        elif data.startswith("cp_remove_confirm_"):
            ch_id = int(data.replace("cp_remove_confirm_", ""))
            await cp_remove_confirm(update, context, ch_id)
        elif data.startswith("cp_remove_"):
            ch_id = int(data.replace("cp_remove_", ""))
            await cp_remove_channel(update, context, ch_id)
        elif data == "cp_settings":
            await cp_settings(update, context)
        else:
            await query.answer("Unknown action", show_alert=True)

    except ValueError as e:
        logger.error(f"Invalid callback data '{data}': {e}")
        await query.answer("Invalid action", show_alert=True)
    except Exception as e:
        logger.error(f"Error handling channel callback '{data}': {e}")
        await query.answer(f"Error: {str(e)[:100]}", show_alert=True)


async def cp_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot settings panel."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    is_admin = user_id in ADMIN_IDS

    buttons = []
    if is_admin:
        buttons.append([InlineKeyboardButton("\u270f\ufe0f Set Global Welcome", callback_data="cp_setwelcome_global")])
    buttons.append([InlineKeyboardButton("\U0001f519 Back to Panel", callback_data="cp_main")])

    text = "\u2699\ufe0f <b>Settings</b>\n\n"
    if is_admin:
        text += "Configure global bot settings here."
    else:
        text += "Channel-specific settings can be configured from each channel's detail page."

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
