import os
import threading
import logging
from flask import Flask
from telegram import Update
from telegram.error import BadRequest
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- НАСТРОЙКИ ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")
PORT = int(os.environ.get('PORT', 5000))
USER_LIST_FILE = "group_user_ids.txt"
# ------------------

# Веб-приложение Flask для Render
app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Bot is alive and running!'

# --- Вспомогательные функции ---

def load_user_ids():
    if not os.path.exists(USER_LIST_FILE):
        return set()
    with open(USER_LIST_FILE, "r") as f:
        return set(int(line.strip()) for line in f if line.strip())

def save_user_ids(user_ids):
    with open(USER_LIST_FILE, "w") as f:
        for user_id in user_ids:
            f.write(str(user_id) + "\n")

def add_user_id(user_id):
    user_ids = load_user_ids()
    if user_id not in user_ids:
        user_ids.add(user_id)
        save_user_ids(user_ids)
        return True
    return False

# --- Основные функции-обработчики ---

async def remember_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.from_user:
        user = update.message.from_user
        if not user.is_bot and add_user_id(user.id):
            logging.info(f"Запомнил нового пользователя: {user.first_name} (ID: {user.id})")

async def tag_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.from_user:
        user = update.message.from_user
        if not user.is_bot:
            add_user_id(user.id)
            
    chat_id = update.message.chat_id
    logging.info(f"Получена команда @all в чате {chat_id}")
    
    user_ids = load_user_ids()
    if not user_ids:
        await update.message.reply_text("Я пока никого не знаю!")
        return
    
    original_text = update.message.text.replace('/all', '').replace('@all', '').strip()
    # Упоминания без форматирования
    mentions_string = " ".join([f"[{user_id}](tg://user?id={user_id})" for user_id in user_ids])
    
    final_text = ""
    if original_text:
        final_text = f"Важное сообщение!\n{original_text}\n\n{mentions_string}"
    else:
        final_text = f"Общий сбор!\n\n{mentions_string}"
    
    # Отправляем просто текст, без Markdown
    await context.bot.send_message(chat_id=chat_id, text=final_text)

async def show_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_ids = load_user_ids()
    if not user_ids:
        await update.message.reply_text("Я еще никого не запомнила, квадроберы.")
        return

    known_users = []
    for user_id in user_ids:
        try:
            user_chat = await context.bot.get_chat(user_id)
            known_users.append(user_chat.first_name)
        except Exception:
            logging.warning(f"Не удалось получить информацию о пользователе с ID {user_id}")

    if not known_users:
        await update.message.reply_text("Что-то пошло не так, не могу найти ваших имен.")
        return

    response_text = "Я запомнила вас, квадроберы:\n\n"
    for i, name in enumerate(known_users, 1):
        response_text += f"{i}. {name}\n"
    
    await update.message.reply_text(response_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = "Подходите в центр международных конкурсов по праву МГУ, я вам всё расскажу. Центр расположен в кабинете 659А"
    await update.message.reply_text(help_text)

# --- НОВАЯ ФУНКЦИЯ ---
async def danya_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выдает определение синдрома Танцурина."""
    danya_text = (
        "Синдром Танцурина — это хроническое невезение студента, "
        "проявляющееся в серии неудач, которые происходят не по его вине, "
        "но неизменно с его участием. Часто сопровождается фразами окружающих "
        "\"Ну это же Даня\" и приводит к неожиданным, но закономерным провалам "
        "в самых ответственных ситуациях."
    )
    await update.message.reply_text(danya_text)

async def tag_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    logging.info(f"Получена команда /admins в чате {chat_id}")
    
    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        admin_mentions = [f"[{admin.user.first_name}](tg://user?id={admin.user.id})" for admin in admins if not admin.user.is_bot]
        
        if not admin_mentions:
            await update.message.reply_text("В этом чате нет администраторов (кроме ботов).")
            return
            
        message_text = "Внимание администраторам! " + " ".join(admin_mentions)
        await context.bot.send_message(chat_id=chat_id, text=message_text)
        
    except Exception as e:
        logging.error(f"Ошибка при получении админов: {e}")
        await update.message.reply_text("Не удалось получить список администраторов.")

async def cleanup_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_ids = load_user_ids()
    
    if not user_ids:
        await update.message.reply_text("Мой список и так пуст.")
        return
        
    await update.message.reply_text(f"Начинаю проверку {len(user_ids)} участников...")
    
    kept_ids = set()
    removed_count = 0
    
    for user_id in user_ids:
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            if member.status not in ['left', 'kicked']:
                kept_ids.add(user_id)
            else:
                removed_count += 1
        except BadRequest:
            removed_count += 1
        except Exception as e:
            logging.error(f"Ошибка при проверке пользователя {user_id}: {e}")
            kept_ids.add(user_id)

    save_user_ids(kept_ids)
    await update.message.reply_text(f"Очистка завершена.\nОсталось в списке: {len(kept_ids)}\nУдалено: {removed_count}")

async def greet_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    my_bot = await context.bot.get_me()
    for member in update.message.new_chat_members:
        if member.id == my_bot.id:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Привет! Я здесь, чтобы всех пинговать."
            )

# --- ЗАПУСК БОТА И СЕРВЕРА ---
def run_bot():
    application = Application.builder().token(TOKEN).build()

    # Добавляем обработчик для новой команды /danya
    application.add_handler(CommandHandler("danya", danya_command))
    
    application.add_handler(CommandHandler(["start", "help"], help_command))
    application.add_handler(CommandHandler("list", show_list))
    application.add_handler(CommandHandler("admins", tag_admins))
    application.add_handler(CommandHandler("cleanup", cleanup_list))
    
    application.add_handler(CommandHandler("all", tag_all))
    application.add_handler(MessageHandler(filters.Regex(r'(?i)@all'), tag_all))
    
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, greet_new_members))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, remember_user))
    
    logging.info("Бот запущен в отдельном потоке...")
    application.run_polling(stop_signals=None)

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    
    logging.info("Веб-сервер запущен...")
    app.run(host='0.0.0.0', port=PORT)