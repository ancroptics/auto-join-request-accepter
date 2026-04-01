import database as db
from utils.helpers import get_tier, next_tier_info


async def process_referral(user_id, referrer_id):
    if user_id == referrer_id:
        return None
    existing = await db.get_user(user_id)
    if existing:
        return None
    await db.increment_referral(referrer_id)
    referrer = await db.get_user(referrer_id)
    count = referrer.get("referral_count", 0) if referrer else 0
    tier = get_tier(count)
    return {"referrer_id": referrer_id, "count": count, "tier": tier}


async def get_referral_stats(user_id):
    user = await db.get_user(user_id)
    if not user:
        return None
    count = user.get("referral_count", 0)
    tier = get_tier(count)
    next_name, next_threshold = next_tier_info(count)
    return {
        "count": count,
        "tier": tier,
        "next_tier": next_name,
        "next_threshold": next_threshold,
        "remaining": max(0, next_threshold - count),
    }
