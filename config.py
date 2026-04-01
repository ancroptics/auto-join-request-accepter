import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_IDS_STR = os.environ.get("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS_STR.split(",") if x.strip().isdigit()]
BOT_USERNAME = os.environ.get("BOT_USERNAME", "Botofall_robot")
REFERRAL_REWARD_COINS = int(os.environ.get("REFERRAL_REWARD_COINS", "10"))
DATABASE_URL = os.environ.get("DATABASE_URL", "")
USE_WEBHOOK = os.environ.get("USE_WEBHOOK", "false").lower() == "true"
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")
PORT = int(os.environ.get("PORT", "10000"))
