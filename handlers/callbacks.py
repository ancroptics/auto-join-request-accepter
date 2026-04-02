import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import ADMIN_IDS, BOT_USERNAME, REFERRAL_REWARD_COINS
import database as db

logger = logging.getLogger(__name__)

LANGUAGES = {
    "en": "\ud83c\uddfa\ud83c\uddf8 English",
    "fa": "\ud83c\uddee\ud83c\uddf7 \u0641\u0627\u0631\u0633\u06cc",
    "ar": "\ud83c\uddf8\ud83c\udde6 \u0627\u0644\u0639\u0631\u0628\u064a\u0629",
    "tr": "\ud83c\uddf9\ud83c\uddf7 T\u00fcrk\u00e7e",
    "ru": "\ud83c\uddf7\ud83c\uddfa \u0420\u0443\u0441\u0441\u043a\u0438\u0439",
}

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    logger.info(f"Callback: {data} from {query.from_user.id}")

    try:
        # Start menu callbacks
        if data == "my_referral":
            from handlers.user_commands import referral_command
            await referral_command(update, context)
            return

        if data == "my_stats":
            from handlers.user_commands import mystats_command
            await mystats_command(update, context)
            return

        if data == "admin_panel":
            from handlers.admin_panel import admin_panel
            await admin_panel(update, context)
            return

        if data == "go_home":
            from handlers.start import start_command
            await start_command(update, context)
            return

        # Channel panel routes
        if data.startswith("cp_"):
            from handlers.channel_manage import handle_channel_callback
            await handle_channel_callback(update, context)
            return

        # Admin panel routes
        if data.startswith("admin_"):
            from handlers.admin_panel import handle_admin_callback
            await handle_admin_callback(update, context)
            return

        # Admin sub-panel callbacks
        admin_panels = ["stats_panel", "broadcast_panel", "joinreq_panel", "channels_panel",
                        "templates_panel", "autoposter_panel", "usermgmt_panel", "settings_panel",
                        "toggle_auto_approve", "export_users", "edit_welcome_msg",
                        "lookup_user", "ban_user"]
        if data in admin_panels:
            from handlers.admin_panel import handle_admin_callback
            await handle_admin_callback(update, context)
            return

        # Language settings
        if data.startswith("set_lang_"):
            await handle_set_language(update, context)
            return

        if data == "set_language":
            await show_language_selection(update, context)
            return

        # Mandatory channels
        if data == "set_mandatory":
            await show_mandatory_channels(update, context)
            return

        if data.startswith("rm_mandatory_"):
            await remove_mandatory_channel_cb(update, context)
            return

        # Welcome message
        if data == "set_welcome":
            await set_welcome_prompt(update, context, "global")
            return

        if data.startswith("set_welcome_"):
            channel_id = int(data.split("_", 2)[2])
            await set_welcome_prompt(update, context, channel_id)
            return

        # Mandatory channel check
        if data == "check_mandatory":
            await check_mandatory_channels(update, context)
            return

        # Settings menu
        if data == "cp_settings":
            await show_settings(update, context)
            return

        await query.answer("\u2754 Unknown action")
    except Exception as e:
        logger.error(f"Callback error for {data}: {e}")
        import traceback
        traceback.print_exc()
        try:
            await query.answer(f"\u274c Error: {str(e)[:50]}", show_alert=True)
        except:
            pass

async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    lang = await db.get_user_language(user_id)
    lang_name = LANGUAGES.get(lang, "? " + lang)

    # Get welcome message preview
    welcome = await db.get_bot_setting("welcome_message", "Not set")
    welcome_preview = (welcome[:50] + "...") if len(welcome) > 50 else welcome

    text = (
        "\u2699\ufe0f <b>Settings</b>\n\n"
        f"\ud83c\udf10 <b>Language:</b> {lang_name}\n"
        f"\ud83d\udc4b <b>Welcome:</b> {welcome_preview}\n"
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("\ud83c\udf10 Language", callback_data="set_language")],
        [InlineKeyboardButton("\ud83d\udc4b Welcome Message", callback_data="set_welcome")],
        [InlineKeyboardButton("\ud83d\udce2 Mandatory Channels", callback_data="set_mandatory")],
        [InlineKeyboardButton("\ud83d\udd19 Back", callback_data="cp_main")],
    ])

    try:
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await query.message.reply_text(text, parse_mode="HTML", reply_markup=kb)

async def show_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    current_lang = await db.get_user_language(user_id)

    buttons = []
    for code, name in LANGUAGES.items():
        marker = " \u2705" if code == current_lang else ""
        buttons.append([InlineKeyboardButton(f"{name}{marker}", callback_data=f"set_lang_{code}")])
    buttons.append([InlineKeyboardButton("\ud83d\udd19 Back", callback_data="cp_settings")])

    kb = InlineKeyboardMarkup(buttons)
    try:
        await query.edit_message_text(
            "\ud83c\udf10 <b>Select Language</b>\n\nChoose your preferred language:",
            parse_mode="HTML", reply_markup=kb
        )
    except Exception:
        await query.message.reply_text(
            "\ud83c\udf10 <b>Select Language</b>\n\nChoose your preferred language:",
            parse_mode="HTML", reply_markup=kb
        )

async def handle_set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    lang_code = query.data.replace("set_lang_", "")

    if lang_code not in LANGUAGES:
        await query.answer("\u274c Invalid language")
        return

    user_id = query.from_user.id
    await db.set_user_language(user_id, lang_code)
    await query.answer(f"\u2705 Language set to {LANGUAGES[lang_code]}")

    # Refresh the language selection screen
    await show_language_selection(update, context)

async def show_mandatory_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if user_id not in ADMIN_IDS:
        await query.answer("\u274c Admin only", show_alert=True)
        return

    channels = await db.get_mandatory_channels()

    if not channels:
        text = (
            "\ud83d\udce2 <b>Mandatory Channels</b>\n\n"
            "No mandatory channels set.\n\n"
            "Use <code>/addmandatory &lt;channel_id&gt; [@username]</code> to add one."
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("\ud83d\udd19 Back", callback_data="cp_settings")]])
    else:
        lines = ["\ud83d\udce2 <b>Mandatory Channels</b>\n"]
        buttons = []
        for ch in channels:
            title = ch.get("title") or str(ch["channel_id"])
            un = ch.get("username") or ""
            lines.append(f"\u25ab <b>{title}</b> {un}")
            buttons.append([InlineKeyboardButton(f"\u274c Remove {title}", callback_data=f"rm_mandatory_{ch['channel_id']}")])
        lines.append("\nUse <code>/addmandatory &lt;id&gt; [@username]</code> to add more.")
        text = "\n".join(lines)
        buttons.append([InlineKeyboardButton("\ud83d\udd19 Back", callback_data="cp_settings")])
        kb = InlineKeyboardMarkup(buttons)

    try:
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await query.message.reply_text(text, parse_mode="HTML", reply_markup=kb)

async def remove_mandatory_channel_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if user_id not in ADMIN_IDS:
        await query.answer("\u274c Admin only", show_alert=True)
        return

    channel_id = int(query.data.replace("rm_mandatory_", ""))
    await db.remove_mandatory_channel(channel_id)
    await query.answer("\u2705 Removed!")
    await show_mandatory_channels(update, context)

async def set_welcome_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id):
    query = update.callback_query
    user_id = query.from_user.id
    if user_id not in ADMIN_IDS:
        await query.answer("\u274c Admin only", show_alert=True)
        return
    await query.answer()

    context.user_data["set_welcome_chat_id"] = chat_id
    label = "global" if chat_id == "global" else f"channel {chat_id}"

    # Get current welcome
    if chat_id == "global":
        current = await db.get_bot_setting("welcome_message", "Not set")
    else:
        ch = await db.get_channel(chat_id)
        current = (ch or {}).get("welcome_message") or "Not set"

    back_cb = "cp_settings" if chat_id == "global" else f"cp_ch_{chat_id}"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("\ud83d\udd19 Cancel", callback_data=back_cb)]])

    try:
        await query.edit_message_text(
            f"\ud83d\udc4b <b>Welcome Message</b> ({label})\n\n"
            f"<b>Current:</b>\n{current}\n\n"
            f"Send me the new welcome message, or /cancel",
            parse_mode="HTML", reply_markup=kb
        )
    except Exception:
        await query.message.reply_text(
            f"\ud83d\udc4b <b>Welcome Message</b> ({label})\n\n"
            f"<b>Current:</b>\n{current}\n\n"
            f"Send me the new welcome message, or /cancel",
            parse_mode="HTML", reply_markup=kb
        )

async def check_mandatory_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    channels = await db.get_mandatory_channels()
    if not channels:
        await query.answer("\u2705 No mandatory channels!")
        return

    not_joined = []
    for ch in channels:
        try:
            member = await context.bot.get_chat_member(ch["channel_id"], user_id)
            if member.status in ("left", "kicked"):
                not_joined.append(ch)
        except:
            not_joined.append(ch)

    if not not_joined:
        await query.answer("\u2705 You've joined all required channels!", show_alert=True)
        await query.edit_message_text(
            "\u2705 <b>All done!</b>\n\nYou've joined all required channels.",
            parse_mode="HTML"
        )
    else:
        buttons = []
        for ch in not_joined:
            title = ch.get("title") or str(ch["channel_id"])
            un = ch.get("username")
            if un:
                url = f"https://t.me/{un.lstrip('@')}"
                buttons.append([InlineKeyboardButton(f"\ud83d\udce2 Join {title}", url=url)])
            else:
                buttons.append([InlineKeyboardButton(f"\ud83d\udce2 {title} (no link)", callback_data="noop")])
        buttons.append([InlineKeyboardButton("\u2705 Check Again", callback_data="check_mandatory")])
        kb = InlineKeyboardMarkup(buttons)
        await query.answer(f"\u274c Please join {len(not_joined)} channel(s)", show_alert=True)
        try:
            await query.edit_message_text(
                f"\u274c <b>Please join these channels:</b>\n\n"
                f"You must join {len(not_joined)} channel(s) to continue.",
                parse_mode="HTML", reply_markup=kb
            )
        except Exception:
            await query.message.reply_text(
                f"\u274c <b>Please join these channels:</b>\n\n"
                f"You must join {len(not_joined)} channel(s) to continue.",
                parse_mode="HTML", reply_markup=kb
            )
