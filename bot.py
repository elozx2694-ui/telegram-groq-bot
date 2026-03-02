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
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')

# Проверка токенов
if not TELEGRAM_TOKEN:
    print("ERROR: TELEGRAM_TOKEN not set!")
    exit(1)

# URL для API
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# Инициализация бота
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Модели с указанием API
MODELS = {
    # Groq модели (бесплатные)
    '1': {'name': 'llama-3.1-8b-instant', 'api': 'groq', 'desc': 'Llama 3.1 8B (fast)'},
    '2': {'name': 'llama-3.1-70b-versatile', 'api': 'groq', 'desc': 'Llama 3.1 70B (powerful)'},
    '3': {'name': 'mixtral-8x7b-32768', 'api': 'groq', 'desc': 'Mixtral 8x7B'},
    '4': {'name': 'gemma2-9b-it', 'api': 'groq', 'desc': 'Gemma 2 9B (Google)'},
    '5': {'name': 'deepseek-r1-distill-llama-70b', 'api': 'groq', 'desc': 'DeepSeek R1 (reasoning)'},
    # Qwen через Groq
    '6': {'name': 'qwen-2.5-72b', 'api': 'groq', 'desc': 'Qwen 2.5 72B'},
    '7': {'name': 'qwen-2.5-32b', 'api': 'groq', 'desc': 'Qwen 2.5 32B'},
    # DeepSeek модели (платные, нужен ключ)
    '8': {'name': 'deepseek-chat', 'api': 'deepseek', 'desc': 'DeepSeek Chat (standard)'},
    '9': {'name': 'deepseek-coder', 'api': 'deepseek', 'desc': 'DeepSeek Coder'},
}

# Модель по умолчанию - Llama 3.1 70B
current_model = 'llama-3.1-70b-versatile'
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
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"Web server started on port {port}")
    server.serve_forever()

# Запускаем веб-сервер в отдельном потоке
webserver_thread = threading.Thread(target=run_webserver, daemon=True)
webserver_thread.start()

def ask_groq(messages, model):
    """Запрос к Groq API"""
    if not GROQ_API_KEY:
        raise Exception("Groq API key not set!")
    
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
        raise Exception("Groq API timeout")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Groq API error: {str(e)}")

def ask_deepseek(messages, model):
    """Запрос к официальному API DeepSeek"""
    if not DEEPSEEK_API_KEY:
        raise Exception("DeepSeek API key not set in Environment Variables")
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model,
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
    except requests.exceptions.Timeout:
        raise Exception("DeepSeek API timeout")
    except requests.exceptions.RequestException as e:
        raise Exception(f"DeepSeek API error: {str(e)}")

@bot.message_handler(commands=['start', 'help'])
def start(message):
    text = (
        "Groq + DeepSeek Bot\n\n"
        "Available APIs:\n"
        "- Groq (free) - Llama, Mixtral, Gemma, Qwen\n"
        "- DeepSeek (paid) - standard DeepSeek\n\n"
        f"Current model: {current_model}\n"
        f"Current API: {current_api}\n\n"
        "Commands:\n"
        "/models - list all models\n"
        "/model [number] - select model\n"
        "/clear - clear history\n"
        "/help - this menu\n\n"
        "Just send a message and I'll reply!"
    )
    bot.reply_to(message, text)

@bot.message_handler(commands=['models'])
def show_models(message):
    text = "Available models:\n\n"
    
    # Groq models
    text += "GROQ (free):\n"
    for num, model_info in MODELS.items():
        if model_info['api'] == 'groq':
            mark = ">>" if model_info['name'] == current_model else "  "
            text += f"{mark} {num}. {model_info['desc']}\n"
    
    text += "\nDEEPSEEK (key required):\n"
    for num, model_info in MODELS.items():
        if model_info['api'] == 'deepseek':
            mark = ">>" if model_info['name'] == current_model else "  "
            status = " (available)" if DEEPSEEK_API_KEY else " (no key)"
            text += f"{mark} {num}. {model_info['desc']}{status}\n"
    
    text += "\nSelect model: /model [number]\n"
    text += "Example: /model 2 for Llama 70B"
    
    bot.reply_to(message, text)

@bot.message_handler(commands=['model'])
def set_model(message):
    global current_model, current_api
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "Specify model number. Example: /model 2")
            return
        
        num = parts[1]
        if num in MODELS:
            # Check if DeepSeek API is available
            if MODELS[num]['api'] == 'deepseek' and not DEEPSEEK_API_KEY:
                bot.reply_to(message, 
                    "DeepSeek API key not configured!\n"
                    "Add DEEPSEEK_API_KEY to Environment Variables")
                return
            
            current_model = MODELS[num]['name']
            current_api = MODELS[num]['api']
            
            response_text = (
                f"Model changed to:\n"
                f"{MODELS[num]['desc']}\n"
                f"API: {current_api}"
            )
            bot.reply_to(message, response_text)
        else:
            bot.reply_to(message, f"Invalid number. Use 1-{len(MODELS)}")
    
    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)[:100]}")

@bot.message_handler(commands=['clear'])
def clear_history(message):
    user_id = message.from_user.id
    if user_id in user_history:
        user_history[user_id] = []
        bot.reply_to(message, "History cleared!")
    else:
        bot.reply_to(message, "History is already empty.")

@bot.message_handler(func=lambda m: True)
def chat(message):
    user_id = message.from_user.id
    
    # Initialize history for new user
    if user_id not in user_history:
        user_history[user_id] = []
    
    # Add user message
    user_history[user_id].append({"role": "user", "content": message.text})
    
    # Limit history (last 20 messages)
    if len(user_history[user_id]) > 20:
        user_history[user_id] = user_history[user_id][-20:]
    
    try:
        # Send typing indicator
        bot.send_chat_action(message.chat.id, 'typing')
        
        # Choose API
        if current_api == 'groq':
            answer = ask_groq(user_history[user_id], current_model)
        else:  # deepseek
            answer = ask_deepseek(user_history[user_id], current_model)
        
        # Save answer
        user_history[user_id].append({"role": "assistant", "content": answer})
        
        # Send to user
        bot.reply_to(message, answer)
        
    except Exception as e:
        error_text = str(e)
        bot.reply_to(message, f"Error: {error_text[:200]}")

print("=" * 50)
print("BOT STARTING")
print("=" * 50)
print(f"Telegram: {TELEGRAM_TOKEN[:10]}...")
print(f"Groq API: {'YES' if GROQ_API_KEY else 'NO'}")
print(f"DeepSeek API: {'YES' if DEEPSEEK_API_KEY else 'NO'}")
print(f"Current model: {current_model}")
print(f"Current API: {current_api}")
print("=" * 50)

# Запускаем бота
if __name__ == "__main__":
    try:
        bot.infinity_polling()
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"\nCritical error: {e}")
        time.sleep(5)