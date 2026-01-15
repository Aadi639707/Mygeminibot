import os
import telebot
import google.generativeai as genai
from flask import Flask, request
from upstash_redis import Redis

# 1. API Keys and Tokens (Environment Variables se aayenge)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_KEY")
REDIS_URL = os.getenv("REDIS_URL")
REDIS_TOKEN = os.getenv("REDIS_TOKEN")

# 2. Setup
bot = telebot.TeleBot(TOKEN)
genai.configure(api_key=GEMINI_KEY)
redis = Redis(url=REDIS_URL, token=REDIS_TOKEN)
app = Flask(__name__)

# Gemini Model Settings
model = genai.GenerativeModel('gemini-1.5-flash')

@app.route('/')
def home():
    return "Bot is Running!"

# 3. Webhook Route (Yahi rasta hai jo Telegram use karega)
@app.route('/telegram', methods=['POST'])
def telegram_webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Forbidden', 403

# 4. Bot Logic
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Namaste! Main Gemini AI bot hoon. Aap mujhse kuch bhi pooch sakte hain.")

@bot.message_handler(func=lambda message: True)
def chat_with_gemini(message):
    user_id = str(message.from_user.id)
    user_input = message.text

    try:
        # Chat History from Redis (Optional: basic memory)
        history = redis.get(f"chat_{user_id}") or ""
        full_prompt = f"{history}\nUser: {user_input}\nAI:"

        # Generate Response from Gemini
        response = model.generate_content(full_prompt)
        reply_text = response.text

        # Update History
        new_history = f"{full_prompt} {reply_text}"[-1000:] # Last 1000 chars save karega
        redis.set(f"chat_{user_id}", new_history, ex=3600) # 1 hour memory

        bot.reply_to(message, reply_text)

    except Exception as e:
        print(f"Error: {e}")
        bot.reply_to(message, "Maaf kijiyega, abhi mere system mein thodi dikkat aa rahi hai.")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
    
