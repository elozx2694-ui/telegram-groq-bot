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
HUGGINGFACE_API_KEY = os.environ.get('HUGGINGFACE_API_KEY')

# Проверка токенов
if not TELEGRAM_TOKEN:
    print("ERROR: TELEGRAM_TOKEN not set!")
    sys.exit(1)

GROQ_AVAILABLE = bool(GROQ_API_KEY)
HF_AVAILABLE = bool(HUGGINGFACE_API_KEY)

# URL для API
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Инициализация бота
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# ==================== СПИСОК МОДЕЛЕЙ ====================
ALL_MODELS = {
    '1': {'name': 'llama-3.3-70b-versatile', 'api': 'groq', 'desc': 'Llama 3.3 70B (Groq)'},
    '2': {'name': 'llama-3.1-8b-instant', 'api': 'groq', 'desc': 'Llama 3.1 8B (Groq)'},
    '3': {'name': 'deepseek-r1-distill-llama-70b', 'api': 'groq', 'desc': 'DeepSeek R1 (Groq)'},
    '4': {'name': 'gemma2-9b-it', 'api': 'groq', 'desc': 'Gemma 2 9B (Groq)'},
    '5': {'name': 'qwen-2.5-72b', 'api': 'groq', 'desc': 'Qwen 2.5 72B (Groq)'},
    '6': {'name': 'IlyaGusev/saiga_llama3_8b', 'api': 'huggingface', 'desc': 'Saiga - Русская (HF)'},
    '7': {'name': 'microsoft/phi-3-mini-128k-instruct', 'api': 'huggingface', 'desc': 'Phi-3 Mini (HF)'},
    '8': {'name': 'mistralai/Mistral-7B-Instruct-v0.2', 'api': 'huggingface', 'desc': 'Mistral 7B (HF)'},
}

# Фильтруем доступные модели
MODELS = {k: v for k, v in ALL_MODELS.items() if (v['api'] == 'groq' and GROQ_AVAILABLE) or (v['api'] == 'huggingface' and HF_AVAILABLE)}

if not MODELS:
    print("ERROR: No models available!")
    sys.exit(1)

# Хранилище данных (в оперативной памяти)
user_history = {}    # История сообщений: {user_id: [messages]}
user_settings = {}   # Настройки модели: {user_id: {'model': name, 'api': api}}

# По умолчанию для новых юзеров берем первую модель из списка
DEFAULT_MODEL_KEY = list(MODELS.keys())[0]

# ==================== ВЕБ-СЕРВЕР ДЛЯ RENDER ====================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")
    def log_message(self, format, *args): pass

def run_webserver():
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=run_webserver, daemon=True).start()

# ==================== ФУНКЦИИ API ====================
def ask_groq(messages, model):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    # Ограничиваем длину контекста для экономии
    data = {"model": model, "messages": messages[-10:], "temperature": 0.7}
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        return f"Ошибка Groq API: {response.status_code}"
    except Exception as e:
        return f"Ошибка соединения: {str(e)[:50]}"

def ask_huggingface(messages, model):
    api_url = f"https://api-inference.huggingface.co/models/{model}"
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
    last_msg = messages[-1]['content']
    data = {"inputs": last_msg, "parameters": {"max_new_tokens": 500, "temperature": 0.7}}
    try:
        response = requests.post(api_url, headers=headers, json=data, timeout=60)
        if response.status_code == 200:
            res = response.json()
            return res[0].get('generated_text', str(res)) if isinstance(res, list) else str(res)
        return f"Ошибка HF API: {response.status_code}"
    except Exception as e:
        return f"Ошибка соединения: {str(e)[:50]}"

# ==================== КОМАНДЫ БОТА ====================
@bot.message_handler(commands=['start', 'help'])
def start(message):
    help_text = (
        "🤖 **AI Multi-Bot**\n\n"
        "/models - Список доступных нейросетей\n"
        "/model [номер] - Выбрать модель лично для себя\n"
        "/clear - Очистить историю диалога\n\n"
        "Просто напиши мне что-нибудь!"
    )
    bot.reply_to(message, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['models'])
def show_models(message):
    uid = message.from_user.id
    current = user_settings.get(uid, MODELS[DEFAULT_MODEL_KEY])
    
    text = "📊 **Доступные модели:**\n"
    for num, info in MODELS.items():
        status = "✅ (активна)" if info['name'] == current['model'] else ""
        text += f"{num}. {info['desc']} {status}\n"
    text += "\nВыбери номер: `/model 3`"
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(commands=['model'])
def set_model(message):
    uid = message.from_user.id
    try:
        num = message.text.split()[1]
        if num in MODELS:
            user_settings[uid] = {
                'model': MODELS[num]['name'],
                'api': MODELS[num]['api'],
                'desc': MODELS[num]['desc']
            }
            bot.reply_to(message, f"🎯 Установлена модель: **{MODELS[num]['desc']}**", parse_mode='Markdown')
        else:
            bot.reply_to(message, "❌ Нет такого номера в списке.")
    except:
        bot.reply_to(message, "Используй: `/model [номер]`")

@bot.message_handler(commands=['clear'])
def clear_history(message):
    user_history[message.from_user.id] = []
    bot.reply_to(message, "🧹 История очищена!")

# ==================== ОБРАБОТКА СООБЩЕНИЙ ====================
@bot.message_handler(func=lambda m: True)
def chat(message):
    uid = message.from_user.id
    
    # 1. Инициализация истории и настроек
    if uid not in user_history: user_history[uid] = []
    if uid not in user_settings: user_settings[uid] = MODELS[DEFAULT_MODEL_KEY]
    
    # 2. Добавляем сообщение юзера в историю
    user_history[uid].append({"role": "user", "content": message.text})
    
    # 3. Получаем настройки пользователя
    current = user_settings[uid]
    
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        
        # 4. Запрос к нужному API
        if current['api'] == 'groq':
            answer = ask_groq(user_history[uid], current['model'])
        else:
            answer = ask_huggingface(user_history[uid], current['model'])
        
        # 5. Сохраняем ответ в историю только если это не ошибка
        if not any(err in answer for err in ["Ошибка API", "Ошибка соединения"]):
            user_history[uid].append({"role": "assistant", "content": answer})
        
        # Ограничиваем историю (последние 10 сообщений)
        user_history[uid] = user_history[uid][-10:]
        
        bot.reply_to(message, answer)
        
    except Exception as e:
        bot.reply_to(message, f"⚠️ Произошла ошибка: {str(e)[:100]}")

# ==================== ЗАПУСК ====================
if __name__ == "__main__":
    print(f"Бот запущен. Доступно моделей: {len(MODELS)}")
    bot.infinity_polling()