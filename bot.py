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

# Токены из переменных окружения Render
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
HUGGINGFACE_API_KEY = os.environ.get('HUGGINGFACE_API_KEY')
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')

# Проверка токенов
if not TELEGRAM_TOKEN:
    print("ERROR: TELEGRAM_TOKEN not set!")
    sys.exit(1)

# Проверяем какие API доступны
GROQ_AVAILABLE = bool(GROQ_API_KEY)
HF_AVAILABLE = bool(HUGGINGFACE_API_KEY)
OR_AVAILABLE = bool(OPENROUTER_API_KEY)

print("=" * 70)
print("API STATUS:")
print(f"Groq API: {'✅ AVAILABLE' if GROQ_AVAILABLE else '❌ NOT SET'}")
print(f"Hugging Face API: {'✅ AVAILABLE' if HF_AVAILABLE else '❌ NOT SET'}")
print(f"OpenRouter API: {'✅ AVAILABLE' if OR_AVAILABLE else '❌ NOT SET'}")
print("=" * 70)

if not GROQ_AVAILABLE and not HF_AVAILABLE and not OR_AVAILABLE:
    print("ERROR: No APIs available! Please set at least one API key.")
    sys.exit(1)

# URL для API
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Инициализация бота
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# ==================== ВСЕ МОДЕЛИ ====================
ALL_MODELS = {
    # ========== OPENROUTER МОДЕЛИ (ПЕРВЫЕ) ==========
    '1': {'name': 'openrouter/healer-alpha', 'api': 'openrouter',
          'desc': '🧠 Healer Alpha - Целитель (OpenRouter)'},
    '2': {'name': 'openrouter/hunter-alpha', 'api': 'openrouter',
          'desc': '🎯 Hunter Alpha - Охотник (OpenRouter)'},

    # ========== GROQ МОДЕЛИ (БЕСПЛАТНО) ==========
    '3': {'name': 'llama-3.3-70b-versatile', 'api': 'groq',
          'desc': 'Llama 3.3 70B - САМАЯ НОВАЯ (Groq)'},
    '4': {'name': 'llama-3.1-8b-instant', 'api': 'groq',
          'desc': 'Llama 3.1 8B - БЫСТРАЯ (Groq)'},
    '5': {'name': 'mixtral-8x7b-32768', 'api': 'groq',
          'desc': 'Mixtral 8x7B - МОЩНАЯ (Groq)'},
    '6': {'name': 'gemma2-9b-it', 'api': 'groq',
          'desc': 'Gemma 2 9B - GOOGLE (Groq)'},
    '7': {'name': 'deepseek-r1-distill-llama-70b', 'api': 'groq',
          'desc': 'DeepSeek R1 - РАССУЖДЕНИЯ (Groq)'},
    '8': {'name': 'qwen-2.5-32b', 'api': 'groq',
          'desc': 'Qwen 2.5 32B (Groq)'},
    '9': {'name': 'qwen-2.5-72b', 'api': 'groq',
          'desc': 'Qwen 2.5 72B (Groq)'},
    '10': {'name': 'llama-3.2-3b-preview', 'api': 'groq',
           'desc': 'Llama 3.2 3B - СВЕРХБЫСТРАЯ (Groq)'},
    '11': {'name': 'llama-3.2-1b-preview', 'api': 'groq',
           'desc': 'Llama 3.2 1B - МАЛАЯ (Groq)'},
    '12': {'name': 'gemma-7b-it', 'api': 'groq',
           'desc': 'Gemma 7B - GOOGLE (Groq)'},
    '13': {'name': 'llama-guard-3-8b', 'api': 'groq',
           'desc': 'Llama Guard - БЕЗОПАСНОСТЬ (Groq)'},

    # ========== HUGGING FACE МОДЕЛИ (БЕСПЛАТНО) ==========
    '14': {'name': 'microsoft/phi-2', 'api': 'huggingface',
           'desc': 'Phi-2 - МАЛЕНЬКАЯ НО УМНАЯ (HF)'},
    '15': {'name': 'google/flan-t5-large', 'api': 'huggingface',
           'desc': 'Flan-T5 Large - GOOGLE (HF)'},
    '16': {'name': 'IlyaGusev/saiga_llama3_8b', 'api': 'huggingface',
           'desc': 'Saiga - РУССКАЯ ЛУЧШАЯ (HF)'},
    '17': {'name': 'mistralai/Mistral-7B-v0.1', 'api': 'huggingface',
           'desc': 'Mistral 7B (HF)'},
    '18': {'name': 'tiiuae/falcon-7b-instruct', 'api': 'huggingface',
           'desc': 'Falcon 7B (HF)'},
    '19': {'name': 'bigscience/bloom-7b1', 'api': 'huggingface',
           'desc': 'BLOOM 7B - МНОГОЯЗЫЧНАЯ (HF)'},
    '20': {'name': 'microsoft/phi-1_5', 'api': 'huggingface',
           'desc': 'Phi-1.5 - ДЛЯ КОДА (HF)'},
    '21': {'name': 'EleutherAI/gpt-neox-20b', 'api': 'huggingface',
           'desc': 'GPT-NeoX 20B (HF)'},
    '22': {'name': 'Salesforce/codegen-6B-mono', 'api': 'huggingface',
           'desc': 'CodeGen - ПРОГРАММИРОВАНИЕ (HF)'},
    '23': {'name': 'HuggingFaceH4/zephyr-7b-beta', 'api': 'huggingface',
           'desc': 'Zephyr 7B - ПОМОЩНИК (HF)'},
    '24': {'name': 'mistralai/Mixtral-8x7B-Instruct-v0.1', 'api': 'huggingface',
           'desc': 'Mixtral 8x7B (HF)'},
    '25': {'name': 'upstage/SOLAR-10.7B-Instruct-v1.0', 'api': 'huggingface',
           'desc': 'SOLAR 10.7B (HF)'},
    '26': {'name': 'lmsys/vicuna-7b-v1.5', 'api': 'huggingface',
           'desc': 'Vicuna 7B (HF)'},
    '27': {'name': 'OpenAssistant/oasst-sft-4-pythia-12b-epoch-3.5', 'api': 'huggingface',
           'desc': 'OpenAssistant 12B (HF)'},
    '28': {'name': 'google/flan-t5-xl', 'api': 'huggingface',
           'desc': 'Flan-T5 XL - GOOGLE (HF)'},
    '29': {'name': 'meta-llama/Llama-2-7b-chat-hf', 'api': 'huggingface',
           'desc': 'Llama 2 7B (HF)'},
    '30': {'name': 'meta-llama/Llama-2-13b-chat-hf', 'api': 'huggingface',
           'desc': 'Llama 2 13B (HF)'},
    '31': {'name': 'tiiuae/falcon-40b-instruct', 'api': 'huggingface',
           'desc': 'Falcon 40B (HF)'},
    '32': {'name': 'mistralai/Mistral-7B-Instruct-v0.2', 'api': 'huggingface',
           'desc': 'Mistral 7B v0.2 (HF)'},
    '33': {'name': 'google/gemma-2b-it', 'api': 'huggingface',
           'desc': 'Gemma 2B (HF)'},
    '34': {'name': 'google/gemma-7b-it', 'api': 'huggingface',
           'desc': 'Gemma 7B (HF)'},
    '35': {'name': 'microsoft/phi-3-mini-128k-instruct', 'api': 'huggingface',
           'desc': 'Phi-3 Mini (HF)'},
    '36': {'name': 'microsoft/phi-3-medium-128k-instruct', 'api': 'huggingface',
           'desc': 'Phi-3 Medium (HF)'},
    '37': {'name': 'deepseek-ai/deepseek-llm-7b-chat', 'api': 'huggingface',
           'desc': 'DeepSeek 7B (HF)'},
    '38': {'name': 'Qwen/Qwen2.5-7B-Instruct', 'api': 'huggingface',
           'desc': 'Qwen 2.5 7B (HF)'},
    '39': {'name': 'Qwen/Qwen2.5-14B-Instruct', 'api': 'huggingface',
           'desc': 'Qwen 2.5 14B (HF)'},
    '40': {'name': 'Qwen/Qwen2.5-32B-Instruct', 'api': 'huggingface',
           'desc': 'Qwen 2.5 32B (HF)'},
    '41': {'name': 'Qwen/Qwen2.5-72B-Instruct', 'api': 'huggingface',
           'desc': 'Qwen 2.5 72B (HF)'},
    '42': {'name': 'NousResearch/Nous-Hermes-2-Mixtral-8x7B-DPO', 'api': 'huggingface',
           'desc': 'Hermes 2 Mixtral (HF)'},
}

# Фильтруем модели по доступным API
MODELS = {}
for num, model_info in ALL_MODELS.items():
    if model_info['api'] == 'groq' and GROQ_AVAILABLE:
        MODELS[num] = model_info
    elif model_info['api'] == 'huggingface' and HF_AVAILABLE:
        MODELS[num] = model_info
    elif model_info['api'] == 'openrouter' and OR_AVAILABLE:
        MODELS[num] = model_info

if not MODELS:
    print("ERROR: No models available with current API keys!")
    sys.exit(1)

# Модель по умолчанию - первая доступная (Healer Alpha)
first_key = list(MODELS.keys())[0]
current_model = MODELS[first_key]['name']
current_api = MODELS[first_key]['api']
user_history = {}

print(f"Available models: {len(MODELS)}")
print(f"Default model: {MODELS[first_key]['desc']}")

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

# ========== KEEP AWAKE - предотвращает засыпание на Render ==========
RENDER_URL = "https://telegram-bot-90ez.onrender.com"

def keep_awake():
    """Пингует сервер каждые 5 минут, чтобы не уснуть"""
    print(f"Keep-awake started for {RENDER_URL}")
    while True:
        try:
            response = requests.get(RENDER_URL, timeout=10)
            print(f"Keep-awake ping: {response.status_code}")
        except Exception as e:
            print(f"Keep-awake error: {e}")
        time.sleep(300)  # 5 минут

awake_thread = threading.Thread(target=keep_awake, daemon=True)
awake_thread.start()
# ====================================================================

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
        response = requests.post(GROQ_API_URL, headers=headers, json=data, timeout=30)

        if response.status_code != 200:
            return f"Groq API Error: {response.status_code}"

        result = response.json()
        return result['choices'][0]['message']['content']

    except Exception as e:
        return f"Groq Error: {str(e)[:100]}"

def ask_openrouter(messages, model):
    """Запрос к OpenRouter API"""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://t.me/your_bot",
        "X-Title": "AI Bot"
    }

    clean_messages = []
    for msg in messages[-10:]:
        if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
            clean_messages.append({
                'role': msg['role'],
                'content': str(msg['content'])[:4000]
            })

    data = {
        "model": model,
        "messages": clean_messages,
        "temperature": 0.7,
        "max_tokens": 2048,
        "top_p": 1
    }

    try:
        response = requests.post(OPENROUTER_API_URL, headers=headers, json=data, timeout=60)

        if response.status_code != 200:
            return f"OpenRouter API Error: {response.status_code} - {response.text[:200]}"

        result = response.json()
        return result['choices'][0]['message']['content']

    except Exception as e:
        return f"OpenRouter Error: {str(e)[:150]}"

def ask_huggingface(messages, model):
    """Запрос к Hugging Face API"""
    if not HUGGINGFACE_API_KEY:
        return "Hugging Face API key not set!"

    API_URL = f"https://api-inference.huggingface.co/models/{model}"
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}

    last_message = messages[-1]['content']

    data = {
        "inputs": last_message,
        "parameters": {
            "max_new_tokens": 200,
            "temperature": 0.7,
            "top_p": 0.95,
            "do_sample": True
        }
    }

    try:
        response = requests.post(API_URL, headers=headers, json=data, timeout=60)

        if response.status_code == 503:
            return "Model is loading on Hugging Face. Please try again in 10 seconds."
        elif response.status_code != 200:
            return f"HF API Error: {response.status_code}"

        result = response.json()

        if isinstance(result, list) and len(result) > 0:
            if 'generated_text' in result[0]:
                return result[0]['generated_text']
            elif isinstance(result[0], dict) and 'text' in result[0]:
                return result[0]['text']

        return str(result)[:500]

    except Exception as e:
        return f"HF Error: {str(e)[:100]}"

@bot.message_handler(commands=['start', 'help'])
def start(message):
    text = (
        "🤖 FREE AI BOT\n"
        "===========\n\n"
        f"Текущая модель: {MODELS[first_key]['desc']}\n"
        f"Доступные API: {'Groq ✅ ' if GROQ_AVAILABLE else ''}{'HF ✅ ' if HF_AVAILABLE else ''}{'OpenRouter ✅' if OR_AVAILABLE else ''}\n\n"
        "Команды:\n"
        "/models - список моделей\n"
        "/model [номер] - выбор модели\n"
        "/clear - очистить историю\n"
        "/help - это меню\n\n"
        f"Всего моделей: {len(MODELS)}"
    )
    bot.reply_to(message, text)

@bot.message_handler(commands=['models'])
def show_models(message):
    text = f"📋 МОДЕЛИ ({len(MODELS)}):\n"
    text += "====================\n\n"

    for num, model_info in MODELS.items():
        if model_info['name'] == current_model:
            text += f">> {num}. {model_info['desc']} (активна)\n"
        else:
            text += f"   {num}. {model_info['desc']}\n"

    text += "\nВыбор: /model [номер]"
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['model'])
def set_model(message):
    global current_model, current_api

    try:
        num = message.text.split()[1]
        if num in MODELS:
            current_model = MODELS[num]['name']
            current_api = MODELS[num]['api']
            bot.reply_to(
                message,
                f"✅ Теперь используется: {MODELS[num]['desc']}"
            )
        else:
            bot.reply_to(message, f"❌ Неверный номер. Доступно: 1-{list(MODELS.keys())[-1]}")
    except:
        bot.reply_to(message, "Используй: /model [номер]")

@bot.message_handler(commands=['clear'])
def clear_history(message):
    user_id = message.from_user.id
    if user_id in user_history:
        user_history[user_id] = []
        bot.reply_to(message, "🗑 История очищена!")
    else:
        bot.reply_to(message, "История уже пуста.")

@bot.message_handler(func=lambda m: True)
def chat(message):
    global current_model, current_api
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
        elif current_api == 'openrouter':
            answer = ask_openrouter(user_history[user_id], current_model)
        elif current_api == 'huggingface':
            answer = ask_huggingface(user_history[user_id], current_model)
        else:
            answer = "❌ Неизвестный API"

        if answer and not answer.startswith("Error:") and not answer.startswith("Groq Error:") and not answer.startswith("HF Error:") and not answer.startswith("OpenRouter Error:"):
            user_history[user_id].append({"role": "assistant", "content": answer})

        bot.reply_to(message, answer)

    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)[:100]}")

print("=" * 70)
print("🤖 FREE AI BOT")
print("=" * 70)
print(f"Telegram: {'OK' if TELEGRAM_TOKEN else 'ERROR'}")
print(f"Groq: {'OK' if GROQ_AVAILABLE else 'MISSING'}")
print(f"Hugging Face: {'OK' if HF_AVAILABLE else 'MISSING'}")
print(f"OpenRouter: {'OK' if OR_AVAILABLE else 'MISSING'}")
print(f"Available models: {len(MODELS)}")
print(f"Default: {MODELS[first_key]['desc']}")
print("=" * 70)

if __name__ == "__main__":
    try:
        bot.remove_webhook()
        time.sleep(1)
        bot.infinity_polling(timeout=60)
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")