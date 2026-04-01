from functools import wraps
from config import ADMIN_IDS
import database as db

def admin_only(func):
    @wraps(func)
    async def wrapper(update, context):
        if update.effective_user.id not in ADMIN_IDS:
            return
        return await func(update, context)
    return wrapper

def track_user(func):
    @wraps(func)
    async def wrapper(update, context):
        user = update.effective_user
        if user:
            await db.upsert_user(user.id, user.username, user.first_name, user.last_name)
        return await func(update, context)
    return wrapper
