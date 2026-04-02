import logging
import asyncio
import time
import traceback
import os

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

from config import ADMIN_IDS
start_time = time.time()
db_connected = False
bot_status = "starting"
bot_error = None
bot_username = None
CODE_VERSION = "v2.2-panel-fix"

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
                "error": bot_error,
                "version": CODE_VERSION
            }
            self.wfile.write(json_mod.dumps(data).encode())
        def log_message(self, format, *args):
            pass

    server = HTTPServer(("0.0.0.0", port), Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    logger.info(f"Health server running on port {port}")


async def self_ping_loop(port):
    import urllib.request
    url = f"http://localhost:{port}/"
    while True:
        await asyncio.sleep(240)
        try:
            urllib.request.urlopen(url, timeout=5)
            logger.info("Self-ping OK")
        except Exception as e:
            logger.warning(f"Self-ping failed: {e}")


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
        logger.error(f"Database init failed: {e}")
        traceback.print_exc()
    try:
        from services.scheduler_service import run_scheduler
        asyncio.create_task(run_scheduler(application.bot))
        logger.info("Scheduler started")
    except Exception as e:
        logger.error(f"Scheduler start failed: {e}")
    port = int(os.environ.get("PORT", "10000"))
    asyncio.create_task(self_ping_loop(port))
    logger.info("Self-ping keep-alive started (every 4 min)")
    bot_status = "polling"


async def handle_welcome_message_set(update, context):
    chat_id = context.user_data.get("set_welcome_chat_id")
    if not chat_id:
        return
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        if chat_id != "global":
            import database as dbc
            ch = await dbc.get_channel(chat_id)
            if not ch or ch.get("added_by") != user_id:
                return
        else:
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
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    user_id = update.effective_user.id
    is_admin = user_id in ADMIN_IDS
    buttons = [
        [InlineKeyboardButton("\U0001f4cb My Channels", callback_data="cp_channels_list")],
        [InlineKeyboardButton("\U0001f465 Pending Requests", callback_data="cp_pending_mine")],
        [InlineKeyboardButton("\u2699\ufe0f Settings", callback_data="cp_settings")],
    ]
    if is_admin:
        buttons.insert(2, [InlineKeyboardButton("\U0001f465 All Pending (Admin)", callback_data="cp_pending_overview")])
    buttons.append([InlineKeyboardButton("\U0001f3e0 Home", callback_data="go_home")])
    kb = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(
        "\U0001f39b <b>Control Panel</b>\n\nManage your channels, approve join requests, and configure settings.",
        parse_mode="HTML", reply_markup=kb
    )


async def addmandatory_command(update, context):
    if update.effective_user.id not in ADMIN_IDS:
        return
    args = context.args
    if not args or len(args) < 1:
        await update.message.reply_text(
            "\U0001f512 <b>Add Mandatory Channel</b>\n\nUsage: <code>/addmandatory &lt;channel_id&gt; &lt;@username&gt;</code>\n\nExample: <code>/addmandatory -1001234567890 @mychannel</code>",
            parse_mode="HTML"
        )
        return
    try:
        channel_id = int(args[0])
        username = args[1] if len(args) > 1 else None
        import database as db
        try:
            chat = await context.bot.get_chat(channel_id)
            title = chat.title or "Unknown"
            username = username or (f"@{chat.username}" if chat.username else None)
        except:
            title = "Unknown"
        await db.add_mandatory_channel(channel_id, title, username)
        await update.message.reply_text(
            f"\u2705 <b>Mandatory channel added!</b>\n\nID: <code>{channel_id}</code>\nTitle: {title}\nUsername: {username or 'N/A'}",
            parse_mode="HTML"
        )
    except ValueError:
        await update.message.reply_text("\u274c Invalid channel ID. Must be a number.")
    except Exception as e:
        await update.message.reply_text(f"\u274c Error: {e}")


async def admin_command(update, context):
    from handlers.admin_panel import admin_panel
    await admin_panel(update, context)


def main():
    try:
        from telegram.ext import Application, CommandHandler as CmdHandler, ChatJoinRequestHandler, ChatMemberHandler, CallbackQueryHandler, MessageHandler, filters
        from handlers.start import start_command
        from handlers.user_commands import referral_command, balance_command, leaderboard_command, mystats_command, help_command
        from handlers.join_request import handle_join_request
        from handlers.callbacks import callback_router
        from handlers.broadcast import get_broadcast_handler
        from handlers.templates import get_template_handler, del_template
        from handlers.user_mgmt import get_user_mgmt_handler
        from handlers.auto_poster import get_autoposter_handler, del_poster
        token = os.environ.get("BOT_TOKEN", "")
        if not token:
            logger.error("BOT_TOKEN not set!")
            return
        app = Application.builder().token(token).post_init(post_init).build()
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
        async def error_handler(update, context):
            logger.error(f"Exception: {context.error}", exc_info=context.error)
        app.add_error_handler(error_handler)
        port = int(os.environ.get("PORT", "10000"))
        run_health_server_in_thread(port)
        logger.info(f"Starting bot ({CODE_VERSION}) in polling mode...")
        app.run_polling(drop_pending_updates=True, allowed_updates=["message", "callback_query", "chat_join_request", "my_chat_member"])
    except Exception as e:
        global bot_status, bot_error
        bot_status = "error"
        bot_error = str(e)
        logger.critical(f"Bot failed to start: {e}")
        traceback.print_exc()
        port = int(os.environ.get("PORT", "10000"))
        run_health_server_in_thread(port)
        import signal
        signal.pause()

if __name__ == "__main__":
    main()
