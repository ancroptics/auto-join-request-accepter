import logging
from telegram import Update
from telegram.ext import ContextTypes
from handlers.admin_panel import admin_panel, stats_panel
from handlers.templates import templates_menu
from handlers.user_mgmt import users_menu, export_users
from handlers.auto_poster import autoposter_menu, ap_view_groups

logger = logging.getLogger(__name__)

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    if data == "admin_panel":
        await admin_panel(update, context)
    elif data == "adm_stats":
        await stats_panel(update, context)
    elif data == "adm_templates":
        await templates_menu(update, context)
    elif data == "adm_users":
        await users_menu(update, context)
    elif data == "adm_autoposter":
        await autoposter_menu(update, context)
    elif data == "ap_groups":
        await ap_view_groups(update, context)
    elif data == "um_export":
        await export_users(update, context)
    elif data == "my_referral":
        await query.answer("Use /referral command", show_alert=False)
    elif data == "my_stats":
        await query.answer("Use /mystats command", show_alert=False)
    elif data in ("adm_join_requests", "adm_channels", "adm_settings"):
        await query.answer("Coming soon!", show_alert=True)
    else:
        await query.answer()
