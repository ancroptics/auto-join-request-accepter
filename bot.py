import logging
import asyncio
import os
from aiohttp import web
from telegram.ext import Application, CommandHandler, ChatJoinRequestHandler, CallbackQueryHandler
from config import BOT_TOKEN, USE_WEBHOOK, WEBHOOK_URL, PORT
import database as db
from handlers.start import start_command
from handlers.user_commands import referral_command, balance_command, leaderboard_command, mystats_command, help_command
from handlers.join_request import handle_join_request
from handlers.callbacks import callback_router
from handlers.broadcast import get_broadcast_handler
from services.scheduler_service import run_scheduler, daily_stats_job
import time

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

start_time = time.time()
db_connected = False

async def health_handler(request):
    try:
        if db_connected:
            users = await db.get_user_count()
        else:
            users = -1
    except Exception:
        users = -1
    return web.json_response({
        "status": "running",
        "uptime": int(time.time() - start_time),
        "users": users,
        "version": "1.0.0",
        "db": db_connected
    })

async def index_handler(request):
    return web.Response(text="Telegram Growth Engine Bot is running!", status=200)

async def start_health_server_standalone():
    app = web.Application()
    app.router.add_get("/", index_handler)
    app.router.add_get("/health", health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Health server running on port {PORT}")
    return runner

async def post_init(application):
    global db_connected
    try:
        await db.init_db()
        db_connected = True
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database init failed: {e}")
    asyncio.create_task(run_scheduler(application.bot))
    asyncio.create_task(daily_stats_loop())

async def daily_stats_loop():
    while True:
        try:
            await daily_stats_job()
        except Exception as e:
            logger.error(f"Daily stats error: {e}")
        await asyncio.sleep(3600)

async def main_async():
    # Start health server FIRST so Render sees the port binding
    await start_health_server_standalone()
    logger.info("Health server started, now starting bot...")

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

    logger.info("Bot starting polling...")
    async with app:
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        logger.info("Bot is running!")
        # Keep running forever
        stop_event = asyncio.Event()
        await stop_event.wait()

if __name__ == "__main__":
    asyncio.run(main_async())
