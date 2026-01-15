import os
from flask import Flask, request
import google.generativeai as genai
from upstash_redis import Redis
import requests

app = Flask(__name__)

# Config from Environment Variables
GEMINI_KEY = os.getenv("GEMINI_KEY")
REDIS_URL = os.getenv("REDIS_URL")
REDIS_TOKEN = os.getenv("REDIS_TOKEN")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

genai.configure(api_key=GEMINI_KEY)
redis = Redis(url=REDIS_URL, token=REDIS_TOKEN)
model = genai.GenerativeModel('gemini-1.5-flash')

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

@app.route('/telegram', methods=['POST'])
def webhook():
    data = request.json
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        user_msg = data["message"].get("text", "")

        if user_msg.lower() == "/reset":
            redis.delete(chat_id)
            send_message(chat_id, "Memory reset! What's next?")
            return "ok"

        # Image Logic
        if "image" in user_msg.lower() or "photo" in user_msg.lower():
            img_url = f"https://image.pollinations.ai/prompt/{user_msg.replace(' ', '%20')}"
            send_message(chat_id, f"Here is your image: {img_url}")
            return "ok"

        # AI Chat Memory
        history = redis.get(chat_id) or ""
        system_instruction = "You are Gemini. Stay on topic until /reset. Use user's language."
        full_prompt = f"{system_instruction}\nHistory: {history}\nUser: {user_msg}\nAI:"
        
        response = model.generate_content(full_prompt)
        bot_reply = response.text
        
        redis.set(chat_id, f"{history}\nUser: {user_msg}\nAI: {bot_reply}", ex=86400)
        send_message(chat_id, bot_reply)
    return "ok"

@app.route('/')
def health(): return "Bot is Alive!"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
            
