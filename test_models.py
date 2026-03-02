import requests
import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

if not GROQ_API_KEY:
    print("ERROR: GROQ_API_KEY not set!")
    exit(1)

headers = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

# Список моделей для проверки
test_models = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant", 
    "llama-3.2-3b-preview",
    "llama-3.2-1b-preview",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
    "gemma-7b-it",
    "qwen-2.5-32b",
    "qwen-2.5-72b",
    "deepseek-r1-distill-llama-70b"
]

print("Checking models...\n")

for model in test_models:
    data = {
        "model": model,
        "messages": [{"role": "user", "content": "test"}],
        "max_tokens": 5
    }
    
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=10
        )
        
        if response.status_code == 200:
            print(f"✅ {model} - WORKING")
        else:
            error = response.json()
            print(f"❌ {model} - {error.get('error', {}).get('message', 'Unknown error')}")
    except Exception as e:
        print(f"❌ {model} - Connection error")

print("\nDone!")