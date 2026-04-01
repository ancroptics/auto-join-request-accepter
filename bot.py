import os
import logging
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, ChatJoinRequestHandler, CommandHandler
import asyncio
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_USER_ID = int(os.environ.get('ADMIN_USER_ID', '0'))
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')
PORT = int(os.environ.get('PORT', 10000))

app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)

async def approve_join_request(update: Update, context):
    join_request = update.chat_join_request
    try:
        await join_request.approve()
        user = join_request.from_user
        chat = join_request.chat
        logger.info(f'Approved join request from {user.first_name} ({user.id}) for {chat.title}')
        try:
            await context.bot.send_message(
                chat_id=ADMIN_USER_ID,
                text=f'\u2705 Approved: {user.first_name} (ID: {user.id}) joined {chat.title}'
            )
        except Exception:
            pass
    except Exception as e:
        logger.error(f'Failed to approve join request: {e}')

async def start_command(update: Update, context):
    await update.message.reply_text(
        '\U0001f916 Auto Join Request Accepter Bot\n\n'
        'I automatically approve join requests for groups and channels.\n\n'
        'How to use:\n'
        '1. Add me to your group/channel as admin\n'
        '2. Give me permission to invite users\n'
        '3. Enable join requests in your group/channel\n'
        '4. I will auto-approve all join requests!\n\n'
        'Admin commands:\n'
        '/start - Show this message\n'
        '/status - Check bot status'
    )

async def status_command(update: Update, context):
    if update.effective_user.id == ADMIN_USER_ID:
        await update.message.reply_text('\u2705 Bot is running and accepting join requests!')
    else:
        await update.message.reply_text('\u2705 Bot is online!')

telegram_app = None

async def setup_bot():
    global telegram_app
    telegram_app = Application.builder().token(BOT_TOKEN).build()
    telegram_app.add_handler(ChatJoinRequestHandler(approve_join_request))
    telegram_app.add_handler(CommandHandler('start', start_command))
    telegram_app.add_handler(CommandHandler('status', status_command))
    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.updater.start_polling(drop_pending_updates=True)
    logger.info('Bot started polling')

def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(setup_bot())
    loop.run_forever()

@app.route('/')
def index():
    return 'Auto Join Request Accepter Bot is running!', 200

@app.route('/health')
def health():
    return 'OK', 200

if __name__ == '__main__':
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    app.run(host='0.0.0.0', port=PORT)
