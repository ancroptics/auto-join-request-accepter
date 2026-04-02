import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import ADMIN_IDS
import database as db

logger = logging.getLogger(__name__)

async def handle_my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detect when bot is added/removed from a channel."""
    result = update.my_chat_member
    chat = result.chat
    new_status = result.new_chat_member.status
    old_status = result.old_chat_member.status

    logger.info(f"MyChatMember: chat={chat.id} ({chat.title}) old={old_status} new={new_status}")

    if chat.type not in ("channel", "supergroup", "group"):
        return

    if new_status in ("administrator", "member"):
        title = safe_text(chat.title or "Unknown Channel")
        await db.add_channel(chat.id, title, getattr(chat, "username", None))
        logger.info(f"Channel added: {chat.id} - {safe_text(chat.title)}")
        # Notify admins
        for aid in ADMIN_IDS:
            try:
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("\ud83d\udccb Manage Channels", callback_data="cp_channels_list")],
                    [InlineKeyboardButton("\ud83d\udd19 Control Panel", callback_data="cp_main")],
                ])
                await context.bot.send_message(
                    aid,
                    f"\u2705 <b>Bot added to channel!</b>\n\n"
                    f"\ud83d\udce2 <b>{safe_text(chat.title)}</b>\n"
                    f"ID: <code>{chat.id}</code>",
                    parse_mode="HTML", reply_markup=kb
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {aid}: {e}")

    elif new_status in ("left", "kicked"):
        await db.remove_channel(chat.id)
        logger.info(f"Channel removed: {chat.id} - {safe_text(chat.title)}")
        for aid in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    aid,
                    f"\u274c <b>Bot removed from channel</b>\n\n"
                    f"\ud83d\udce2 {safe_text(chat.title)}\n"
                    f"ID: <code>{chat.id}</code>",
                    parse_mode="HTML"
                )
            except:
                pass

async def handle_channel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all cp_* callbacks."""
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    if user_id not in ADMIN_IDS:
        await query.answer("\u274c Admin only", show_alert=True)
        return

    if data == "cp_main":
        await show_main_panel(query)
    elif data == "cp_channels_list":
        await show_channels_list(query)
    elif data == "cp_pending_all":
        await show_pending_all(query)
    elif data.startswith("cp_ch_"):
        channel_id = int(data.replace("cp_ch_", ""))
        await show_channel_detail(query, channel_id, context)
    elif data.startswith("cp_toggle_auto_"):
        channel_id = int(data.replace("cp_toggle_auto_", ""))
        await toggle_auto_approve_cb(query, channel_id, context)
    elif data.startswith("cp_approve_all_"):
        channel_id = int(data.replace("cp_approve_all_", ""))
        await approve_all_cb(query, channel_id, context)
    elif data.startswith("cp_approve_first_"):
        parts = data.replace("cp_approve_first_", "").split("_")
        channel_id = int(parts[0])
        count = int(parts[1]) if len(parts) > 1 else 10
        await approve_first_n_cb(query, channel_id, count, context)
    elif data.startswith("cp_approve_random_"):
        parts = data.replace("cp_approve_random_", "").split("_")
        channel_id = int(parts[0])
        count = int(parts[1]) if len(parts) > 1 else 10
        await approve_random_n_cb(query, channel_id, count, context)
    elif data.startswith("cp_remove_"):
        channel_id = int(data.replace("cp_remove_", ""))
        await remove_channel_cb(query, channel_id)
    elif data.startswith("cp_settings"):
        # Route to settings in callbacks.py
        from handlers.callbacks import show_settings
        await show_settings(update, context)
    else:
        await query.answer("\u2754 Unknown panel action")

async def show_main_panel(query):
    await query.answer()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("\ud83d\udccb My Channels", callback_data="cp_channels_list")],
        [InlineKeyboardButton("\ud83d\udc65 Pending Requests", callback_data="cp_pending_all")],
        [InlineKeyboardButton("\u2699\ufe0f Settings", callback_data="cp_settings")],
    ])
    try:
        await query.edit_message_text(
            "\ud83c\udf9b <b>Control Panel</b>\n\n"
            "Manage your channels, approve join requests, and configure settings.",
            parse_mode="HTML", reply_markup=kb
        )
    except Exception:
        await query.message.reply_text(
            "\ud83c\udf9b <b>Control Panel</b>\n\n"
            "Manage your channels, approve join requests, and configure settings.",
            parse_mode="HTML", reply_markup=kb
        )

async def show_channels_list(query):
    await query.answer()
    channels = await db.get_all_channels()
    if not channels:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("\ud83d\udd19 Back", callback_data="cp_main")]])
        try:
            await query.edit_message_text(
                "\ud83d\udccb <b>My Channels</b>\n\n"
                "No channels found. Add the bot as admin to a channel to get started.",
                parse_mode="HTML", reply_markup=kb
            )
        except:
            await query.message.reply_text(
                "\ud83d\udccb <b>My Channels</b>\n\n"
                "No channels found. Add the bot as admin to a channel to get started.",
                parse_mode="HTML", reply_markup=kb
            )
        return

    buttons = []
    for ch in channels:
        title = ch.get("title") or "Unknown"
        pending = await db.get_pending_count_for_channel(ch["channel_id"])
        auto_icon = "\u2705" if ch.get("auto_approve") else "\u274c"
        buttons.append([InlineKeyboardButton(
            f"{auto_icon} {title} ({pending} pending)",
            callback_data=f"cp_ch_{ch['channel_id']}"
        )])
    buttons.append([InlineKeyboardButton("\ud83d\udd19 Back", callback_data="cp_main")])

    kb = InlineKeyboardMarkup(buttons)
    try:
        await query.edit_message_text(
            f"\ud83d\udccb <b>My Channels</b> ({len(channels)})\n\n"
            f"\u2705 = Auto-approve ON | \u274c = OFF\n"
            f"Tap a channel to manage it.",
            parse_mode="HTML", reply_markup=kb
        )
    except:
        await query.message.reply_text(
            f"\ud83d\udccb <b>My Channels</b> ({len(channels)})\n\n"
            f"\u2705 = Auto-approve ON | \u274c = OFF\n"
            f"Tap a channel to manage it.",
            parse_mode="HTML", reply_markup=kb
        )

async def show_pending_all(query):
    await query.answer()
    channels = await db.get_all_channels()
    if not channels:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("\ud83d\udd19 Back", callback_data="cp_main")]])
        try:
            await query.edit_message_text(
                "\ud83d\udc65 <b>Pending Requests</b>\n\nNo channels found.",
                parse_mode="HTML", reply_markup=kb
            )
        except:
            pass
        return

    lines = ["\ud83d\udc65 <b>Pending Requests Summary</b>\n"]
    total = 0
    buttons = []
    for ch in channels:
        count = await db.get_pending_count_for_channel(ch["channel_id"])
        total += count
        title = ch.get("title") or "Unknown"
        lines.append(f"\u25ab {title}: <b>{count}</b>")
        if count > 0:
            buttons.append([InlineKeyboardButton(f"\u2705 Approve all for {title}", callback_data=f"cp_approve_all_{ch['channel_id']}")])

    lines.append(f"\n\ud83d\udcca <b>Total pending: {total}</b>")
    buttons.append([InlineKeyboardButton("\ud83d\udd19 Back", callback_data="cp_main")])

    kb = InlineKeyboardMarkup(buttons)
    try:
        await query.edit_message_text("\n".join(lines), parse_mode="HTML", reply_markup=kb)
    except:
        await query.message.reply_text("\n".join(lines), parse_mode="HTML", reply_markup=kb)

async def show_channel_detail(query, channel_id, context):
    await query.answer()
    ch = await db.get_channel(channel_id)
    if not ch:
        await query.edit_message_text("\u274c Channel not found.")
        return

    title = ch.get("title") or "Unknown"
    pending = await db.get_pending_count_for_channel(channel_id)
    auto_approve = "\u2705 ON" if ch.get("auto_approve") else "\u274c OFF"
    welcome = ch.get("welcome_message") or "Not set (using global)"
    welcome_preview = (welcome[:50] + "...") if len(welcome) > 50 else welcome

    text = (
        f"\ud83d\udce2 <b>{html_escape(title)}</b>\n\n"
        f"\ud83c\udd94 ID: <code>{channel_id}</code>\n"
        f"\ud83d\udc65 Pending: <b>{pending}</b>\n"
        f"\ud83d\ude80 Auto-approve: {auto_approve}\n"
        f"\ud83d\udc4b Welcome: {welcome_preview}"
    )

    buttons = []
    toggle_text = "\u274c Disable Auto-approve" if ch.get("auto_approve") else "\u2705 Enable Auto-approve"
    buttons.append([InlineKeyboardButton(toggle_text, callback_data=f"cp_toggle_auto_{channel_id}")])

    if pending > 0:
        buttons.append([InlineKeyboardButton(f"\u2705 Approve All ({pending})", callback_data=f"cp_approve_all_{channel_id}")])
        if pending > 10:
            buttons.append([
                InlineKeyboardButton("\ud83d\udd1d First 10", callback_data=f"cp_approve_first_{channel_id}_10"),
                InlineKeyboardButton("\ud83c\udfb2 Random 10", callback_data=f"cp_approve_random_{channel_id}_10"),
            ])

    buttons.append([InlineKeyboardButton("\ud83d\udc4b Set Welcome", callback_data=f"set_welcome_{channel_id}")])
    buttons.append([InlineKeyboardButton("\ud83d\uddd1 Remove Channel", callback_data=f"cp_remove_{channel_id}")])
    buttons.append([InlineKeyboardButton("\ud83d\udd19 Back", callback_data="cp_channels_list")])

    kb = InlineKeyboardMarkup(buttons)
    try:
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
    except:
        await query.message.reply_text(text, parse_mode="HTML", reply_markup=kb)

def html_escape(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def safe_text(text):
    """Remove surrogate characters that break HTTP encoding."""
    if not text:
        return text
    return text.encode('utf-8', errors='replace').decode('utf-8')

async def toggle_auto_approve_cb(query, channel_id, context):
    new_val = await db.toggle_auto_approve(channel_id)
    if new_val is None:
        await query.answer("\u274c Channel not found")
        return
    status = "ON" if new_val else "OFF"
    await query.answer(f"Auto-approve: {status}")
    await show_channel_detail(query, channel_id, context)

async def approve_all_cb(query, channel_id, context):
    await query.answer("\u23f3 Approving...")
    requests = await db.get_pending_requests_for_channel(channel_id)
    success = 0
    failed = 0
    for req in requests:
        try:
            await context.bot.approve_chat_join_request(channel_id, req["user_id"])
            await db.update_join_request_status(req["id"], "approved")
            success += 1
        except Exception as e:
            logger.error(f"Failed to approve {req['user_id']}: {e}")
            await db.update_join_request_status(req["id"], "failed")
            failed += 1

    try:
        await query.edit_message_text(
            f"\u2705 <b>Approval complete!</b>\n\n"
            f"\u2705 Approved: <b>{success}</b>\n"
            f"\u274c Failed: <b>{failed}</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\ud83d\udd19 Back", callback_data=f"cp_ch_{channel_id}")]])
        )
    except:
        pass

async def approve_first_n_cb(query, channel_id, count, context):
    await query.answer(f"\u23f3 Approving first {count}...")
    requests = await db.get_pending_requests_for_channel(channel_id, limit=count)
    success = 0
    for req in requests:
        try:
            await context.bot.approve_chat_join_request(channel_id, req["user_id"])
            await db.update_join_request_status(req["id"], "approved")
            success += 1
        except:
            await db.update_join_request_status(req["id"], "failed")

    try:
        await query.edit_message_text(
            f"\u2705 <b>Approved {success}/{count} requests</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\ud83d\udd19 Back", callback_data=f"cp_ch_{channel_id}")]])
        )
    except:
        pass

async def approve_random_n_cb(query, channel_id, count, context):
    await query.answer(f"\u23f3 Approving {count} random...")
    all_reqs = await db.get_pending_requests_for_channel(channel_id)
    selected = random.sample(all_reqs, min(count, len(all_reqs)))
    success = 0
    for req in selected:
        try:
            await context.bot.approve_chat_join_request(channel_id, req["user_id"])
            await db.update_join_request_status(req["id"], "approved")
            success += 1
        except:
            await db.update_join_request_status(req["id"], "failed")

    try:
        await query.edit_message_text(
            f"\u2705 <b>Approved {success} random requests</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\ud83d\udd19 Back", callback_data=f"cp_ch_{channel_id}")]])
        )
    except:
        pass

async def remove_channel_cb(query, channel_id):
    await db.remove_channel(channel_id)
    await query.answer("\u2705 Channel removed")
    await show_channels_list(query)
