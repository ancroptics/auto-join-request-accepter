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

def run_health_server_in_thread(port):
    import threading
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import json as json_mod

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            data = {"status": "running", "uptime": int(time.time() - start_time), "db": db_connected}
            self.wfile.write(json_mod.dumps(data).encode())
        def log_message(self, format, *args):
            pass

    server = HTTPServer(("0.0.0.0", port), Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    logger.info(f"Health server running on port {port}")

async def post_init(application):
    global db_connected
    try:
        import database as db
        await db.init_db()
        db_connected = True
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database init failed (bot will run without DB): {e}")
        traceback.print_exc()

def main():
    import os
    port = int(os.environ.get("PORT", "10000"))

    # Start health server immediately
    run_health_server_in_thread(port)

    from telegram.ext import Application, CommandHandler, ChatJoinRequestHandler, CallbackQueryHandler
    from config import BOT_TOKEN
    from handlers.start import start_command
    from handlers.user_commands import referral_command, balance_command, leaderboard_command, mystats_command, help_command
    from handlers.join_request import handle_join_request
    from handlers.callbacks import callback_router
    from handlers.broadcast import get_broadcast_handler

    logger.info("All imports successful")

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(get_broadcast_handler())
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("referral", referral_command))
    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("leaderboard", leaderboard_command))
    app.add_handler(CommandHandler("mystats", mystats_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(ChatJoinRequestHandler(handle_join_request))
    app.add_handler(CallbackQueryHandler(callback_router))

    logger.info("Starting polling...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
