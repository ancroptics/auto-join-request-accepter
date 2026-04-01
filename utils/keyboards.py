from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def admin_panel_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Statistics", callback_data="adm_stats"),
         InlineKeyboardButton("📢 Broadcast", callback_data="adm_broadcast")],
        [InlineKeyboardButton("📋 Join Requests", callback_data="adm_join_requests"),
         InlineKeyboardButton("📡 Channels", callback_data="adm_channels")],
        [InlineKeyboardButton("📝 Templates", callback_data="adm_templates"),
         InlineKeyboardButton("🤖 Auto Poster", callback_data="adm_autoposter")],
        [InlineKeyboardButton("👥 Users", callback_data="adm_users"),
         InlineKeyboardButton("⚙️ Settings", callback_data="adm_settings")],
    ])


def back_to_admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]
    ])


def confirm_cancel_keyboard(confirm_data, cancel_data="admin_panel"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirm", callback_data=confirm_data),
         InlineKeyboardButton("❌ Cancel", callback_data=cancel_data)]
    ])


def broadcast_target_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 All Users", callback_data="bc_all")],
        [InlineKeyboardButton("🆕 New (7 days)", callback_data="bc_new"),
         InlineKeyboardButton("🔥 Active (30d)", callback_data="bc_active")],
        [InlineKeyboardButton("❌ Cancel", callback_data="admin_panel")],
    ])


def channel_list_keyboard(channels):
    buttons = []
    for ch in channels:
        title = ch.get("chat_title", "Unknown")[:30]
        buttons.append([InlineKeyboardButton(f"📡 {title}", callback_data=f"ch_{ch['chat_id']}" )])
    buttons.append([InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")])
    return InlineKeyboardMarkup(buttons)


def user_mgmt_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Find User", callback_data="um_find"),
         InlineKeyboardButton("🚫 Ban User", callback_data="um_ban")],
        [InlineKeyboardButton("✅ Unban User", callback_data="um_unban"),
         InlineKeyboardButton("📤 Export Users", callback_data="um_export")],
        [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")],
    ])
