import os
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# --- НАСТРОЙКИ ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")
PORT = int(os.environ.get('PORT', 5000)) # Порт, который будет слушать веб-сервер
USER_LIST_FILE = "group_user_ids.txt"
# ------------------

# Создаем веб-приложение Flask
app = Flask(__name__)

@app.route('/')
def hello_world():
    # Этот ответ будет видеть Render для проверки, что сервис работает
    return 'Bot is alive and running!'

# --- ВСЯ ЛОГИКА БОТА ОСТАЕТСЯ ПРЕЖНЕЙ ---

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

def remember_user(update: Update, context: CallbackContext):
    if update.message and update.message.from_user:
        user = update.message.from_user
        if save_user_id(user.id):
            print(f"Запомнил нового пользователя: {user.first_name} (ID: {user.id})")

def tag_all(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    print(f"Получена команда @all в чате {chat_id}")
    user_ids = load_user_ids()
    if not user_ids:
        update.message.reply_text("Я пока никого не знаю. Пусть участники напишут что-нибудь в чат!")
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
        context.bot.send_message(chat_id=chat_id, text=message_text, parse_mode='Markdown')

# --- ФУНКЦИЯ ДЛЯ ЗАПУСКА БОТА ---
def run_bot():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(MessageHandler(Filters.regex('(?i)@all') | Filters.command('all'), tag_all))
    dp.add_handler(MessageHandler(Filters.text & (~Filters.command), remember_user))

    print("Бот запущен в отдельном потоке...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    # Запускаем бота в отдельном потоке (thread)
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()

    # В основном потоке запускаем веб-сервер
    print("Веб-сервер запущен...")
    app.run(host='0.0.0.0', port=PORT)