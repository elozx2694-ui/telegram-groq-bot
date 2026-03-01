import telebot
import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    print("Ошибка: Не заданы токены в переменных окружения")
    exit(1)

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# URL для Groq API
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Доступные модели
MODELS = {
    '1': 'llama-3.1-70b-versatile',
    '2': 'llama-3.1-8b-instant',
    '3': 'mixtral-8x7b-32768',
    '4': 'gemma2-9b-it',
    '5': 'deepseek-r1-distill-llama-70b'
}

current_model = 'llama-3.1-8b-instant'
user_history = {}

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
    except requests.exceptions.RequestException as e:
        raise Exception(f"Ошибка запроса к Groq API: {str(e)}")

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(
        message,
        "Привет! Я бот с доступом к нейросетям через Groq.\n\n"
        "Команды:\n"
        "/models - список моделей\n"
        "/model [номер] - выбрать модель\n"
        "/clear - очистить историю\n\n"
        "Просто напиши сообщение и я отвечу."
    )

@bot.message_handler(commands=['models'])
def show_models(message):
    text = "Доступные модели:\n\n"
    for num, model in MODELS.items():
        mark = ">>" if model == current_model else "  "
        text += f"{mark} {num}. {model}\n"
    text += "\nЧтобы выбрать: /model [номер]\nНапример: /model 2"
    bot.reply_to(message, text)

@bot.message_handler(commands=['model'])
def set_model(message):
    global current_model
    try:
        num = message.text.split()[1]
        if num in MODELS:
            current_model = MODELS[num]
            bot.reply_to(message, f"Модель изменена на: {current_model}")
        else:
            bot.reply_to(message, "Неверный номер. Используй /models")
    except:
        bot.reply_to(message, "Формат: /model [номер]\nНапример: /model 2")

@bot.message_handler(commands=['clear'])
def clear_history(message):
    user_id = message.from_user.id
    if user_id in user_history:
        user_history[user_id] = []
    bot.reply_to(message, "История очищена.")

@bot.message_handler(func=lambda m: True)
def chat(message):
    user_id = message.from_user.id
    
    if user_id not in user_history:
        user_history[user_id] = []
    
    user_history[user_id].append({"role": "user", "content": message.text})
    
    if len(user_history[user_id]) > 20:
        user_history[user_id] = user_history[user_id][-20:]
    
    try:
        answer = ask_groq(user_history[user_id], current_model)
        user_history[user_id].append({"role": "assistant", "content": answer})
        bot.reply_to(message, answer)
        
    except Exception as e:
        error_text = str(e)
        if '403' in error_text:
            bot.reply_to(message, "Ошибка доступа к Groq API. Проверь ключ в настройках")
        elif 'model_not_found' in error_text:
            bot.reply_to(message, f"Модель {current_model} не найдена. Выбери другую через /models")
        else:
            bot.reply_to(message, f"Ошибка: {error_text[:100]}")

print("Бот запущен!")
bot.infinity_polling()