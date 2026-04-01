import logging
import asyncio
from telegram.ext import ContextTypes
import database as db

logger = logging.getLogger(__name__)


async def broadcast_message(bot, text, target="all", parse_mode="HTML"):
    if target == "all":
        users = await db.get_all_user_ids()
    elif target == "new":
        users = await db.get_new_user_ids(days=7)
    elif target == "active":
        users = await db.get_active_user_ids(days=30)
    else:
        users = await db.get_all_user_ids()

    total = len(users)
    sent = 0
    failed = 0
    blocked = 0

    for uid in users:
        try:
            await bot.send_message(chat_id=uid, text=text, parse_mode=parse_mode)
            sent += 1
        except Exception as e:
            err = str(e).lower()
            if "blocked" in err or "deactivated" in err:
                blocked += 1
                await db.set_user_banned(uid, True)
            else:
                failed += 1
            logger.debug(f"Broadcast fail {uid}: {e}")
        if sent % 25 == 0:
            await asyncio.sleep(1)

    return {
        "total": total,
        "sent": sent,
        "failed": failed,
        "blocked": blocked,
    }
