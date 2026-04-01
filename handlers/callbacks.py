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
                referrals = await db.get_referral_count(user_id)
                coins = await db.get_coins(user_id)
                rank = await db.get_user_rank(user_id)
            else:
                referrals, coins, rank = 0, 0, "N/A"
            text = (
                f"\U0001f4ca <b>Your Stats</b>\n\n"
                f"\U0001f465 Referrals: <b>{referrals}</b>\n"
                f"\U0001f4b0 Coins: <b>{coins}</b>\n"
                f"\U0001f3c6 Rank: <b>#{rank}</b>"
            )
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="go_home")]])
            await query.answer()
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)

        elif data == "go_home":
            from handlers.start import start_command
            await start_command(update, context)

        elif data == "admin_panel":
            if user_id not in ADMIN_IDS:
                await query.answer("Unauthorized", show_alert=True)
                return
            from handlers.admin_panel import admin_panel
            await admin_panel(update, context)

        elif data == "admin_stats":
            if user_id not in ADMIN_IDS:
                await query.answer("Unauthorized", show_alert=True)
                return
            from handlers.admin_panel import show_stats
            await show_stats(update, context)

        elif data == "admin_join_requests":
            if user_id not in ADMIN_IDS:
                return
            from handlers.admin_panel import show_join_requests
            await show_join_requests(update, context)

        elif data == "admin_channels":
            if user_id not in ADMIN_IDS:
                return
            from handlers.admin_panel import show_channels
            await show_channels(update, context)

        elif data.startswith("ch_toggle_"):
            if user_id not in ADMIN_IDS:
                return
            chat_id = int(data.replace("ch_toggle_", ""))
            new_val = await db.toggle_channel_auto_approve(chat_id)
            await query.answer(f"Auto-approve: {'ON' if new_val else 'OFF'}")
            from handlers.admin_panel import show_channels
            await show_channels(update, context)

        elif data.startswith("ch_welcome_"):
            if user_id not in ADMIN_IDS:
                return
            chat_id = int(data.replace("ch_welcome_", ""))
            context.user_data["set_welcome_chat_id"] = chat_id
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="admin_channels")]])
            await query.answer()
            await query.edit_message_text(
                "\U0001f4dd Send the welcome message for this channel.\nSupports HTML formatting.\n\nSend /cancel to abort.",
                reply_markup=kb
            )

        elif data.startswith("ch_delete_"):
            if user_id not in ADMIN_IDS:
                return
            chat_id = int(data.replace("ch_delete_", ""))
            await db.delete_channel(chat_id)
            await query.answer("Channel removed!")
            from handlers.admin_panel import show_channels
            await show_channels(update, context)

        elif data == "admin_templates":
            if user_id not in ADMIN_IDS:
                return
            from handlers.admin_panel import show_templates
            await show_templates(update, context)

        elif data == "admin_autoposter":
            if user_id not in ADMIN_IDS:
                return
            from handlers.admin_panel import show_autoposter
            await show_autoposter(update, context)

        elif data == "admin_user_mgmt":
            if user_id not in ADMIN_IDS:
                return
            from handlers.admin_panel import show_user_mgmt
            await show_user_mgmt(update, context)

        elif data == "admin_settings":
            if user_id not in ADMIN_IDS:
                return
            from handlers.admin_panel import show_settings
            await show_settings(update, context)

        elif data.startswith("toggle_setting_"):
            if user_id not in ADMIN_IDS:
                return
            key = data.replace("toggle_setting_", "")
            settings = await db.get_bot_settings()
            new_val = not settings.get(key, True)
            await db.update_bot_setting(key, new_val)
            await query.answer(f"{key}: {'ON' if new_val else 'OFF'}")
            from handlers.admin_panel import show_settings
            await show_settings(update, context)

        elif data == "admin_broadcast":
            if user_id not in ADMIN_IDS:
                return
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("\U0001f4e2 All Users", callback_data="broadcast_all")],
                [InlineKeyboardButton("\U0001f195 New (7d)", callback_data="broadcast_new"),
                 InlineKeyboardButton("\U0001f525 Active (30d)", callback_data="broadcast_active")],
                [InlineKeyboardButton("\U0001f519 Back", callback_data="admin_panel")]
            ])
            await query.answer()
            await query.edit_message_text("\U0001f4e3 <b>Broadcast</b>\n\nChoose target audience:", parse_mode="HTML", reply_markup=kb)

        elif data == "admin_referrals":
            if user_id not in ADMIN_IDS:
                return
            total_refs = await db.get_total_referrals()
            top = await db.get_top_referrer()
            leaderboard = await db.get_leaderboard(5)
            text = f"\U0001f4ca <b>Referral Stats</b>\n\nTotal referrals: <b>{total_refs}</b>\n"
            if top:
                text += f"Top referrer: {top.get('first_name', 'Unknown')} ({top.get('referral_count', 0)})\n"
            if leaderboard:
                text += "\n<b>Leaderboard:</b>\n"
                for i, u in enumerate(leaderboard, 1):
                    text += f"{i}. {u.get('first_name', 'Unknown')} - {u.get('referral_count', 0)} refs\n"
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data="admin_panel")]])
            await query.answer()
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)

        elif data == "admin_export":
            if user_id not in ADMIN_IDS:
                return
            await query.answer("Exporting...")
            users = await db.get_all_users_for_export()
            import io
            output = io.StringIO()
            output.write("user_id,username,first_name,joined_at,referrals,coins,banned\n")
            for u in users:
                output.write(f"{u['user_id']},{u.get('username','')},{u.get('first_name','')},{u.get('joined_at','')},{u.get('referral_count',0)},{u.get('coins',0)},{u.get('is_banned',False)}\n")
            output.seek(0)
            from telegram import InputFile
            await context.bot.send_document(
                chat_id=user_id,
                document=InputFile(io.BytesIO(output.getvalue().encode()), filename="users_export.csv"),
                caption=f"\U0001f4e5 Exported {len(users)} users"
            )

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
