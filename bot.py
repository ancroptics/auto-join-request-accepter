import logging
import asyncio
from telegram.ext import Application, CommandHandler, ChatJoinRequestHandler, CallbackQueryHandler
from config import BOT_TOKEN, USE_WEBHOOK, WEBHOOK_URL, PORT
import database as db
from handlers.start import start_command
from handlers.user_commands import referral_command, balance_command, leaderboard_command, mystats_command, help_command
from handlers.join_request import handle_join_request
from handlers.callbacks import callback_router
from handlers.broadcast import get_broadcast_handler
from services.health_server import start_health_server
from services.scheduler_service import run_scheduler, daily_stats_job

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def post_init(application):
    await db.init_db()
    logger.info("Database initialized")
    await start_health_server()
    logger.info("Health server started")
    asyncio.create_task(run_scheduler(application.bot))
    asyncio.create_task(daily_stats_loop())

async def daily_stats_loop():
    while True:
        await daily_stats_job()
        await asyncio.sleep(3600)

def main():
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

    logger.info("Bot starting...")
    if USE_WEBHOOK and WEBHOOK_URL:
        app.run_webhook(
            listen="0.0.0.0", port=PORT,
            webhook_url=f"{WEBHOOK_URL}/webhook",
            url_path="webhook"
        )
    else:
        app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
