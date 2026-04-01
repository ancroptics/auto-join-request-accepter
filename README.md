# 🚀 Telegram Growth Engine Bot

Auto Join Request Accepter + Growth Engine for Telegram channels/groups.

## Features
- ✅ Auto-approve join requests
- 💬 Welcome DM to new members
- 📢 Broadcast to all users
- 🔗 Referral system with tiers & coins
- 🤖 Auto-poster for groups
- 📊 Analytics dashboard
- ⚙️ Admin panel

## Setup
1. Clone repo
2. Create Supabase project, get DATABASE_URL
3. Set environment variables (see .env.example)
4. Deploy to Render or run locally: `python bot.py`

## Deployment
- Push to GitHub → connect to Render
- Set all env vars in Render dashboard
- UptimeRobot: monitor `https://your-app.onrender.com/health` every 5 min

## Commands
- /start - Start bot
- /referral - Get referral link
- /balance - Check coins
- /leaderboard - Top referrers
- /mystats - Your stats
- /help - Help
