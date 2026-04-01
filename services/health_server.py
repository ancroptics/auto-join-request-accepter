import logging
import time
from aiohttp import web
from config import PORT, VERSION
import database as db

logger = logging.getLogger(__name__)
start_time = time.time()

async def health_handler(request):
    try:
        users = await db.get_user_count()
    except Exception:
        users = -1
    return web.json_response({"status": "running", "uptime": int(time.time() - start_time), "users": users, "version": VERSION})

async def index_handler(request):
    return web.Response(text="Telegram Growth Engine Bot is running!", status=200)

async def start_health_server(app_runner=None):
    app = web.Application()
    app.router.add_get("/", index_handler)
    app.router.add_get("/health", health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Health server running on port {PORT}")
    return runner
