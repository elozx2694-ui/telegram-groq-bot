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

# Проверка токенов
if not TELEGRAM_TOKEN:
    print("ERROR: TELEGRAM_TOKEN not set!")
    sys.exit(1)

if not GROQ_API_KEY:
    print("ERROR: GROQ_API_KEY not set!")
    sys.exit(1)

if not HUGGINGFACE_API_KEY:
    print("ERROR: HUGGINGFACE_API_KEY not set!")
    sys.exit(1)

# URL для API
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Инициализация бота
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# ==================== ТОЛЬКО БЕСПЛАТНЫЕ МОДЕЛИ ====================
MODELS = {
    # ========== GROQ МОДЕЛИ (БЕСПЛАТНО) ==========
    '1': {'name': 'llama-3.3-70b-versatile', 'api': 'groq', 
          'desc': 'Llama 3.3 70B - САМАЯ НОВАЯ (Groq)'},
    '2': {'name': 'llama-3.1-8b-instant', 'api': 'groq', 
          'desc': 'Llama 3.1 8B - БЫСТРАЯ (Groq)'},
    '3': {'name': 'mixtral-8x7b-32768', 'api': 'groq', 
          'desc': 'Mixtral 8x7B - МОЩНАЯ (Groq)'},
    '4': {'name': 'gemma2-9b-it', 'api': 'groq', 
          'desc': 'Gemma 2 9B - GOOGLE (Groq)'},
    '5': {'name': 'deepseek-r1-distill-llama-70b', 'api': 'groq', 
          'desc': 'DeepSeek R1 - РАССУЖДЕНИЯ (Groq)'},
    '6': {'name': 'qwen-2.5-32b', 'api': 'groq', 
          'desc': 'Qwen 2.5 32B (Groq)'},
    '7': {'name': 'qwen-2.5-72b', 'api': 'groq', 
          'desc': 'Qwen 2.5 72B (Groq)'},
    '8': {'name': 'llama-3.2-3b-preview', 'api': 'groq', 
          'desc': 'Llama 3.2 3B - СВЕРХБЫСТРАЯ (Groq)'},
    '9': {'name': 'llama-3.2-1b-preview', 'api': 'groq', 
          'desc': 'Llama 3.2 1B - МИКРО (Groq)'},
    '10': {'name': 'gemma-7b-it', 'api': 'groq', 
           'desc': 'Gemma 7B - GOOGLE (Groq)'},
    '11': {'name': 'llama-guard-3-8b', 'api': 'groq', 
           'desc': 'Llama Guard - БЕЗОПАСНОСТЬ (Groq)'},
    
    # ========== HUGGING FACE МОДЕЛИ (БЕСПЛАТНО) ==========
    '12': {'name': 'microsoft/phi-2', 'api': 'huggingface', 
           'desc': 'Phi-2 - МАЛЕНЬКАЯ НО УМНАЯ (HF)'},
    '13': {'name': 'google/flan-t5-large', 'api': 'huggingface', 
           'desc': 'Flan-T5 Large - GOOGLE (HF)'},
    '14': {'name': 'IlyaGusev/saiga_llama3_8b', 'api': 'huggingface', 
           'desc': 'Saiga - РУССКАЯ ЛУЧШАЯ (HF)'},
    '15': {'name': 'mistralai/Mistral-7B-v0.1', 'api': 'huggingface', 
           'desc': 'Mistral 7B (HF)'},
    '16': {'name': 'tiiuae/falcon-7b-instruct', 'api': 'huggingface', 
           'desc': 'Falcon 7B (HF)'},
    '17': {'name': 'bigscience/bloom-7b1', 'api': 'huggingface', 
           'desc': 'BLOOM 7B - МНОГОЯЗЫЧНАЯ (HF)'},
    '18': {'name': 'microsoft/phi-1_5', 'api': 'huggingface', 
           'desc': 'Phi-1.5 - ДЛЯ КОДА (HF)'},
    '19': {'name': 'EleutherAI/gpt-neox-20b', 'api': 'huggingface', 
           'desc': 'GPT-NeoX 20B (HF)'},
    '20': {'name': 'Salesforce/codegen-6B-mono', 'api': 'huggingface', 
           'desc': 'CodeGen - ПРОГРАММИРОВАНИЕ (HF)'},
    '21': {'name': 'HuggingFaceH4/zephyr-7b-beta', 'api': 'huggingface', 
           'desc': 'Zephyr 7B - ПОМОЩНИК (HF)'},
    '22': {'name': 'mistralai/Mixtral-8x7B-Instruct-v0.1', 'api': 'huggingface', 
           'desc': 'Mixtral 8x7B (HF)'},
    '23': {'name': 'upstage/SOLAR-10.7B-Instruct-v1.0', 'api': 'huggingface', 
           'desc': 'SOLAR 10.7B (HF)'},
    '24': {'name': 'lmsys/vicuna-7b-v1.5', 'api': 'huggingface', 
           'desc': 'Vicuna 7B (HF)'},
    '25': {'name': 'OpenAssistant/oasst-sft-4-pythia-12b-epoch-3.5', 'api': 'huggingface', 
           'desc': 'OpenAssistant 12B (HF)'},
    '26': {'name': 'google/flan-t5-xl', 'api': 'huggingface', 
           'desc': 'Flan-T5 XL - GOOGLE (HF)'},
    '27': {'name': 'meta-llama/Llama-2-7b-chat-hf', 'api': 'huggingface', 
           'desc': 'Llama 2 7B (HF)'},
    '28': {'name': 'meta-llama/Llama-2-13b-chat-hf', 'api': 'huggingface', 
           'desc': 'Llama 2 13B (HF)'},
    '29': {'name': 'tiiuae/falcon-40b-instruct', 'api': 'huggingface', 
           'desc': 'Falcon 40B (HF)'},
    '30': {'name': 'mistralai/Mistral-7B-Instruct-v0.2', 'api': 'huggingface', 
           'desc': 'Mistral 7B v0.2 (HF)'},
    '31': {'name': 'google/gemma-2b-it', 'api': 'huggingface', 
           'desc': 'Gemma 2B (HF)'},
    '32': {'name': 'google/gemma-7b-it', 'api': 'huggingface', 
           'desc': 'Gemma 7B (HF)'},
    '33': {'name': 'microsoft/phi-3-mini-128k-instruct', 'api': 'huggingface', 
           'desc': 'Phi-3 Mini (HF)'},
    '34': {'name': 'microsoft/phi-3-medium-128k-instruct', 'api': 'huggingface', 
           'desc': 'Phi-3 Medium (HF)'},
    '35': {'name': 'deepseek-ai/deepseek-llm-7b-chat', 'api': 'huggingface', 
           'desc': 'DeepSeek 7B (HF)'},
    '36': {'name': 'Qwen/Qwen2.5-7B-Instruct', 'api': 'huggingface', 
           'desc': 'Qwen 2.5 7B (HF)'},
    '37': {'name': 'Qwen/Qwen2.5-14B-Instruct', 'api': 'huggingface', 
           'desc': 'Qwen 2.5 14B (HF)'},
    '38': {'name': 'Qwen/Qwen2.5-32B-Instruct', 'api': 'huggingface', 
           'desc': 'Qwen 2.5 32B (HF)'},
    '39': {'name': 'Qwen/Qwen2.5-72B-Instruct', 'api': 'huggingface', 
           'desc': 'Qwen 2.5 72B (HF)'},
    '40': {'name': 'NousResearch/Nous-Hermes-2-Mixtral-8x7B-DPO', 'api': 'huggingface', 
           'desc': 'Hermes 2 Mixtral (HF)'},
}

# Модель по умолчанию - Llama 3.3 (лучшая бесплатная)
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
    if not GROQ_API_KEY:
        return "⚠️ Groq API key not set!"
    
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
            return f"⚠️ Groq API Error: {response.status_code}"
        
        result = response.json()
        return result['choices'][0]['message']['content']
        
    except Exception as e:
        return f"⚠️ Groq Error: {str(e)[:100]}"

def ask_huggingface(messages, model):
    """Запрос к Hugging Face API"""
    if not HUGGINGFACE_API_KEY:
        return "⚠️ Hugging Face API key not set!"
    
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
            return "⚠️ Model is loading on Hugging Face. Please try again in 10 seconds."
        elif response.status_code != 200:
            return f"⚠️ HF API Error: {response.status_code}"
        
        result = response.json()
        
        # Разные форматы ответов
        if isinstance(result, list):
            if len(result) > 0:
                if 'generated_text' in result[0]:
                    return result[0]['generated_text']
                elif isinstance(result[0], dict) and 'text' in result[0]:
                    return result[0]['text']
        
        return str(result)[:500]
        
    except requests.exceptions.Timeout:
        return "⚠️ Hugging Face API timeout"
    except Exception as e:
        return f"⚠️ HF Error: {str(e)[:100]}"

@bot.message_handler(commands=['start', 'help'])
def start(message):
    text = (
        "🤖 FREE AI BOT - 40 MODELS\n"
        "==========================\n\n"
        f"✨ Current: {MODELS['1']['desc']}\n\n"
        "📋 Commands:\n"
        "• /models - list all 40 FREE models\n"
        "• /model [1-40] - select model by number\n"
        "• /clear - clear history\n"
        "• /help - this menu\n\n"
        "🔥 ALL MODELS ARE 100% FREE!\n"
        "💎 No payment required!"
    )
    bot.reply_to(message, text)

@bot.message_handler(commands=['models'])
def show_models(message):
    text = "📊 *ALL FREE MODELS (1=best, 40=fastest):*\n"
    text += "=======================================\n\n"
    
    for num in range(1, 21):
        num_str = str(num)
        model_info = MODELS[num_str]
        if model_info['name'] == current_model:
            text += f"✅ *{num_str}.* {model_info['desc']}*\n"
        else:
            text += f"   {num_str}. {model_info['desc']}\n"
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")
    
    text2 = "📊 *FREE MODELS 21-40:*\n"
    text2 += "=======================\n\n"
    for num in range(21, 41):
        num_str = str(num)
        model_info = MODELS[num_str]
        if model_info['name'] == current_model:
            text2 += f"✅ *{num_str}.* {model_info['desc']}*\n"
        else:
            text2 += f"   {num_str}. {model_info['desc']}\n"
    
    text2 += "\nSelect: /model [number]\n"
    text2 += "Example: /model 1 for Llama 3.3"
    
    bot.send_message(message.chat.id, text2, parse_mode="Markdown")

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
                f"✅ Now using: {MODELS[num]['desc']}\n📡 API: {current_api}"
            )
        else:
            bot.reply_to(message, f"❌ Invalid number. Use 1-{len(MODELS)}")
    except:
        bot.reply_to(message, "❌ Use: /model [number]")

@bot.message_handler(commands=['clear'])
def clear_history(message):
    user_id = message.from_user.id
    if user_id in user_history:
        user_history[user_id] = []
        bot.reply_to(message, "🧹 History cleared!")
    else:
        bot.reply_to(message, "📭 History is already empty.")

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
        else:  # huggingface
            answer = ask_huggingface(user_history[user_id], current_model)
        
        if not answer.startswith("⚠️"):
            user_history[user_id].append({"role": "assistant", "content": answer})
        
        bot.reply_to(message, answer)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)[:100]}")

print("=" * 70)
print("🤖 FREE AI BOT - 40 MODELS")
print("=" * 70)
print(f"📱 Telegram: {'✅' if TELEGRAM_TOKEN else '❌'}")
print(f"⚡ Groq: {'✅' if GROQ_API_KEY else '❌'}")
print(f"🤗 Hugging Face: {'✅' if HUGGINGFACE_API_KEY else '❌'}")
print(f"🎯 Current: {MODELS['1']['desc']}")
print(f"📊 Total FREE models: {len(MODELS)}")
print("=" * 70)
print("✅ ALL MODELS ARE 100% FREE!")
print("✅ Groq models 1-11: Llama, Mixtral, Gemma, Qwen")
print("✅ Hugging Face models 12-40: Phi, Saiga, Falcon, Bloom, etc.")
print("=" * 70)

if __name__ == "__main__":
    try:
        bot.remove_webhook()
        time.sleep(1)
        bot.infinity_polling(timeout=60)
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")