import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import ADMIN_IDS, BOT_USERNAME, REFERRAL_REWARD_COINS
import database as db

logger = logging.getLogger(__name__)

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    try:
        # ===== USER CALLBACKS =====
        if data == "my_referral":
            link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
            text = (
                f"\U0001f517 <b>Your Referral Link</b>\n\n"
                f"<code>{link}</code>\n\n"
                f"Share this link to earn <b>{REFERRAL_REWARD_COINS} coins</b> per new user!"
            )
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="go_home")]])
            await query.answer()
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)

        elif data == "my_stats":
            if db.pool:
                try:
                    referrals = await db.get_referral_count(user_id)
                    coins = await db.get_coins(user_id)
                    rank = await db.get_user_rank(user_id)
                except:
                    referrals, coins, rank = 0, 0, "N/A"
            else:
                referrals, coins, rank = 0, 0, "N/A"
            text = (
                f"\U0001f4ca <b>Your Stats</b>\n\n"
                f"\U0001f465 Referrals: <b>{referrals}</b>\n"
                f"\U0001f4b0 Coins: <b>{coins}</b>\n"
                f"\U0001f3c6 Rank: <b>#{rank}</b>"
            )
            if not db.pool:
                text += "\n\n\u26a0\ufe0f Database offline - stats may be inaccurate"
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="go_home")]])
            await query.answer()
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)

        elif data == "go_home":
            from handlers.start import start_command
            await start_command(update, context)

        # ===== ADMIN PANEL =====
        elif data == "admin_panel":
            if user_id not in ADMIN_IDS:
                await query.answer("Unauthorized", show_alert=True)
                return
            from handlers.admin_panel import admin_panel
            await admin_panel(update, context)

        elif data == "stats_panel":
            if user_id not in ADMIN_IDS:
                await query.answer("Unauthorized", show_alert=True)
                return
            from handlers.admin_panel import stats_panel
            await stats_panel(update, context)

        elif data == "broadcast_panel":
            if user_id not in ADMIN_IDS:
                await query.answer("Unauthorized", show_alert=True)
                return
            from handlers.admin_panel import broadcast_panel
            await broadcast_panel(update, context)

        elif data == "joinreq_panel":
            if user_id not in ADMIN_IDS:
                await query.answer("Unauthorized", show_alert=True)
                return
            from handlers.admin_panel import joinreq_panel
            await joinreq_panel(update, context)

        elif data == "channels_panel":
            if user_id not in ADMIN_IDS:
                await query.answer("Unauthorized", show_alert=True)
                return
            from handlers.admin_panel import channels_panel
            await channels_panel(update, context)

        elif data == "templates_panel":
            if user_id not in ADMIN_IDS:
                await query.answer("Unauthorized", show_alert=True)
                return
            from handlers.admin_panel import templates_panel
            await templates_panel(update, context)

        elif data == "autoposter_panel":
            if user_id not in ADMIN_IDS:
                await query.answer("Unauthorized", show_alert=True)
                return
            from handlers.admin_panel import autoposter_panel
            await autoposter_panel(update, context)

        elif data == "usermgmt_panel":
            if user_id not in ADMIN_IDS:
                await query.answer("Unauthorized", show_alert=True)
                return
            from handlers.admin_panel import usermgmt_panel
            await usermgmt_panel(update, context)

        elif data == "settings_panel":
            if user_id not in ADMIN_IDS:
                await query.answer("Unauthorized", show_alert=True)
                return
            from handlers.admin_panel import settings_panel
            await settings_panel(update, context)

        elif data == "toggle_auto_approve":
            if user_id not in ADMIN_IDS:
                await query.answer("Unauthorized", show_alert=True)
                return
            from handlers.admin_panel import toggle_auto_approve
            await toggle_auto_approve(update, context)

        elif data == "edit_welcome_msg":
            if user_id not in ADMIN_IDS:
                await query.answer("Unauthorized", show_alert=True)
                return
            context.user_data["set_welcome_chat_id"] = "global"
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="joinreq_panel")]])
            await query.answer()
            await query.edit_message_text(
                "\U0001f4dd <b>Set Welcome Message</b>\n\n"
                "Send the welcome message for new join requests.\n"
                "Supports HTML formatting.\n\n"
                "Variables: {first_name}, {user_id}, {username}\n\n"
                "Send /cancel to abort.",
                parse_mode="HTML", reply_markup=kb
            )

        elif data == "export_users":
            if user_id not in ADMIN_IDS:
                await query.answer("Unauthorized", show_alert=True)
                return
            from handlers.admin_panel import export_users
            await export_users(update, context)

        elif data == "lookup_user":
            if user_id not in ADMIN_IDS:
                return
            await query.answer()
            await query.edit_message_text(
                "\U0001f50d <b>Lookup User</b>\n\nSend /userinfo &lt;user_id&gt; to look up a user.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="usermgmt_panel")]])
            )

        elif data == "ban_user":
            if user_id not in ADMIN_IDS:
                return
            await query.answer()
            await query.edit_message_text(
                "\U0001f6ab <b>Ban User</b>\n\nSend /ban &lt;user_id&gt; to ban a user.\nSend /unban &lt;user_id&gt; to unban.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="usermgmt_panel")]])
            )

        elif data == "set_language":
            if user_id not in ADMIN_IDS:
                return
            await query.answer("Language settings coming soon!", show_alert=True)

        elif data == "set_mandatory":
            if user_id not in ADMIN_IDS:
                return
            await query.answer("Mandatory channel settings coming soon!", show_alert=True)

        # ===== BROADCAST TARGETS =====
        elif data in ("broadcast_all", "broadcast_new", "broadcast_active"):
            if user_id not in ADMIN_IDS:
                return
            target = data.replace("broadcast_", "")
            context.user_data["broadcast_target"] = target
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("\u274c Cancel", callback_data="broadcast_panel")]])
            await query.answer()
            await query.edit_message_text(
                f"\U0001f4e3 <b>Broadcast to: {target.upper()}</b>\n\n"
                "Send the message you want to broadcast.\n"
                "Supports text, photo, video, document.\n\n"
                "Send /cancel to abort.",
                parse_mode="HTML", reply_markup=kb
            )

        # ===== CHANNEL-SPECIFIC =====
        elif data.startswith("ch_toggle_"):
            if user_id not in ADMIN_IDS:
                return
            chat_id = int(data.replace("ch_toggle_", ""))
            if db.pool:
                new_val = await db.toggle_channel_auto_approve(chat_id)
                status = "ON" if new_val else "OFF"
                await query.answer(f"Auto-approve: {status}")
            else:
                await query.answer("DB offline", show_alert=True)
            from handlers.admin_panel import channels_panel
            await channels_panel(update, context)

        elif data.startswith("ch_welcome_"):
            if user_id not in ADMIN_IDS:
                return
            chat_id = int(data.replace("ch_welcome_", ""))
            context.user_data["set_welcome_chat_id"] = chat_id
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="channels_panel")]])
            await query.answer()
            await query.edit_message_text(
                "\U0001f4dd Send the welcome message for this channel.\nSupports HTML formatting.\n\nSend /cancel to abort.",
                reply_markup=kb
            )

        elif data.startswith("ch_delete_"):
            if user_id not in ADMIN_IDS:
                return
            chat_id = int(data.replace("ch_delete_", ""))
            if db.pool:
                await db.delete_channel(chat_id)
                await query.answer("Channel removed!")
            else:
                await query.answer("DB offline", show_alert=True)
            from handlers.admin_panel import channels_panel
            await channels_panel(update, context)


        # ===== CHANNEL CONTROL PANEL =====
        elif data == "cp_main":
            from handlers.channel_manage import cp_main
            await cp_main(update, context)

        elif data == "cp_channels_list":
            from handlers.channel_manage import cp_channels_list
            await cp_channels_list(update, context)

        elif data == "cp_pending_all":
            from handlers.channel_manage import cp_pending_all
            await cp_pending_all(update, context)

        elif data == "cp_settings":
            from handlers.channel_manage import cp_settings
            await cp_settings(update, context)

        elif data.startswith("cp_ch_"):
            chat_id = int(data.replace("cp_ch_", ""))
            from handlers.channel_manage import cp_channel_detail
            await cp_channel_detail(update, context, chat_id)

        elif data.startswith("cp_approve_all_"):
            chat_id = int(data.replace("cp_approve_all_", ""))
            from handlers.channel_manage import cp_approve_all
            await cp_approve_all(update, context, chat_id)

        elif data.startswith("cp_approve_n_"):
            chat_id = int(data.replace("cp_approve_n_", ""))
            from handlers.channel_manage import cp_approve_n_ask
            await cp_approve_n_ask(update, context, chat_id)

        elif data.startswith("cp_approve_rand_"):
            chat_id = int(data.replace("cp_approve_rand_", ""))
            from handlers.channel_manage import cp_approve_rand_ask
            await cp_approve_rand_ask(update, context, chat_id)

        elif data.startswith("cp_do_approve_n_"):
            parts = data.replace("cp_do_approve_n_", "").rsplit("_", 1)
            chat_id = int(parts[0])
            count = int(parts[1])
            from handlers.channel_manage import cp_do_approve_n
            await cp_do_approve_n(update, context, chat_id, count)

        elif data.startswith("cp_do_approve_rand_"):
            parts = data.replace("cp_do_approve_rand_", "").rsplit("_", 1)
            chat_id = int(parts[0])
            count = int(parts[1])
            from handlers.channel_manage import cp_do_approve_rand
            await cp_do_approve_rand(update, context, chat_id, count)

        elif data.startswith("cp_toggle_"):
            chat_id = int(data.replace("cp_toggle_", ""))
            from handlers.channel_manage import cp_toggle_auto
            await cp_toggle_auto(update, context, chat_id)

        else:
            logger.warning(f"Unhandled callback: {data}")
            await query.answer("Unknown action")

    except Exception as e:
        logger.error(f"Callback error ({data}): {e}")
        import traceback
        traceback.print_exc()
        try:
            await query.answer(f"Error: {str(e)[:50]}", show_alert=True)
        except:
            pass
