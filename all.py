import os
import threading
import logging
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Включаем логирование, чтобы видеть информацию о работе бота
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- НАСТРОЙКИ ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")
PORT = int(os.environ.get('PORT', 5000))
USER_LIST_FILE = "group_user_ids.txt"
# ------------------

# Создаем веб-приложение Flask для Render
app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Bot is alive and running!'

# --- ЛОГИКА БОТА ---

def load_user_ids():
    if not os.path.exists(USER_LIST_FILE):
        return set()
    with open(USER_LIST_FILE, "r") as f:
        return set(int(line.strip()) for line in f if line.strip())

def save_user_id(user_id):
    user_ids = load_user_ids()
    if user_id not in user_ids:
        with open(USER_LIST_FILE, "a") as f:
            f.write(str(user_id) + "\n")
        return True
    return False

async def remember_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.from_user:
        user = update.message.from_user
        if not user.is_bot and save_user_id(user.id):
            logging.info(f"Запомнил нового пользователя: {user.first_name} (ID: {user.id})")

async def tag_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    logging.info(f"Получена команда @all в чате {chat_id}")
    
    user_ids = load_user_ids()
    if not user_ids:
        await update.message.reply_text("Я пока никого не знаю. Пусть участники напишут что-нибудь в чат!")
        return
    
    command_text = update.message.text
    original_text = command_text.replace('/all', '').replace('@all', '').strip()
    mentions = [f"[\u200b](tg://user?id={uid})" for uid in user_ids]
    
    chunk_size = 50
    for i in range(0, len(mentions), chunk_size):
        chunk = mentions[i:i + chunk_size]
        message_text = " ".join(chunk)
        if i == 0 and original_text:
            message_text = f"❗ **Важное сообщение!** ❗\n_{original_text}_\n\n" + message_text
        
        await context.bot.send_message(chat_id=chat_id, text=message_text, parse_mode='Markdown')

# --- ЗАПУСК ---
def run_bot():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("all", tag_all))
    application.add_handler(MessageHandler(filters.Regex(r'(?i)@all'), tag_all))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, remember_user))
    
    logging.info("Бот запущен в отдельном потоке...")
    # ИСПРАВЛЕНИЕ ЗДЕСЬ: Добавлен параметр stop_signals=None
    application.run_polling(stop_signals=None)

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    
    logging.info("Веб-сервер запущен...")
    app.run(host='0.0.0.0', port=PORT)