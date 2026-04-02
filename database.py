import logging
import asyncpg
import os
from urllib.parse import urlparse, unquote, quote

logger = logging.getLogger(__name__)
pool = None

def fix_database_url(url):
    if not url:
        return url
    parsed = urlparse(url)
    password = unquote(parsed.password or '')
    host = parsed.hostname
    port = parsed.port or 5432
    if host and 'db.' in host and '.supabase.co' in host:
        project_ref = host.replace('db.', '').replace('.supabase.co', '')
        pooler_host = 'aws-1-ap-northeast-1.pooler.supabase.com'
        port = 6543
        user = f'postgres.{project_ref}'
        encoded_pw = quote(password, safe='')
        new_url = f'postgresql://{user}:{encoded_pw}@{pooler_host}:{port}/{parsed.path.lstrip("/")}'
        logger.info(f'Converted to pooler URL: {pooler_host}:{port}')
        return new_url
    encoded_pw = quote(password, safe='')
    user = parsed.username or 'postgres'
    db_name = parsed.path.lstrip('/') or 'postgres'
    return f'postgresql://{user}:{encoded_pw}@{host}:{port}/{db_name}'

async def get_pool():
    global pool
    if pool is None:
        await init_db()
    return pool

async def init_db():
    global pool
    url = os.environ.get('DATABASE_URL', '')
    if not url:
        raise Exception('DATABASE_URL not set')
    fixed_url = fix_database_url(url)
    logger.info('Connecting to database...')
    pool = await asyncpg.create_pool(fixed_url, min_size=1, max_size=5, command_timeout=30)
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA_SQL)
    logger.info('Database connected and schema created')

async def upsert_user(user_id, username=None, first_name=None, last_name=None, referrer_id=None, source=None, created_via=None):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute(
            """INSERT INTO users (user_id, username, first_name, referrer_id, joined_at, last_active)
            VALUES ($1, $2, $3, $4, NOW(), NOW())
            ON CONFLICT (user_id) DO UPDATE SET username=$2, first_name=$3, last_active=NOW()""",
            user_id, username, first_name, referrer_id)

async def get_user(user_id):
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE user_id=$1", user_id)
        return dict(row) if row else None

async def get_user_count():
    p = await get_pool()
    async with p.acquire() as conn:
        return await conn.fetchval("SELECT COUNT(*) FROM users") or 0

async def get_active_count():
    p = await get_pool()
    async with p.acquire() as conn:
        return await conn.fetchval("SELECT COUNT(*) FROM users WHERE last_active > NOW() - INTERVAL '24 hours'") or 0

async def get_today_joins():
    p = await get_pool()
    async with p.acquire() as conn:
        return await conn.fetchval("SELECT COUNT(*) FROM users WHERE joined_at::date = CURRENT_DATE") or 0

async def get_week_joins():
    p = await get_pool()
    async with p.acquire() as conn:
        return await conn.fetchval("SELECT COUNT(*) FROM users WHERE joined_at > NOW() - INTERVAL '7 days'") or 0

async def get_month_joins():
    p = await get_pool()
    async with p.acquire() as conn:
        return await conn.fetchval("SELECT COUNT(*) FROM users WHERE joined_at > NOW() - INTERVAL '30 days'") or 0

async def get_active_24h():
    p = await get_pool()
    async with p.acquire() as conn:
        return await conn.fetchval("SELECT COUNT(*) FROM users WHERE last_active > NOW() - INTERVAL '24 hours'") or 0

async def get_active_7d():
    p = await get_pool()
    async with p.acquire() as conn:
        return await conn.fetchval("SELECT COUNT(*) FROM users WHERE last_active > NOW() - INTERVAL '7 days'") or 0

async def get_blocked_count():
    p = await get_pool()
    async with p.acquire() as conn:
        return await conn.fetchval("SELECT COUNT(*) FROM users WHERE is_banned=true") or 0

async def get_referral_count(user_id):
    p = await get_pool()
    async with p.acquire() as conn:
        return await conn.fetchval("SELECT referral_count FROM users WHERE user_id=$1", user_id) or 0

async def get_coins(user_id):
    p = await get_pool()
    async with p.acquire() as conn:
        return await conn.fetchval("SELECT coins FROM users WHERE user_id=$1", user_id) or 0

async def add_coins(user_id, amount):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("UPDATE users SET coins = coins + $1 WHERE user_id=$2", amount, user_id)

async def get_user_rank(user_id):
    p = await get_pool()
    async with p.acquire() as conn:
        rank = await conn.fetchval("SELECT COUNT(*)+1 FROM users WHERE referral_count > (SELECT COALESCE(referral_count,0) FROM users WHERE user_id=$1)", user_id)
        return rank or 'N/A'

async def get_leaderboard(limit=10):
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch("SELECT user_id, first_name, username, referral_count, coins FROM users ORDER BY referral_count DESC LIMIT $1", limit)
        return [dict(r) for r in rows]

async def get_total_referrals():
    p = await get_pool()
    async with p.acquire() as conn:
        return await conn.fetchval("SELECT COALESCE(SUM(referral_count),0) FROM users") or 0

async def get_top_referrer():
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users ORDER BY referral_count DESC LIMIT 1")
        return dict(row) if row else None

async def get_user_stats():
    p = await get_pool()
    async with p.acquire() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM users")
        active = await conn.fetchval("SELECT COUNT(*) FROM users WHERE last_active > NOW() - INTERVAL '24 hours'")
        banned = await conn.fetchval("SELECT COUNT(*) FROM users WHERE is_banned=true")
        return {"total": total or 0, "active_24h": active or 0, "banned": banned or 0}

async def get_all_active_users():
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch("SELECT user_id FROM users WHERE is_banned=false")
        return [dict(r) for r in rows]

async def get_all_user_ids():
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch("SELECT user_id FROM users WHERE is_banned=false")
        return [r['user_id'] for r in rows]

async def get_new_user_ids(days=7):
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch("SELECT user_id FROM users WHERE is_banned=false AND joined_at > NOW() - INTERVAL '7 days'")
        return [r['user_id'] for r in rows]

async def get_active_user_ids(days=30):
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch("SELECT user_id FROM users WHERE is_banned=false AND last_active > NOW() - INTERVAL '30 days'")
        return [r['user_id'] for r in rows]

async def ban_user(user_id):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("UPDATE users SET is_banned=true WHERE user_id=$1", user_id)

async def set_user_banned(user_id, banned=True):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("UPDATE users SET is_banned=$1 WHERE user_id=$2", banned, user_id)

async def increment_referral(user_id):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("UPDATE users SET referral_count = referral_count + 1 WHERE user_id=$1", user_id)

async def update_last_active(user_id):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("UPDATE users SET last_active=NOW() WHERE user_id=$1", user_id)

async def get_all_users_for_export():
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch("SELECT user_id, username, first_name, joined_at, referral_count, coins, is_banned FROM users ORDER BY joined_at DESC")
        return [dict(r) for r in rows]

async def log_join_request(user_id, chat_id, chat_title=None, status="approved", dm_sent=False):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute(
            """INSERT INTO join_requests (user_id, chat_id, chat_title, status, dm_sent, created_at)
            VALUES ($1, $2, $3, $4, $5, NOW()) ON CONFLICT (user_id, chat_id) DO UPDATE SET status=$4, dm_sent=$5""",
            user_id, chat_id, chat_title, status, dm_sent)

async def get_join_request_stats():
    p = await get_pool()
    async with p.acquire() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM join_requests") or 0
        approved = await conn.fetchval("SELECT COUNT(*) FROM join_requests WHERE status='approved'") or 0
        dm_sent = await conn.fetchval("SELECT COUNT(*) FROM join_requests WHERE dm_sent=true") or 0
        pending = await conn.fetchval("SELECT COUNT(*) FROM join_requests WHERE status='pending'") or 0
        today = await conn.fetchval("SELECT COUNT(*) FROM join_requests WHERE created_at::date=CURRENT_DATE") or 0
        return {"total": total, "approved": approved, "dm_sent": dm_sent, "pending": pending, "today": today}

async def get_recent_join_requests(limit=10):
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch("SELECT jr.*, u.first_name, u.username FROM join_requests jr LEFT JOIN users u ON jr.user_id=u.user_id ORDER BY jr.created_at DESC LIMIT $1", limit)
        return [dict(r) for r in rows]

async def save_join_request(user_id, chat_id, status="pending"):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("INSERT INTO join_requests (user_id, chat_id, status, created_at) VALUES ($1, $2, $3, NOW()) ON CONFLICT DO NOTHING", user_id, chat_id, status)

async def mark_dm_sent(user_id, chat_id, message_id=None):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("UPDATE join_requests SET dm_sent=true WHERE user_id=$1 AND chat_id=$2", user_id, chat_id)

async def upsert_channel(chat_id, chat_title, auto_approve=True):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute(
            """INSERT INTO channels (chat_id, chat_title, auto_approve, welcome_message, added_at)
            VALUES ($1, $2, $3, NULL, NOW())
            ON CONFLICT (chat_id) DO UPDATE SET chat_title=$2""",
            chat_id, chat_title, auto_approve)

async def save_channel(chat_id, chat_title, auto_approve=True):
    await upsert_channel(chat_id, chat_title, auto_approve)

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

async def get_channel_config(chat_id):
    return await get_channel(chat_id)

async def update_channel_welcome(chat_id, welcome_message):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("UPDATE channels SET welcome_message=$1 WHERE chat_id=$2", welcome_message, chat_id)

async def toggle_channel_auto_approve(chat_id):
    p = await get_pool()
    async with p.acquire() as conn:
        current = await conn.fetchval("SELECT auto_approve FROM channels WHERE chat_id=$1", chat_id)
        new_val = not current if current is not None else True
        await conn.execute("UPDATE channels SET auto_approve=$1 WHERE chat_id=$2", new_val, chat_id)
        return new_val

async def delete_channel(chat_id):
    p = await get_pool()
    async with p.acquire() as conn:
        result = await conn.execute("DELETE FROM channels WHERE chat_id=$1", chat_id)
        return "DELETE 1" in result

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

async def log_broadcast(admin_id, total, sent, failed, blocked, duration=0):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("INSERT INTO broadcasts (admin_id, target, total, sent, failed, created_at) VALUES ($1, 'all', $2, $3, $4, NOW())", admin_id, total, sent, failed)

async def get_broadcast_count():
    p = await get_pool()
    async with p.acquire() as conn:
        return await conn.fetchval("SELECT COUNT(*) FROM broadcasts") or 0

async def increment_broadcasts_received(user_id):
    pass

async def get_bot_settings():
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM bot_settings WHERE id=1")
        if row:
            return dict(row)
        return {"auto_approve": True, "welcome_dm": True, "referral_reward": 10}

async def update_bot_setting(key, value):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute(f"INSERT INTO bot_settings (id, {key}) VALUES (1, $1) ON CONFLICT (id) DO UPDATE SET {key}=$1", value)


async def get_pending_count_for_channel(chat_id):
    p = await get_pool()
    async with p.acquire() as conn:
        return await conn.fetchval(
            "SELECT COUNT(*) FROM join_requests WHERE chat_id=$1 AND status='pending'", chat_id
        ) or 0

async def get_pending_requests_for_channel(chat_id, limit=50):
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            """SELECT jr.*, u.first_name, u.username FROM join_requests jr
            LEFT JOIN users u ON jr.user_id=u.user_id
            WHERE jr.chat_id=$1 AND jr.status='pending'
            ORDER BY jr.created_at ASC LIMIT $2""",
            chat_id, limit
        )
        return [dict(r) for r in rows]

async def update_join_request_status(user_id, chat_id, status):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute(
            "UPDATE join_requests SET status=$1 WHERE user_id=$2 AND chat_id=$3",
            status, user_id, chat_id
        )

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY, username TEXT, first_name TEXT, referrer_id BIGINT,
    referral_count INTEGER DEFAULT 0, coins INTEGER DEFAULT 0, is_banned BOOLEAN DEFAULT false,
    joined_at TIMESTAMP DEFAULT NOW(), last_active TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS join_requests (
    id SERIAL PRIMARY KEY, user_id BIGINT, chat_id BIGINT, chat_title TEXT,
    status TEXT DEFAULT 'pending', dm_sent BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(), UNIQUE(user_id, chat_id)
);
CREATE TABLE IF NOT EXISTS channels (
    chat_id BIGINT PRIMARY KEY, chat_title TEXT, auto_approve BOOLEAN DEFAULT true,
    welcome_message TEXT, added_at TIMESTAMP DEFAULT NOW()
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
CREATE TABLE IF NOT EXISTS bot_settings (
    id INTEGER PRIMARY KEY DEFAULT 1,
    auto_approve BOOLEAN DEFAULT true,
    welcome_dm BOOLEAN DEFAULT true,
    referral_reward INTEGER DEFAULT 10
);
INSERT INTO bot_settings (id) VALUES (1) ON CONFLICT DO NOTHING;
"""
