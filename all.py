import os
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# --- ВАША НАСТРОЙКА ---
TOKEN = "8416235194:AAH50UPbbwvaii-7TmTDyHhlqyHg6DtsdTo"  # <--- Замените на токен от BotFather
# ---------------------

# Имя файла, где будут храниться ID участников
USER_LIST_FILE = "group_user_ids.txt"

# --- Логика бота ---

# Загружаем ID из файла
def load_user_ids():
    if not os.path.exists(USER_LIST_FILE):
        return set()
    with open(USER_LIST_FILE, "r") as f:
        # Читаем ID и убираем пустые строки, если есть
        return set(int(line.strip()) for line in f if line.strip())

# Сохраняем новый ID в файл
def save_user_id(user_id):
    user_ids = load_user_ids()
    if user_id not in user_ids:
        with open(USER_LIST_FILE, "a") as f:
            f.write(str(user_id) + "\n")
        return True
    return False

# Функция, которая "запоминает" всех, кто пишет в чате
def remember_user(update: Update, context: CallbackContext):
    # Убеждаемся, что сообщение не пустое и от пользователя
    if update.message and update.message.from_user:
        user = update.message.from_user
        if save_user_id(user.id):
            print(f"Запомнил нового пользователя: {user.first_name} (ID: {user.id})")

# Функция для команды @all
def tag_all(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    print(f"Получена команда @all в чате {chat_id}")

    user_ids = load_user_ids()

    if not user_ids:
        update.message.reply_text("Я пока никого не знаю в этом чате. Как только кто-нибудь напишет, я его запомню!")
        return

    # Получаем текст, который идет после команды @all
    command_text = update.message.text
    original_text = command_text.replace('/all', '').replace('@all', '').strip()

    # Формируем "упоминания"
    mentions = [f"[\u200b](tg://user?id={uid})" for uid in user_ids]

    # Разбиваем на части, т.к. в одном сообщении есть лимиты
    chunk_size = 50
    for i in range(0, len(mentions), chunk_size):
        chunk = mentions[i:i + chunk_size]
        message_text = " ".join(chunk)

        # Добавляем исходный текст к первому сообщению
        if i == 0 and original_text:
            message_text = f"❗ **Важное сообщение!** ❗\n_{original_text}_\n\n" + message_text

        context.bot.send_message(chat_id=chat_id, text=message_text, parse_mode='Markdown')

def main():
    # Создаем и настраиваем бота
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # 1. Обработчик для команды @all (или /all)
    dp.add_handler(MessageHandler(Filters.regex('(?i)@all') | Filters.command('all'), tag_all))

    # 2. Обработчик для всех остальных сообщений, чтобы запоминать пользователей
    # Он не будет реагировать на команды
    dp.add_handler(MessageHandler(Filters.text & (~Filters.command), remember_user))

    print("Бот запущен. Нажмите Ctrl+C, чтобы остановить.")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()