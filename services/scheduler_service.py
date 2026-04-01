import logging
import asyncio
from datetime import datetime, timedelta
import database as db

logger = logging.getLogger(__name__)

async def auto_post_job(bot):
    try:
        schedules = await db.get_due_schedules()
        for s in schedules:
            try:
                await bot.send_message(chat_id=s["group_chat_id"], text=s["content"], parse_mode="HTML")
                next_post = datetime.utcnow() + timedelta(minutes=s["interval_minutes"])
                await db.update_schedule_posted(s["id"], next_post)
                logger.info(f"Auto-posted to {s['group_title']}")
            except Exception as e:
                logger.error(f"Auto-post failed for {s.get('group_title')}: {e}")
    except Exception as e:
        logger.error(f"Auto-post job error: {e}")

async def daily_stats_job():
    try:
        await db.record_daily_stats()
        logger.info("Daily stats recorded")
    except Exception as e:
        logger.error(f"Daily stats error: {e}")

async def run_scheduler(bot):
    while True:
        await auto_post_job(bot)
        await asyncio.sleep(60)
