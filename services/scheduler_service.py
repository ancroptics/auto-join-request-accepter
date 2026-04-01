import logging
import asyncio
import database as db

logger = logging.getLogger(__name__)

async def auto_post_job(bot):
    try:
        jobs = await db.get_all_autoposter_jobs()
        for j in jobs:
            if not j.get("is_active"):
                continue
            try:
                await bot.send_message(chat_id=j["chat_id"], text=j["message"], parse_mode="HTML")
                logger.info(f"Auto-posted to {j['chat_id']}")
            except Exception as e:
                logger.error(f"Auto-post failed for {j['chat_id']}: {e}")
    except Exception as e:
        logger.error(f"Auto-post job error: {e}")

async def run_scheduler(bot):
    while True:
        await auto_post_job(bot)
        await asyncio.sleep(300)
