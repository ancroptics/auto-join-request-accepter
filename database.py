import asyncpg
import logging
import asyncio
from urllib.parse import urlparse
from config import DATABASE_URL

logger = logging.getLogger(__name__)
pool = None

def parse_db_url(url):
    try:
        parsed = urlparse(url)
        return dict(
            user=parsed.username,
            password=parsed.password,
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=parsed.path.lstrip("/")
        )
    except Exception:
        return None

async def get_pool():
    global pool
    if pool is None:
        params = parse_db_url(DATABASE_URL)
        if params:
            pool = await asyncpg.create_pool(**params, min_size=2, max_size=10, ssl='require')
        else:
            pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10, ssl='require')
    return pool

async def init_db():
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute(SCHEMA_SQL)
    logger.info("Database initialized")

async def save_user(user_id, username=None, first_name=None, referrer_id=None):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute(
            """INSERT INTO users (user_id, username, first_name, referrer_id, joined_at, last_active)
            VALUES ($1, $2, $3, $4, NOW(), NOW())
            ON CONFLICT (user_id) DO UPDATE SET username=$2, first_name=$3, last_active=NOW()""",
            user_id, username, first_name, referrer_id
        )

async def get_user(user_id):
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE user_id=$1", user_id)
        return dict(row) if row else None

async def get_user_stats():
    p = await get_pool()
    async with p.acquire() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM users")
        active = await conn.fetchval("SELECT COUNT(*) FROM users WHERE last_active > NOW() - INTERVAL '24 hours'")
        banned = await conn.fetchval("SELECT COUNT(*) FROM users WHERE is_banned=true")
        new_today = await conn.fetchval("SELECT COUNT(*) FROM users WHERE joined_at::date = CURRENT_DATE")
        return {"total": total, "active_24h": active, "banned": banned, "new_today": new_today}

async def get_join_request_stats():
    p = await get_pool()
    async with p.acquire() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM join_requests")
        approved_today = await conn.fetchval("SELECT COUNT(*) FROM join_requests WHERE status='approved' AND created_at::date=CURRENT_DATE")
        pending = await conn.fetchval("SELECT COUNT(*) FROM join_requests WHERE status='pending'")
        return {"total": total or 0, "approved_today": approved_today or 0, "pending": pending or 0}

async def save_join_request(user_id, chat_id, status="pending"):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute(
            """INSERT INTO join_requests (user_id, chat_id, status, created_at)
            VALUES ($1, $2, $3, NOW()) ON CONFLICT DO NOTHING""",
            user_id, chat_id, status
        )

async def update_join_request_status(user_id, chat_id, status):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("UPDATE join_requests SET status=$1 WHERE user_id=$2 AND chat_id=$3", status, user_id, chat_id)

async def get_all_user_ids():
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch("SELECT user_id FROM users WHERE is_banned=false")
        return [r["user_id"] for r in rows]

async def get_new_user_ids(days=7):
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch("SELECT user_id FROM users WHERE is_banned=false AND joined_at > NOW() - INTERVAL '7 days'")
        return [r["user_id"] for r in rows]

async def get_active_user_ids(days=30):
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch("SELECT user_id FROM users WHERE is_banned=false AND last_active > NOW() - INTERVAL '30 days'")
        return [r["user_id"] for r in rows]

async def set_user_banned(user_id, banned=True):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("UPDATE users SET is_banned=$1 WHERE user_id=$2", banned, user_id)

async def increment_referral(user_id):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("UPDATE users SET referral_count = referral_count + 1 WHERE user_id=$1", user_id)

async def get_top_referrers(limit=10):
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch("SELECT user_id, first_name, username, referral_count FROM users ORDER BY referral_count DESC LIMIT $1", limit)
        return [dict(r) for r in rows]

async def get_daily_user_growth(days=7):
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch("SELECT joined_at::date as date, COUNT(*) as count FROM users WHERE joined_at > NOW() - INTERVAL '7 days' GROUP BY joined_at::date ORDER BY date")
        return [dict(r) for r in rows]

async def get_all_users_for_export():
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch("SELECT user_id, username, first_name, joined_at, referral_count, is_banned FROM users ORDER BY joined_at DESC")
        return [dict(r) for r in rows]

async def get_all_templates():
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM templates ORDER BY created_at DESC")
        return [dict(r) for r in rows]

async def save_template(name, content):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("INSERT INTO templates (name, content, created_at) VALUES ($1, $2, NOW()) ON CONFLICT (name) DO UPDATE SET content=$2", name, content)

async def delete_template(name):
    p = await get_pool()
    async with p.acquire() as conn:
        result = await conn.execute("DELETE FROM templates WHERE name=$1", name)
        return "DELETE 1" in result

async def get_template(name):
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM templates WHERE name=$1", name)
        return dict(row) if row else None

async def get_all_autoposter_jobs():
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM autoposter_jobs ORDER BY created_at DESC")
        return [dict(r) for r in rows]

async def save_autoposter_job(chat_id, interval_min, message):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute(
            """INSERT INTO autoposter_jobs (chat_id, interval_min, message, is_active, created_at)
            VALUES ($1, $2, $3, true, NOW()) ON CONFLICT (chat_id) DO UPDATE SET interval_min=$2, message=$3, is_active=true""",
            chat_id, interval_min, message)

async def delete_autoposter_job(chat_id):
    p = await get_pool()
    async with p.acquire() as conn:
        result = await conn.execute("DELETE FROM autoposter_jobs WHERE chat_id=$1", chat_id)
        return "DELETE 1" in result

async def save_channel(chat_id, chat_title, auto_approve=True):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute(
            """INSERT INTO channels (chat_id, chat_title, auto_approve, added_at)
            VALUES ($1, $2, $3, NOW()) ON CONFLICT (chat_id) DO UPDATE SET chat_title=$2, auto_approve=$3""",
            chat_id, chat_title, auto_approve)

async def get_all_channels():
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM channels ORDER BY added_at DESC")
        return [dict(r) for r in rows]

async def get_channel(chat_id):
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM channels WHERE chat_id=$1", chat_id)
        return dict(row) if row else None

async def update_last_active(user_id):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("UPDATE users SET last_active=NOW() WHERE user_id=$1", user_id)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY, username TEXT, first_name TEXT, referrer_id BIGINT,
    referral_count INTEGER DEFAULT 0, is_banned BOOLEAN DEFAULT false,
    joined_at TIMESTAMP DEFAULT NOW(), last_active TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS join_requests (
    id SERIAL PRIMARY KEY, user_id BIGINT, chat_id BIGINT, status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(), UNIQUE(user_id, chat_id)
);
CREATE TABLE IF NOT EXISTS channels (
    chat_id BIGINT PRIMARY KEY, chat_title TEXT, auto_approve BOOLEAN DEFAULT true,
    added_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS templates (
    name TEXT PRIMARY KEY, content TEXT, created_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS autoposter_jobs (
    chat_id BIGINT PRIMARY KEY, interval_min INTEGER DEFAULT 60, message TEXT,
    is_active BOOLEAN DEFAULT true, created_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS broadcasts (
    id SERIAL PRIMARY KEY, admin_id BIGINT, target TEXT, total INTEGER DEFAULT 0,
    sent INTEGER DEFAULT 0, failed INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS daily_stats (
    date DATE PRIMARY KEY, total_users INTEGER DEFAULT 0, active_users INTEGER DEFAULT 0,
    new_users INTEGER DEFAULT 0, total_referrals INTEGER DEFAULT 0, total_broadcasts INTEGER DEFAULT 0
);
"""
