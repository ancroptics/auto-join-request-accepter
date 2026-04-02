import logging
import asyncio
import os

logger = logging.getLogger(__name__)

_pool = None

async def get_pool():
    global _pool
    if _pool is None:
        import asyncpg
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL not set")
        _pool = await asyncpg.create_pool(database_url, min_size=1, max_size=5)
    return _pool

async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                language TEXT DEFAULT 'en',
                referred_by BIGINT,
                balance INTEGER DEFAULT 0,
                referral_count INTEGER DEFAULT 0,
                is_banned BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                channel_id BIGINT PRIMARY KEY,
                title TEXT,
                username TEXT,
                auto_approve BOOLEAN DEFAULT TRUE,
                welcome_message TEXT,
                added_at TIMESTAMP DEFAULT NOW()
            );
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS join_requests (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                channel_id BIGINT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT NOW(),
                processed_at TIMESTAMP
            );
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS mandatory_channels (
                channel_id BIGINT PRIMARY KEY,
                title TEXT,
                username TEXT,
                added_at TIMESTAMP DEFAULT NOW()
            );
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS broadcasts (
                id SERIAL PRIMARY KEY,
                message_text TEXT,
                sent_count INTEGER DEFAULT 0,
                fail_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS auto_posters (
                id SERIAL PRIMARY KEY,
                channel_id BIGINT NOT NULL,
                template_name TEXT NOT NULL,
                interval_minutes INTEGER NOT NULL,
                last_post TIMESTAMP WITH TIME ZONE,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
    logger.info("Database tables initialized")

# ===================================
# User functions
# ===================================

async def get_or_create_user(user_id, username=None, first_name=None, referred_by=None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
        if row:
            return dict(row)
        await conn.execute(
            "INSERT INTO users (user_id, username, first_name, referred_by) VALUES ($1, $2, $3, $4) ON CONFLICT (user_id) DO NOTHING",
            user_id, username, first_name, referred_by
        )
        if referred_by:
            await conn.execute(
                "UPDATE users SET referral_count = referral_count + 1, balance = balance + 1 WHERE user_id = $1",
                referred_by
            )
        row = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
        return dict(row) if row else None

async def get_user(user_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
        return dict(row) if row else None

async def get_user_language(user_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT language FROM users WHERE user_id = $1", user_id)
        return row["language"] if row else "en"

async def set_user_language(user_id, language):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET language = $1 WHERE user_id = $2", language, user_id)

async def get_all_user_ids():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT user_id FROM users WHERE is_banned = FALSE")
        return [r["user_id"] for r in rows]

async def get_user_count():
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT COUNT(*) as c FROM users")
        return row["c"]

async def ban_user(user_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET is_banned = TRUE WHERE user_id = $1", user_id)

async def unban_user(user_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET is_banned = FALSE WHERE user_id = $1", user_id)

async def get_leaderboard(limit=10):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT user_id, username, first_name, referral_count FROM users ORDER BY referral_count DESC LIMIT $1",
            limit
        )
        return [dict(r) for r in rows]

# ===================================
# Channel functions
# ===================================

async def add_channel(channel_id, title=None, username=None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO channels (channel_id, title, username) VALUES ($1, $2, $3) ON CONFLICT (channel_id) DO UPDATE SET title = $2, username = $3",
            channel_id, title, username
        )

async def remove_channel(channel_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM channels WHERE channel_id = $1", channel_id)

async def get_all_channels():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM channels ORDER BY added_at DESC")
        return [dict(r) for r in rows]

async def get_channel(channel_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM channels WHERE channel_id = $1", channel_id)
        return dict(row) if row else None

async def toggle_auto_approve(channel_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT auto_approve FROM channels WHERE channel_id = $1", channel_id)
        if row:
            new_val = not row["auto_approve"]
            await conn.execute("UPDATE channels SET auto_approve = $1 WHERE channel_id = $2", new_val, channel_id)
            return new_val
        return None

async def update_channel_welcome(channel_id, welcome_message):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE channels SET welcome_message = $1 WHERE channel_id = $2",
            welcome_message, channel_id
        )

# ===================================
# Join request functions
# ===================================

async def add_join_request(user_id, channel_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO join_requests (user_id, channel_id, status) VALUES ($1, $2, 'pending')",
            user_id, channel_id
        )

async def get_pending_count_for_channel(channel_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT COUNT(*) as c FROM join_requests WHERE channel_id = $1 AND status = 'pending'",
            channel_id
        )
        return row["c"] if row else 0

async def get_pending_requests_for_channel(channel_id, limit=None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        if limit:
            rows = await conn.fetch(
                "SELECT * FROM join_requests WHERE channel_id = $1 AND status = 'pending' ORDER BY created_at ASC LIMIT $2",
                channel_id, limit
            )
        else:
            rows = await conn.fetch(
                "SELECT * FROM join_requests WHERE channel_id = $1 AND status = 'pending' ORDER BY created_at ASC",
                channel_id
            )
        return [dict(r) for r in rows]

async def update_join_request_status(request_id, status):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE join_requests SET status = $1, processed_at = NOW() WHERE id = $2",
            status, request_id
        )

async def get_total_pending_count():
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT COUNT(*) as c FROM join_requests WHERE status = 'pending'")
        return row["c"] if row else 0

async def get_join_request_stats():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT status, COUNT(*) as c FROM join_requests GROUP BY status
        """)
        return {r["status"]: r["c"] for r in rows}

# ===================================
# Bot settings
# ===================================

async def get_bot_setting(key, default=None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT value FROM bot_settings WHERE key = $1", key)
        return row["value"] if row else default

async def update_bot_setting(key, value):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO bot_settings (key, value) VALUES ($1, $2) ON CONFLICT (key) DO UPDATE SET value = $2",
            key, value
        )

# ===================================
# Mandatory channels
# ===================================

async def add_mandatory_channel(channel_id, title=None, username=None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO mandatory_channels (channel_id, title, username) VALUES ($1, $2, $3) ON CONFLICT (channel_id) DO UPDATE SET title = $2, username = $3",
            channel_id, title, username
        )

async def remove_mandatory_channel(channel_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM mandatory_channels WHERE channel_id = $1", channel_id)

async def get_mandatory_channels():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM mandatory_channels ORDER BY added_at DESC")
        return [dict(r) for r in rows]

# ===================================
# Broadcasts
# ===================================

async def add_broadcast(message_text, sent_count, fail_count):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO broadcasts (message_text, sent_count, fail_count) VALUES ($1, $2, $3)",
            message_text, sent_count, fail_count
        )

# ===================================
# Templates
# ===================================

async def add_template(name, content):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO templates (name, content) VALUES ($1, $2) ON CONFLICT (name) DO UPDATE SET content = $2",
            name, content
        )

async def get_template(name):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM templates WHERE name = $1", name)
        return dict(row) if row else None

async def get_all_templates():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM templates ORDER BY name")
        return [dict(r) for r in rows]

async def delete_template(name):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM templates WHERE name = $1", name)

# ===================================
# Auto Poster
# ===================================

async def add_auto_poster(channel_id, template_name, interval_minutes):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO auto_posters (channel_id, template_name, interval_minutes) VALUES ($1, $2, $3)",
            channel_id, template_name, interval_minutes
        )

async def get_active_posters():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM auto_posters WHERE active = TRUE")
        return [dict(r) for r in rows]

async def get_all_posters():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM auto_posters ORDER BY id")
        return [dict(r) for r in rows]

async def update_poster_last_post(poster_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE auto_posters SET last_post = NOW() WHERE id = $1",
            poster_id
        )

async def delete_poster(poster_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM auto_posters WHERE id = $1", poster_id)
