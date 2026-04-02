import logging
import asyncio
import database as db

logger = logging.getLogger(__name__)

async def run_scheduler(bot):
    logger.info("Auto-poster scheduler started")
    while True:
        try:
            if db._pool is not None:
                jobs = await db.get_all_autoposter_jobs()
                for job in jobs:
                    if job.get("is_active"):
                        try:
                            await bot.send_message(
                                chat_id=job["chat_id"],
                                text=job["message"],
                                parse_mode="HTML"
                            )
                            logger.info(f"Auto-posted to {job['chat_id']}")
                        except Exception as e:
                            logger.error(f"Auto-post failed for {job['chat_id']}: {e}")
        except Exception as e:
            logger.error(f"Scheduler error: {e}")

        # Sleep for minimum interval (check every 60 seconds)
        await asyncio.sleep(60)
