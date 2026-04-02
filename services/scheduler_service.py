import logging
import asyncio
import database as db

logger = logging.getLogger(__name__)

async def run_scheduler(bot):
    logger.info("Auto-poster scheduler started")
    while True:
        try:
            if db.pool is not None:
                jobs = await db.get_active_posters()
                for job in jobs:
                    try:
                        # Look up template content
                        template = await db.get_template(job["template_name"])
                        message = template["content"] if template else job.get("template_name", "")
                        await bot.send_message(
                            chat_id=job["channel_id"],
                            text=message,
                            parse_mode="HTML"
                        )
                        await db.update_poster_last_post(job["id"])
                        logger.info(f"Auto-posted to {job['channel_id']}")
                    except Exception as e:
                        logger.error(f"Auto-post failed for {job['channel_id']}: {e}")
        except Exception as e:
            logger.error(f"Scheduler error: {e}")

        await asyncio.sleep(60)
