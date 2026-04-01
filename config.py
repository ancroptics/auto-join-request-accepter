import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_IDS = [int(x.strip()) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()]
BOT_USERNAME = os.environ.get("BOT_USERNAME", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "")
PORT = int(os.environ.get("PORT", "10000"))
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")
USE_WEBHOOK = os.environ.get("USE_WEBHOOK", "false").lower() == "true"
REFERRAL_REWARD_COINS = int(os.environ.get("REFERRAL_REWARD_COINS", "10"))
BROADCAST_RATE_LIMIT = int(os.environ.get("BROADCAST_RATE_LIMIT", "25"))
WELCOME_DM_ENABLED = os.environ.get("WELCOME_DM_ENABLED", "true").lower() == "true"
AUTO_APPROVE_ENABLED = os.environ.get("AUTO_APPROVE_ENABLED", "true").lower() == "true"
APPROVE_BATCH_SIZE = int(os.environ.get("APPROVE_BATCH_SIZE", "50"))
VERSION = "1.0.0"
