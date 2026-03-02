import telebot
import requests
import os
import threading
import time
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv

load_dotenv()

# Токены Telegram
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
# Groq API
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
# DeepSeek API (новый!)
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')

if not TELEGRAM_TOKEN:
    print("❌ Ошибка: TELEGRAM_TOKEN не задан!")
    exit(1)

# URL для API
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Модели с указанием API
MODELS = {
    # Groq модели
    '1': {'name': 'llama-3.1-8b-instant', 'api': 'groq'},
    '2': {'name': 'llama-3.1-70b-versatile', 'api': 'groq'},
    '3': {'name': 'mixtral-8x7b-32768', 'api': 'groq'},
    '4': {'name': 'gemma2-9b-it', 'api': 'groq'},
    '5': {'name': 'deepseek-r1-distill-llama-70b', 'api': 'groq'},
    # DeepSeek модели (обычные, без R1!)
    '6': {'name': 'deepseek-chat', 'api': 'deepseek'},  # Обычный DeepSeek (как здесь!)
    '7': {'name': 'deepseek-coder', 'api': 'deepseek'},  # Для программирования
    # Qwen через Groq
    '8': {'name': 'qwen-2.5-72b', 'api': 'groq'},
    '9': {'name': 'qwen-2.5-32b', 'api': 'groq'},
}

# Модель по умолчанию - мощная Llama через Groq!
current_model = 'llama-3.1-70b-versatile'  
current_api = 'groq

user_history = {}

# Веб-сервер для Render
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")
    def log_message(self, format, *args):
        pass

def run_webserver():
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"🌐 Веб-сервер запущен на порту {port}")
    server.serve_forever()

webserver_thread = threading.Thread(target=run_webserver, daemon=True)
webserver_thread.start()

def ask_groq(messages, model):
    """Запрос к Groq API"""
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
    except Exception as e:
        raise Exception(f"Groq API ошибка: {str(e)}")

def ask_deepseek(messages, model):
    """Запрос к официальному API DeepSeek (обычная модель, без R1!)"""
    if not DEEPSEEK_API_KEY:
        raise Exception("❌ DeepSeek API ключ не задан в Environment Variables")
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,  # 'deepseek-chat' - обычный DeepSeek
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2048,
        "stream": False
    }
    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']
    except Exception as e:
        raise Exception(f"DeepSeek API ошибка: {str(e)}")

@bot.message_handler(commands=['start'])
def start(message):
    text = (
        "🤖 *Бот с двумя API!*\n\n"
        "Доступны модели:\n"
        "• Groq (Llama, Mixtral, Gemma, Qwen)\n"
        "• **DeepSeek официальный** (обычный, как в чате!)\n\n"
        "Команды:\n"
        "/models - список моделей\n"
        f"/model [номер] - выбрать модель\n"
        f"Сейчас: `{current_model}` ({current_api})\n"
        "/clear - очистить историю"
    )
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['models'])
def show_models(message):
    text = "📚 *Доступные модели:*\n\n"
    for num, model_info in MODELS.items():
        mark = "✅" if model_info['name'] == current_model else "•"
        api_icon = "🟢" if model_info['api'] == 'deepseek' else "🟣"
        text += f"{mark} {api_icon} `{num}. {model_info['name']}` ({model_info['api']})\n"
    text += "\n🟢 DeepSeek официальный (обычный)\n🟣 Groq модели\n"
    text += "\nВыбрать: `/model [номер]`"
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['model'])
def set_model(message):
    global current_model, current_api
    try:
        num = message.text.split()[1]
        if num in MODELS:
            current_model = MODELS[num]['name']
            current_api = MODELS[num]['api']
            bot.reply_to(message, f"✅ Модель изменена на: `{current_model}` (через {current_api})", parse_mode="Markdown")
        else:
            bot.reply_to(message, f"❌ Неверный номер. Используй 1-{len(MODELS)}")
    except:
        bot.reply_to(message, "❌ Формат: /model [номер]")

@bot.message_handler(commands=['clear'])
def clear_history(message):
    user_id = message.from_user.id
    if user_id in user_history:
        user_history[user_id] = []
    bot.reply_to(message, "🧹 История очищена!")

@bot.message_handler(func=lambda m: True)
def chat(message):
    user_id = message.from_user.id
    
    if user_id not in user_history:
        user_history[user_id] = []
    
    user_history[user_id].append({"role": "user", "content": message.text})
    
    if len(user_history[user_id]) > 20:
        user_history[user_id] = user_history[user_id][-20:]
    
    try:
        # Выбираем нужный API
        if current_api == 'groq':
            if not GROQ_API_KEY:
                bot.reply_to(message, "❌ Groq API ключ не задан!")
                return
            answer = ask_groq(user_history[user_id], current_model)
        else:  # deepseek
            if not DEEPSEEK_API_KEY:
                bot.reply_to(message, "❌ DeepSeek API ключ не задан! Добавьте DEEPSEEK_API_KEY в Environment Variables")
                return
            answer = ask_deepseek(user_history[user_id], current_model)
        
        user_history[user_id].append({"role": "assistant", "content": answer})
        bot.reply_to(message, answer)
        
    except Exception as e:
        error_text = str(e)
        bot.reply_to(message, f"❌ {error_text[:200]}")

print("=" * 50)
print("🚀 Бот запускается с двумя API!")
print(f"📱 Telegram: {TELEGRAM_TOKEN[:10]}...")
print(f"🟣 Groq: {'✅' if GROQ_API_KEY else '❌'}")
print(f"🟢 DeepSeek: {'✅' if DEEPSEEK_API_KEY else '❌'}")
print(f"🤖 Модель: {current_model} (через {current_api})")
print("=" * 50)

bot.infinity_polling()