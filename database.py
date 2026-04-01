import asyncpg
import logging
import asyncio
from config import DATABASE_URL

logger = logging.getLogger(__name__)
pool = None

async def init_db():
    global pool
    for attempt in range(5):
        try:
            pool = await asyncpg.create_pool(
                DATABASE_URL + ("?sslmode=require" if "sslmode" not in DATABASE_URL else ""),
                min_size=2, max_size=10, command_timeout=30
            )
            await run_migrations()
            logger.info("Database connected")
            return
        except Exception as e:
            logger.error(f"DB connect attempt {attempt+1} failed: {e}")
            await asyncio.sleep(2 ** attempt)
    raise Exception("Could not connect to database")

async def run_migrations():
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA)

async def close_db():
    global pool
    if pool:
        await pool.close()

async def execute(query, *args):
    async with pool.acquire() as conn:
        return await conn.execute(query, *args)

async def fetch(query, *args):
    async with pool.acquire() as conn:
        return await conn.fetch(query, *args)

async def fetchrow(query, *args):
    async with pool.acquire() as conn:
        return await conn.fetchrow(query, *args)

async def fetchval(query, *args):
    async with pool.acquire() as conn:
        return await conn.fetchval(query, *args)

async def upsert_user(user_id, username, first_name, last_name=None, source="organic", referrer_id=None, created_via="start_command"):
    await execute("""
        INSERT INTO users (user_id, username, first_name, last_name, source, referrer_id, created_via)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (user_id) DO UPDATE SET
            username = COALESCE($2, users.username),
            first_name = COALESCE($3, users.first_name),
            last_name = COALESCE($4, users.last_name),
            last_active = NOW()
    """, user_id, username, first_name, last_name, source, referrer_id, created_via)

async def get_user(user_id):
    return await fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)

async def ban_user(user_id):
    await execute("UPDATE users SET is_banned = TRUE WHERE user_id = $1", user_id)

async def unban_user(user_id):
    await execute("UPDATE users SET is_banned = FALSE WHERE user_id = $1", user_id)

async def get_all_active_users():
    return await fetch("SELECT user_id FROM users WHERE is_banned = FALSE")

async def get_user_count():
    return await fetchval("SELECT COUNT(*) FROM users")

async def get_active_count():
    return await fetchval("SELECT COUNT(*) FROM users WHERE is_banned = FALSE")

async def get_blocked_count():
    return await fetchval("SELECT COUNT(*) FROM users WHERE is_banned = TRUE")

async def get_today_joins():
    return await fetchval("SELECT COUNT(*) FROM users WHERE joined_at >= CURRENT_DATE")

async def get_week_joins():
    return await fetchval("SELECT COUNT(*) FROM users WHERE joined_at >= CURRENT_DATE - INTERVAL '7 days'")

async def get_month_joins():
    return await fetchval("SELECT COUNT(*) FROM users WHERE joined_at >= CURRENT_DATE - INTERVAL '30 days'")

async def get_active_24h():
    return await fetchval("SELECT COUNT(*) FROM users WHERE last_active >= NOW() - INTERVAL '24 hours' AND is_banned = FALSE")

async def get_active_7d():
    return await fetchval("SELECT COUNT(*) FROM users WHERE last_active >= NOW() - INTERVAL '7 days' AND is_banned = FALSE")

async def increment_referral(referrer_id, coins):
    await execute("""
        UPDATE users SET referral_count = referral_count + 1, coins = coins + $2,
        tier = CASE
            WHEN referral_count + 1 >= 500 THEN '\ud83d\udc51 Legend'
            WHEN referral_count + 1 >= 100 THEN '\ud83d\udc8e Diamond'
            WHEN referral_count + 1 >= 25 THEN '\ud83e\udd47 Gold'
            WHEN referral_count + 1 >= 5 THEN '\ud83e\udd48 Silver'
            ELSE '\ud83e\udd49 Bronze'
        END
        WHERE user_id = $1
    """, referrer_id, coins)

async def get_leaderboard(limit=10):
    return await fetch("SELECT user_id, username, first_name, referral_count, coins, tier FROM users ORDER BY referral_count DESC LIMIT $1", limit)

async def increment_broadcasts_received(user_id):
    await execute("UPDATE users SET broadcasts_received = broadcasts_received + 1 WHERE user_id = $1", user_id)

async def log_join_request(user_id, chat_id, chat_title, status="approved", auto_approved=True):
    await execute("""
        INSERT INTO join_requests (user_id, chat_id, chat_title, status, approved_at, auto_approved)
        VALUES ($1, $2, $3, $4, NOW(), $5)
        ON CONFLICT (user_id, chat_id) DO UPDATE SET status = $4, approved_at = NOW()
    """, user_id, chat_id, chat_title, status, auto_approved)

async def mark_dm_sent(user_id, chat_id, message_id=None):
    await execute("""
        UPDATE join_requests SET dm_sent = TRUE, dm_sent_at = NOW(), dm_message_id = $3
        WHERE user_id = $1 AND chat_id = $2
    """, user_id, chat_id, message_id)

async def get_join_request_stats():
    total = await fetchval("SELECT COUNT(*) FROM join_requests")
    approved = await fetchval("SELECT COUNT(*) FROM join_requests WHERE status = 'approved'")
    dm_sent = await fetchval("SELECT COUNT(*) FROM join_requests WHERE dm_sent = TRUE")
    return {"total": total or 0, "approved": approved or 0, "dm_sent": dm_sent or 0}

async def log_referral(referrer_id, referred_id, coins):
    await execute("""
        INSERT INTO referral_log (referrer_id, referred_id, coins_awarded)
        VALUES ($1, $2, $3) ON CONFLICT DO NOTHING
    """, referrer_id, referred_id, coins)

async def get_total_referrals():
    return await fetchval("SELECT COUNT(*) FROM referral_log") or 0

async def get_top_referrer():
    return await fetchrow("SELECT username, referral_count FROM users ORDER BY referral_count DESC LIMIT 1")

async def log_broadcast(admin_id, total, sent, failed, blocked, duration):
    return await fetchval("""
        INSERT INTO broadcast_log (admin_id, total_target, sent_count, failed_count, blocked_count, duration_seconds)
        VALUES ($1, $2, $3, $4, $5, $6) RETURNING id
    """, admin_id, total, sent, failed, blocked, duration)

async def get_broadcast_count():
    return await fetchval("SELECT COUNT(*) FROM broadcast_log") or 0

async def save_template(name, content, buttons_json=None, created_by=None):
    await execute("""
        INSERT INTO message_templates (name, content, buttons_json, created_by)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (name) DO UPDATE SET content = $2, buttons_json = $3, updated_at = NOW()
    """, name, content, buttons_json, created_by)

async def get_template(name):
    return await fetchrow("SELECT * FROM message_templates WHERE name = $1", name)

async def list_templates():
    return await fetch("SELECT name, content FROM message_templates ORDER BY created_at DESC")

async def delete_template(name):
    await execute("DELETE FROM message_templates WHERE name = $1", name)

async def upsert_channel(chat_id, title, welcome_message=None, auto_approve=True):
    await execute("""
        INSERT INTO channel_config (chat_id, title, welcome_message, auto_approve)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (chat_id) DO UPDATE SET title = $2, welcome_message = COALESCE($3, channel_config.welcome_message), auto_approve = $4
    """, chat_id, title, welcome_message, auto_approve)

async def get_channel_config(chat_id):
    return await fetchrow("SELECT * FROM channel_config WHERE chat_id = $1", chat_id)

async def list_channels():
    return await fetch("SELECT * FROM channel_config ORDER BY added_at DESC")

async def add_auto_post_group(chat_id, title):
    await execute("""
        INSERT INTO auto_post_groups (chat_id, title) VALUES ($1, $2)
        ON CONFLICT (chat_id) DO UPDATE SET title = $2, is_active = TRUE
    """, chat_id, title)

async def get_auto_post_groups():
    return await fetch("SELECT * FROM auto_post_groups WHERE is_active = TRUE")

async def get_due_schedules():
    return await fetch("""
        SELECT s.*, g.chat_id as group_chat_id, g.title as group_title
        FROM auto_post_schedules s
        JOIN auto_post_groups g ON s.group_id = g.id
        WHERE s.is_active = TRUE AND g.is_active = TRUE AND s.next_post_at <= NOW()
    """)

async def update_schedule_posted(schedule_id, next_post_at):
    await execute("""
        UPDATE auto_post_schedules SET last_posted_at = NOW(), next_post_at = $2, post_count = post_count + 1 WHERE id = $1
    """, schedule_id, next_post_at)

async def record_daily_stats():
    total = await get_user_count()
    active = await get_active_count()
    new = await get_today_joins()
    jr = await fetchval("SELECT COUNT(*) FROM join_requests WHERE request_time >= CURRENT_DATE")
    refs = await fetchval("SELECT COUNT(*) FROM referral_log WHERE created_at >= CURRENT_DATE") or 0
    await execute("""
        INSERT INTO daily_stats (stat_date, total_users, active_users, new_users, join_requests, referrals)
        VALUES (CURRENT_DATE, $1, $2, $3, $4, $5)
        ON CONFLICT (stat_date) DO UPDATE SET total_users=$1, active_users=$2, new_users=$3, join_requests=$4, referrals=$5
    """, total, active, new, jr or 0, refs)

async def get_daily_stats(days=7):
    return await fetch("SELECT * FROM daily_stats ORDER BY stat_date DESC LIMIT $1", days)

SCHEMA = """
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY, username VARCHAR(255), first_name VARCHAR(255), last_name VARCHAR(255),
    joined_at TIMESTAMPTZ DEFAULT NOW(), last_active TIMESTAMPTZ DEFAULT NOW(),
    referrer_id BIGINT, referral_count INTEGER DEFAULT 0, coins INTEGER DEFAULT 0,
    tier VARCHAR(50) DEFAULT '\ud83e\udd49 Bronze', is_banned BOOLEAN DEFAULT FALSE, is_premium BOOLEAN DEFAULT FALSE,
    source VARCHAR(100) DEFAULT 'organic', tags TEXT[] DEFAULT '{}',
    total_messages INTEGER DEFAULT 0, broadcasts_received INTEGER DEFAULT 0,
    dm_sent BOOLEAN DEFAULT FALSE, join_request_approved BOOLEAN DEFAULT FALSE,
    channel_source VARCHAR(255), created_via VARCHAR(50) DEFAULT 'start_command'
);
CREATE INDEX IF NOT EXISTS idx_users_referrer ON users(referrer_id);
CREATE INDEX IF NOT EXISTS idx_users_banned ON users(is_banned);
CREATE INDEX IF NOT EXISTS idx_users_joined ON users(joined_at);
CREATE TABLE IF NOT EXISTS join_requests (
    id BIGSERIAL PRIMARY KEY, user_id BIGINT NOT NULL, chat_id BIGINT NOT NULL,
    chat_title VARCHAR(255), request_time TIMESTAMPTZ DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'pending', approved_at TIMESTAMPTZ,
    dm_sent BOOLEAN DEFAULT FALSE, dm_sent_at TIMESTAMPTZ, dm_message_id BIGINT,
    auto_approved BOOLEAN DEFAULT FALSE, UNIQUE(user_id, chat_id)
);
CREATE TABLE IF NOT EXISTS referral_log (
    id BIGSERIAL PRIMARY KEY, referrer_id BIGINT NOT NULL, referred_id BIGINT NOT NULL,
    coins_awarded INTEGER DEFAULT 0, created_at TIMESTAMPTZ DEFAULT NOW(), UNIQUE(referrer_id, referred_id)
);
CREATE TABLE IF NOT EXISTS broadcast_log (
    id BIGSERIAL PRIMARY KEY, admin_id BIGINT, total_target INTEGER,
    sent_count INTEGER DEFAULT 0, failed_count INTEGER DEFAULT 0, blocked_count INTEGER DEFAULT 0,
    duration_seconds FLOAT, created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS message_templates (
    id BIGSERIAL PRIMARY KEY, name VARCHAR(255) UNIQUE NOT NULL, content TEXT NOT NULL,
    buttons_json TEXT, created_by BIGINT, created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS channel_config (
    chat_id BIGINT PRIMARY KEY, title VARCHAR(255), welcome_message TEXT,
    welcome_buttons TEXT, auto_approve BOOLEAN DEFAULT TRUE, total_joins INTEGER DEFAULT 0,
    added_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS auto_post_groups (
    id BIGSERIAL PRIMARY KEY, chat_id BIGINT UNIQUE NOT NULL, title VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE, added_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS auto_post_schedules (
    id BIGSERIAL PRIMARY KEY, group_id BIGINT REFERENCES auto_post_groups(id),
    content TEXT NOT NULL, interval_minutes INTEGER DEFAULT 60, is_active BOOLEAN DEFAULT TRUE,
    last_posted_at TIMESTAMPTZ, next_post_at TIMESTAMPTZ DEFAULT NOW(),
    post_count INTEGER DEFAULT 0, created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS daily_stats (
    stat_date DATE PRIMARY KEY DEFAULT CURRENT_DATE, total_users INTEGER DEFAULT 0,
    active_users INTEGER DEFAULT 0, new_users INTEGER DEFAULT 0,
    join_requests INTEGER DEFAULT 0, referrals INTEGER DEFAULT 0
);
"""
