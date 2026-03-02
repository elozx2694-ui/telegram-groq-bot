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

# Токены из переменных окружения
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

# Проверка токенов
if not TELEGRAM_TOKEN:
    print("ERROR: TELEGRAM_TOKEN not set!")
    sys.exit(1)

if not GROQ_API_KEY:
    print("ERROR: GROQ_API_KEY not set!")
    sys.exit(1)

# URL для Groq API
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Инициализация бота
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Модели Groq (все 7 рабочих)
MODELS = {
    '1': {'name': 'llama-3.1-8b-instant', 'desc': 'Llama 3.1 8B (fast)'},
    '2': {'name': 'llama-3.1-70b-versatile', 'desc': 'Llama 3.1 70B (powerful)'},
    '3': {'name': 'mixtral-8x7b-32768', 'desc': 'Mixtral 8x7B'},
    '4': {'name': 'gemma2-9b-it', 'desc': 'Gemma 2 9B (Google)'},
    '5': {'name': 'qwen-2.5-72b', 'desc': 'Qwen 2.5 72B'},
    '6': {'name': 'qwen-2.5-32b', 'desc': 'Qwen 2.5 32B'},
    '7': {'name': 'deepseek-r1-distill-llama-70b', 'desc': 'DeepSeek R1 (via Groq)'},
}

# Модель по умолчанию - Llama 3.1 70B
current_model = 'llama-3.1-70b-versatile'
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

# Запускаем веб-сервер в отдельном потоке
webserver_thread = threading.Thread(target=run_webserver, daemon=True)
webserver_thread.start()

def ask_groq(messages, model):
    """Запрос к Groq API через requests"""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Проверяем и очищаем сообщения
    clean_messages = []
    for msg in messages[-10:]:  # Берем только последние 10 сообщений
        if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
            clean_messages.append({
                'role': msg['role'],
                'content': str(msg['content'])[:2000]  # Ограничиваем длину
            })
    
    data = {
        "model": model,
        "messages": clean_messages,
        "temperature": 0.7,
        "max_tokens": 1024,
        "top_p": 1,
        "stream": False
    }
    
    try:
        print(f"Request to Groq with model: {model}")
        
        response = requests.post(
            GROQ_API_URL, 
            headers=headers, 
            json=data, 
            timeout=30
        )
        
        if response.status_code != 200:
            error_text = response.text
            print(f"Groq API Error: {error_text}")
            
            try:
                error_json = response.json()
                if 'error' in error_json:
                    error_message = error_json['error'].get('message', 'Unknown error')
                    return f"Error: {error_message}"
            except:
                pass
            
            return f"Error: API returned status {response.status_code}"
        
        result = response.json()
        
        if 'choices' not in result or len(result['choices']) == 0:
            return "Error: Invalid response from API"
            
        return result['choices'][0]['message']['content']
        
    except requests.exceptions.Timeout:
        return "Error: API timeout"
    except requests.exceptions.ConnectionError:
        return "Error: Cannot connect to API"
    except Exception as e:
        return f"Error: {str(e)[:200]}"

@bot.message_handler(commands=['start', 'help'])
def start(message):
    text = (
        "Groq Bot - 7 Free Models\n"
        "========================\n\n"
        f"Current model: {current_model}\n\n"
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
    text = "Available Groq Models (free):\n"
    text += "============================\n\n"
    
    for num, model_info in MODELS.items():
        if model_info['name'] == current_model:
            text += f"[{num}] {model_info['desc']} (active)\n"
        else:
            text += f" {num}  {model_info['desc']}\n"
    
    text += "\nTo select: /model [number]\n"
    text += "Example: /model 2 for Llama 70B"
    
    bot.reply_to(message, text)

@bot.message_handler(commands=['model'])
def set_model(message):
    global current_model
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "Please specify model number. Example: /model 2")
            return
        
        num = parts[1]
        if num in MODELS:
            current_model = MODELS[num]['name']
            bot.reply_to(message, f"Model changed to: {MODELS[num]['desc']}")
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
    
    # Инициализируем историю для нового пользователя
    if user_id not in user_history:
        user_history[user_id] = []
    
    # Добавляем сообщение пользователя
    user_history[user_id].append({"role": "user", "content": message.text})
    
    # Ограничиваем историю (последние 20 сообщений)
    if len(user_history[user_id]) > 20:
        user_history[user_id] = user_history[user_id][-20:]
    
    try:
        # Показываем что бот печатает
        bot.send_chat_action(message.chat.id, 'typing')
        
        # Отправляем запрос в Groq
        answer = ask_groq(user_history[user_id], current_model)
        
        # Сохраняем ответ если это не ошибка
        if not answer.startswith("Error:"):
            user_history[user_id].append({"role": "assistant", "content": answer})
        
        # Отправляем пользователю
        bot.reply_to(message, answer)
        
    except Exception as e:
        error_text = str(e)
        print(f"Chat error: {error_text}")
        bot.reply_to(message, f"Error: {error_text[:200]}")

print("=" * 50)
print("GROQ BOT STARTING")
print("=" * 50)
print(f"Telegram Token: {TELEGRAM_TOKEN[:10]}...{TELEGRAM_TOKEN[-5:]}")
print(f"Groq API Key: {GROQ_API_KEY[:10]}...{GROQ_API_KEY[-5:]}")
print(f"Current Model: {current_model}")
print(f"Available Models: {len(MODELS)}")
print("=" * 50)
print("Bot is ready! Close this terminal to avoid conflicts.")
print("=" * 50)

# Запускаем бота с обработкой ошибок
if __name__ == "__main__":
    try:
        # Удаляем вебхук если был
        bot.remove_webhook()
        time.sleep(1)
        
        # Запускаем polling
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"\nCritical error: {e}")
        time.sleep(5)