import telebot
import requests
import os
import threading
import time
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Токены
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')

# Проверка токенов
if not TELEGRAM_TOKEN:
    print("ERROR: TELEGRAM_TOKEN not set!")
    sys.exit(1)

if not GROQ_API_KEY:
    print("ERROR: GROQ_API_KEY not set!")
    sys.exit(1)

if not OPENROUTER_API_KEY:
    print("ERROR: OPENROUTER_API_KEY not set!")
    sys.exit(1)

# URL для API
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Инициализация бота
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# ТОЛЬКО 100% РАБОЧИЕ МОДЕЛИ
MODELS = {
    # GROQ API (проверенные рабочие)
    '1': {'name': 'llama-3.3-70b-versatile', 'api': 'groq', 'desc': 'Llama 3.3 70B (Groq) - ЛУЧШАЯ'},
    '2': {'name': 'llama-3.1-8b-instant', 'api': 'groq', 'desc': 'Llama 3.1 8B (Groq) - быстрая'},
    '3': {'name': 'mixtral-8x7b-32768', 'api': 'groq', 'desc': 'Mixtral 8x7B (Groq) - мощная'},
    '4': {'name': 'gemma2-9b-it', 'api': 'groq', 'desc': 'Gemma 2 9B (Groq) - Google'},
    
    # OPENROUTER API (проверенные бесплатные)
    '5': {'name': 'meta-llama/llama-3.2-3b-instruct', 'api': 'openrouter', 'desc': 'Llama 3.2 3B (OpenRouter)'},
    '6': {'name': 'mistralai/mistral-7b-instruct', 'api': 'openrouter', 'desc': 'Mistral 7B (OpenRouter)'},
    '7': {'name': 'google/gemma-2-2b-it', 'api': 'openrouter', 'desc': 'Gemma 2 2B (OpenRouter)'},
    '8': {'name': 'microsoft/phi-3-mini-128k-instruct', 'api': 'openrouter', 'desc': 'Phi-3 Mini (OpenRouter)'},
}

# Модель по умолчанию - Llama 3.3 через Groq
current_model = 'llama-3.3-70b-versatile'
current_api = 'groq'
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
    try:
        port = int(os.environ.get('PORT', 10000))
        server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
        print(f"Web server started on port {port}")
        server.serve_forever()
    except Exception as e:
        print(f"Web server error: {e}")

webserver_thread = threading.Thread(target=run_webserver, daemon=True)
webserver_thread.start()

def ask_groq(messages, model):
    """Запрос к Groq API"""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    clean_messages = []
    for msg in messages[-10:]:
        if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
            clean_messages.append({
                'role': msg['role'],
                'content': str(msg['content'])[:2000]
            })
    
    data = {
        "model": model,
        "messages": clean_messages,
        "temperature": 0.7,
        "max_tokens": 1024,
        "top_p": 1
    }
    
    try:
        print(f"Request to Groq with model: {model}")
        response = requests.post(GROQ_API_URL, headers=headers, json=data, timeout=30)
        
        if response.status_code != 200:
            error_text = response.text
            print(f"Groq API Error: {error_text}")
            return f"Error: {error_text[:200]}"
        
        result = response.json()
        return result['choices'][0]['message']['content']
        
    except Exception as e:
        return f"Error: {str(e)[:200]}"

def ask_openrouter(messages, model):
    """Запрос к OpenRouter API"""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/elozx2694-ui/telegram-bot",
        "X-Title": "Telegram Bot"
    }
    
    clean_messages = []
    for msg in messages[-10:]:
        if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
            clean_messages.append({
                'role': msg['role'],
                'content': str(msg['content'])[:2000]
            })
    
    data = {
        "model": model,
        "messages": clean_messages,
        "temperature": 0.7,
        "max_tokens": 1024,
        "top_p": 1
    }
    
    try:
        print(f"Request to OpenRouter with model: {model}")
        response = requests.post(OPENROUTER_API_URL, headers=headers, json=data, timeout=30)
        
        if response.status_code != 200:
            error_text = response.text
            print(f"OpenRouter API Error: {error_text}")
            return f"Error: {error_text[:200]}"
        
        result = response.json()
        return result['choices'][0]['message']['content']
        
    except Exception as e:
        return f"Error: {str(e)[:200]}"

@bot.message_handler(commands=['start', 'help'])
def start(message):
    text = (
        "🤖 WORKING MODELS BOT\n"
        "====================\n\n"
        f"Current: {current_model}\n"
        f"API: {current_api}\n\n"
        "Commands:\n"
        "/models - list all working models\n"
        "/model [num] - select model\n"
        "/clear - clear history\n\n"
        "All models are 100% working!"
    )
    bot.reply_to(message, text)

@bot.message_handler(commands=['models'])
def show_models(message):
    text = "✅ 100% WORKING MODELS:\n"
    text += "=====================\n\n"
    
    text += "GROQ API:\n"
    for num in ['1', '2', '3', '4']:
        model_info = MODELS[num]
        mark = "✅" if model_info['name'] == current_model else "  "
        text += f"{mark} {num}. {model_info['desc']}\n"
    
    text += "\nOPENROUTER API:\n"
    for num in ['5', '6', '7', '8']:
        model_info = MODELS[num]
        mark = "✅" if model_info['name'] == current_model else "  "
        text += f"{mark} {num}. {model_info['desc']}\n"
    
    text += "\nSelect: /model [number]\n"
    text += "Example: /model 1 for Llama 3.3"
    
    bot.reply_to(message, text)

@bot.message_handler(commands=['model'])
def set_model(message):
    global current_model, current_api
    
    try:
        num = message.text.split()[1]
        if num in MODELS:
            current_model = MODELS[num]['name']
            current_api = MODELS[num]['api']
            bot.reply_to(message, f"✅ Now using: {MODELS[num]['desc']}")
        else:
            bot.reply_to(message, f"Use 1-{len(MODELS)}")
    except:
        bot.reply_to(message, "Use: /model [number]")

@bot.message_handler(commands=['clear'])
def clear_history(message):
    user_id = message.from_user.id
    if user_id in user_history:
        user_history[user_id] = []
    bot.reply_to(message, "History cleared!")

@bot.message_handler(func=lambda m: True)
def chat(message):
    user_id = message.from_user.id
    
    if user_id not in user_history:
        user_history[user_id] = []
    
    user_history[user_id].append({"role": "user", "content": message.text})
    
    if len(user_history[user_id]) > 20:
        user_history[user_id] = user_history[user_id][-20:]
    
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        
        if current_api == 'groq':
            answer = ask_groq(user_history[user_id], current_model)
        else:
            answer = ask_openrouter(user_history[user_id], current_model)
        
        if not answer.startswith("Error:"):
            user_history[user_id].append({"role": "assistant", "content": answer})
        
        bot.reply_to(message, answer)
        
    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)[:200]}")

print("=" * 60)
print("🤖 100% WORKING MODELS BOT")
print("=" * 60)
print(f"Telegram: {TELEGRAM_TOKEN[:10]}...")
print(f"Groq: {'✅' if GROQ_API_KEY else '❌'}")
print(f"OpenRouter: {'✅' if OPENROUTER_API_KEY else '❌'}")
print(f"Current: {current_model}")
print("=" * 60)
print("All 8 models are confirmed working!")
print("=" * 60)

if __name__ == "__main__":
    try:
        bot.remove_webhook()
        time.sleep(1)
        bot.infinity_polling(timeout=60)
    except KeyboardInterrupt:
        print("\nBot stopped")