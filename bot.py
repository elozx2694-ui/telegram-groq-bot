import telebot
import requests
import os
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv

# Загружаем переменные окружения (для локальной разработки)
load_dotenv()

# Токены из переменных окружения
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

# Проверка токенов
if not TELEGRAM_TOKEN:
    print("❌ Ошибка: TELEGRAM_TOKEN не задан!")
    exit(1)
if not GROQ_API_KEY:
    print("❌ Ошибка: GROQ_API_KEY не задан!")
    exit(1)

# URL для Groq API
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Инициализация бота
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Доступные модели Groq (топовые на 2026)
MODELS = {
    '1': 'llama-3.1-8b-instant',        # Быстрая Llama
    '2': 'llama-3.1-70b-versatile',     # Мощная Llama
    '3': 'llama-3.2-1b-preview',        # Сверхбыстрая
    '4': 'llama-3.2-3b-preview',        # Маленькая быстрая
    '5': 'llama-3.2-11b-vision-preview', # С поддержкой зрения
    '6': 'llama-3.2-90b-vision-preview', # Огромная мультимодальная
    '7': 'mixtral-8x7b-32768',          # Mixtral (Mistral)
    '8': 'gemma2-9b-it',                 # Gemma от Google
    '9': 'gemma-7b-it',                  # Gemma старая
    '10': 'deepseek-r1-distill-llama-70b', # DeepSeek (ТОП!)
    '11': 'deepseek-r1-distill-qwen-32b',  # DeepSeek на Qwen
    '12': 'qwen-2.5-32b',                 # Qwen 32B
    '13': 'qwen-2.5-72b',                 # Qwen 72B (очень мощная)
    '14': 'qwen-2.5-coder-32b',           # Для программирования
    '15': 'mistral-saba-24b',             # Mistral свежая
}

current_model = 'deepseek-r1-distill-llama-70b'  # Быстрая для начала
# Или поставьте DeepSeek:
# current_model = 'deepseek-r1-distill-llama-70b'

user_history = {}

# ========== ВЕБ-СЕРВЕР ДЛЯ RENDER ==========
# Это нужно, чтобы Render думал, что у нас веб-приложение
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")
    
    def log_message(self, format, *args):
        # Отключаем логи веб-сервера
        pass

def run_webserver():
    """Запускает простой веб-сервер на порту из переменной PORT"""
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"🌐 Веб-сервер запущен на порту {port}")
    server.serve_forever()

# Запускаем веб-сервер в отдельном потоке
webserver_thread = threading.Thread(target=run_webserver, daemon=True)
webserver_thread.start()
# ===========================================

def ask_groq(messages, model):
    """Отправляет запрос к Groq API и возвращает ответ"""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2048
    }
    
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']
    except requests.exceptions.Timeout:
        raise Exception("⏱️ Превышено время ожидания ответа от Groq API")
    except requests.exceptions.RequestException as e:
        raise Exception(f"❌ Ошибка запроса к Groq API: {str(e)}")

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(
        message,
        "🤖 *Groq Bot 2026*\n\n"
        "Я использую нейросети через Groq API!\n\n"
        "📋 *Команды:*\n"
        "• `/models` - список моделей\n"
        "• `/model [номер]` - выбрать модель\n"
        "• `/clear` - очистить историю\n"
        "• `/help` - это меню\n\n"
        f"✨ *Текущая модель:* `{current_model}`\n\n"
        "Просто напиши сообщение и я отвечу!",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['help'])
def help_command(message):
    start(message)  # Просто вызываем ту же функцию

@bot.message_handler(commands=['models'])
def show_models(message):
    text = "📚 *Доступные модели:*\n\n"
    for num, model in MODELS.items():
        mark = "✅" if model == current_model else "•"
        text += f"{mark} `{num}. {model}`\n"
    text += "\n📝 *Чтобы выбрать:* `/model [номер]`\nНапример: `/model 2`"
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['model'])
def set_model(message):
    global current_model
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Укажите номер модели. Например: `/model 2`", parse_mode="Markdown")
            return
            
        num = parts[1]
        if num in MODELS:
            current_model = MODELS[num]
            bot.reply_to(message, f"✅ Модель изменена на: `{current_model}`", parse_mode="Markdown")
        else:
            bot.reply_to(message, f"❌ Неверный номер. Используй 1-{len(MODELS)}")
    except Exception:
        bot.reply_to(message, "❌ Ошибка. Формат: `/model [номер]`")

@bot.message_handler(commands=['clear'])
def clear_history(message):
    user_id = message.from_user.id
    if user_id in user_history:
        user_history[user_id] = []
    bot.reply_to(message, "🧹 История очищена!")

@bot.message_handler(func=lambda m: True)
def chat(message):
    user_id = message.from_user.id
    
    # Инициализируем историю для нового пользователя
    if user_id not in user_history:
        user_history[user_id] = []
    
    # Добавляем сообщение пользователя
    user_history[user_id].append({"role": "user", "content": message.text})
    
    # Ограничиваем историю (последние 20 сообщений)
    if len(user_history[user_id]) > 20:
        user_history[user_id] = user_history[user_id][-20:]
    
    try:
        # Отправляем запрос в Groq
        answer = ask_groq(user_history[user_id], current_model)
        
        # Сохраняем ответ
        user_history[user_id].append({"role": "assistant", "content": answer})
        
        # Отправляем пользователю
        bot.reply_to(message, answer)
        
    except Exception as e:
        error_text = str(e)
        if '403' in error_text:
            bot.reply_to(message, "❌ Ошибка доступа к Groq API. Проверьте API ключ.")
        elif 'model_not_found' in error_text:
            bot.reply_to(message, f"❌ Модель {current_model} не найдена. Выберите другую через /models")
        else:
            bot.reply_to(message, f"❌ {error_text}")

print("=" * 50)
print("🚀 Бот запускается...")
print(f"📱 Telegram бот: {TELEGRAM_TOKEN[:10]}...")
print(f"🔑 Groq API: {GROQ_API_KEY[:10]}...")
print(f"🤖 Модель: {current_model}")
print("=" * 50)

# Запускаем бота
try:
    bot.infinity_polling()
except Exception as e:
    print(f"❌ Критическая ошибка: {e}")
    time.sleep(5)