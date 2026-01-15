import os
import telebot
import requests
from flask import Flask, request
from upstash_redis import Redis
from groq import Groq

# 1. API Keys
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
REDIS_URL = os.getenv("REDIS_URL")
REDIS_TOKEN = os.getenv("REDIS_TOKEN")

# 2. Setup
bot = telebot.TeleBot(TOKEN)
redis = Redis(url=REDIS_URL, token=REDIS_TOKEN)
app = Flask(__name__)
groq_client = Groq(api_key=GROQ_API_KEY)

@app.route('/')
def home():
    return "Bot is Running!"

@app.route('/telegram', methods=['POST'])
def telegram_webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Forbidden', 403

# 4. Bot Logic - Image Generation (Sahi Keywords ke sath)
@bot.message_handler(func=lambda message: any(word in message.text.lower() for word in ["image", "photo", "banao", "create", "make"]))
def generate_image(message):
    user_text = message.text.lower()
    # Prompt nikalne ka tareeka
    prompt = user_text.replace("generate", "").replace("image", "").replace("banao", "").replace("create", "").replace("ki", "").strip()
    
    if not prompt or len(prompt) < 3:
        bot.reply_to(message, "Kripya batayein ki kis cheez ki image banani hai? (Example: 'Ek sher ki image banao')")
        return

    bot.reply_to(message, "Theek hai, main aapke liye image bana raha hoon... thoda intezar karein! 🎨")
    try:
        image_url = f"https://image.pollinations.ai/prompt/{prompt}"
        bot.send_photo(message.chat.id, image_url, caption=f"Ye rahi aapki image: {prompt}")
    except Exception as e:
        bot.reply_to(message, "Maaf kijiyega, image generation mein error aaya.")

# 5. Chat Logic - Sahi Hindi ke liye
@bot.message_handler(func=lambda message: True)
def chat_with_ai(message):
    user_id = str(message.from_user.id)
    user_input = message.text
    try:
        history = redis.get(f"chat_{user_id}") or ""
        
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system", 
                    "content": "Your name is Chat Gpt Plus Bot. Always reply in clear and natural Hinglish (Hindi + English). Don't use broken sentences. If a user asks to create an image, tell them to use keywords like 'image' or 'banao'."
                },
                {"role": "user", "content": f"History: {history}\nUser: {user_input}"}
            ],
            model="llama-3.3-70b-versatile",
        )
        reply_text = chat_completion.choices[0].message.content

        # Update History
        new_history = f"{history}\nUser: {user_input}\nAI: {reply_text}"
        redis.set(f"chat_{user_id}", new_history[-1000:], ex=3600)

        bot.reply_to(message, reply_text)
    except Exception as e:
        bot.reply_to(message, "System error! Please try again later.")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
    
