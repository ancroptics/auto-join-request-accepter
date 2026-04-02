import logging
import asyncio
import time
import traceback

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

start_time = time.time()
db_connected = False
bot_status = "starting"
bot_error = None
bot_username = None

def run_health_server_in_thread(port):
    import threading
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import json as json_mod

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            data = {
                "status": bot_status,
                "uptime": int(time.time() - start_time),
                "db": db_connected,
                "bot_username": bot_username,
                "error": bot_error
            }
            self.wfile.write(json_mod.dumps(data).encode())
        def log_message(self, format, *args):
            pass

    server = HTTPServer(("0.0.0.0", port), Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    logger.info(f"Health server running on port {port}")

async def post_init(application):
    global db_connected, bot_status, bot_username
    try:
        me = await application.bot.get_me()
        bot_username = me.username
        logger.info(f"Bot authenticated as @{bot_username}")
    except Exception as e:
        logger.error(f"Bot auth check failed: {e}")

    try:
        import database as db
        await db.init_db()
        db_connected = True
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database init failed (bot will run without DB): {e}")
        traceback.print_exc()

    try:
        from services.scheduler_service import run_scheduler
        asyncio.create_task(run_scheduler(application.bot))
        logger.info("Scheduler started")
    except Exception as e:
        logger.error(f"Scheduler start failed: {e}")

    bot_status = "polling"

async def handle_welcome_message_set(update, context):
    chat_id = context.user_data.get("set_welcome_chat_id")
    if not chat_id:
        return
    from config import ADMIN_IDS
    if update.effective_user.id not in ADMIN_IDS:
        return
    welcome_text = update.message.text
    if welcome_text == "/cancel":
        del context.user_data["set_welcome_chat_id"]
        await update.message.reply_text("\u274c Cancelled.")
        return
    import database as db
    try:
        if chat_id == "global":
            await db.update_bot_setting("welcome_message", welcome_text)
        else:
            await db.update_channel_welcome(chat_id, welcome_text)
        del context.user_data["set_welcome_chat_id"]
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        back_cb = "cp_settings" if chat_id == "global" else f"cp_ch_{chat_id}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f519 Back", callback_data=back_cb)]])
        await update.message.reply_text(
            f"\u2705 <b>Welcome message updated!</b>\n\n<b>Preview:</b>\n{welcome_text}",
            parse_mode="HTML", reply_markup=kb
        )
    except Exception as e:
        logger.error(f"Failed to update welcome: {e}")
        await update.message.reply_text(f"\u274c Error: {e}")

async def panel_command(update, context):
    """Open the channel control panel."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("\U0001f4cb My Channels", callback_data="cp_channels_list")],
        [InlineKeyboardButton("\U0001f465 Pending Requests", callback_data="cp_pending_all")],
        [InlineKeyboardButton("\u2699\ufe0f Settings", callback_data="cp_settings")],
    ])
    await update.message.reply_text(
        "\U0001f39b <b>Control Panel</b>\n\n"
        "Manage your channels, approve join requests, and configure settings.",
        parse_mode="HTML", reply_markup=kb
    )

async def addmandatory_command(update, context):
    """Add a mandatory channel. Usage: /addmandatory <channel_id> <@username>"""
    from config import ADMIN_IDS
    if update.effective_user.id not in ADMIN_IDS:
        return
    args = context.args
    if not args or len(args) < 1:
        await update.message.reply_text(
            "\U0001f512 <b>Add Mandatory Channel</b>\n\n"
            "Usage: <code>/addmandatory &lt;channel_id&gt; [@username]</code>\n\n"
            "Example: <code>/addmandatory -1001234567890 @mychannel</code>",
            parse_mode="HTML"
        )
        return
    import database as db
    try:
        chat_id = int(args[0])
        username = args[1] if len(args) > 1 else None
        # Try to get channel title
        title = None
        try:
            chat = await context.bot.get_chat(chat_id)
            title = chat.title
            if not username and chat.username:
                username = f"@{chat.username}"
        except:
            pass
        await db.add_mandatory_channel(chat_id, title, username)
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001f512 Mandatory Channels", callback_data="set_mandatory")]])
        await update.message.reply_text(
            f"\u2705 Added mandatory channel!\n\n"
            f"ID: <code>{chat_id}</code>\n"
            f"Title: {title or 'Unknown'}\n"
            f"Username: {username or 'N/A'}",
            parse_mode="HTML", reply_markup=kb
        )
    except ValueError:
        await update.message.reply_text("\u274c Invalid channel ID. Must be a number.")
    except Exception as e:
        await update.message.reply_text(f"\u274c Error: {e}")

async def admin_command(update, context):
    from handlers.admin_panel import admin_panel
    await admin_panel(update, context)

def main():
    global bot_status, bot_error
    import os
    port = int(os.environ.get("PORT", "10000"))
    from config import USE_WEBHOOK, WEBHOOK_URL
    if not (USE_WEBHOOK and WEBHOOK_URL):
        run_health_server_in_thread(port)
    else:
        logger.info(f"Webhook mode - skipping separate health server (webhook serves on port {port})")

    try:
        from telegram.ext import Application, CommandHandler as CmdHandler, ChatJoinRequestHandler, ChatMemberHandler, CallbackQueryHandler, MessageHandler, filters
        from config import BOT_TOKEN
        from handlers.start import start_command
        from handlers.user_commands import referral_command, balance_command, leaderboard_command, mystats_command, help_command
        from handlers.join_request import handle_join_request
        from handlers.callbacks import callback_router
        from handlers.broadcast import get_broadcast_handler
        from handlers.templates import get_template_handler, del_template
        from handlers.user_mgmt import get_user_mgmt_handler
        from handlers.auto_poster import get_autoposter_handler, del_poster

        logger.info(f"All imports successful. Token length: {len(BOT_TOKEN)}")
        bot_status = "building"

        app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

        app.add_handler(get_broadcast_handler())
        app.add_handler(get_template_handler())
        app.add_handler(get_user_mgmt_handler())
        app.add_handler(get_autoposter_handler())

        app.add_handler(CmdHandler("start", start_command))
        app.add_handler(CmdHandler("referral", referral_command))
        app.add_handler(CmdHandler("balance", balance_command))
        app.add_handler(CmdHandler("leaderboard", leaderboard_command))
        app.add_handler(CmdHandler("mystats", mystats_command))
        app.add_handler(CmdHandler("help", help_command))
        app.add_handler(CmdHandler("panel", panel_command))
        app.add_handler(CmdHandler("admin", admin_command))
        app.add_handler(CmdHandler("addmandatory", addmandatory_command))
        app.add_handler(CmdHandler("deltemplate", del_template))
        app.add_handler(CmdHandler("delposter", del_poster))

        from handlers.channel_manage import handle_my_chat_member
        app.add_handler(ChatMemberHandler(handle_my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))
        app.add_handler(ChatJoinRequestHandler(handle_join_request))
        app.add_handler(CallbackQueryHandler(callback_router))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_welcome_message_set))

        from config import USE_WEBHOOK, WEBHOOK_URL, PORT as WH_PORT

        if USE_WEBHOOK and WEBHOOK_URL:
            bot_status = "starting_webhook"
            logger.info(f"Starting webhook on port {WH_PORT} -> {WEBHOOK_URL}")
            app.run_webhook(
                listen="0.0.0.0",
                port=WH_PORT,
                url_path="webhook",
                webhook_url=f"{WEBHOOK_URL}/webhook",
                drop_pending_updates=True,
                allowed_updates=["message", "callback_query", "chat_join_request", "my_chat_member"],
            )
        else:
            bot_status = "starting_poll"
            logger.info("Starting polling...")
            app.run_polling(drop_pending_updates=True, allowed_updates=["message", "callback_query", "chat_join_request", "my_chat_member"])
    except Exception as e:
        bot_status = "crashed"
        bot_error = str(e)
        logger.error(f"Bot crashed: {e}")
        traceback.print_exc()
        while True:
            time.sleep(60)

if __name__ == "__main__":
    main()
