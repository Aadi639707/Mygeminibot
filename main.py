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

# 4. Bot Logic
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    # Yahan humne naam badal diya hai
    bot.reply_to(message, "Namaste! Main **Chat Gpt Plus Bot** hoon. Aap mujhse kuch bhi pooch sakte hain aur images bhi bana sakte hain!")

@bot.message_handler(func=lambda message: message.text and message.text.lower().startswith("generate image of"))
def generate_image(message):
    prompt = message.text[len("generate image of"):].strip()
    if not prompt:
        bot.reply_to(message, "Please provide a description. Example: 'generate image of a lion'")
        return
    bot.reply_to(message, "Generating your image... please wait!")
    try:
        image_url = f"https://image.pollinations.ai/prompt/{prompt}"
        bot.send_photo(message.chat.id, image_url, caption=f"Here is your image: {prompt}")
    except Exception as e:
        bot.reply_to(message, "Image nahi ban saki, firse try karein.")

@bot.message_handler(func=lambda message: True)
def chat_with_ai(message):
    user_id = str(message.from_user.id)
    user_input = message.text
    try:
        history = redis.get(f"chat_{user_id}") or ""
        
        # Groq model call with stable model name
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Your name is Chat Gpt Plus Bot. You are a helpful assistant."},
                {"role": "user", "content": f"History: {history}\nUser: {user_input}"}
            ],
            model="llama-3.3-70b-versatile", # Sabse stable model
        )
        reply_text = chat_completion.choices[0].message.content

        # Update History
        new_history = f"{history}\nUser: {user_input}\nAI: {reply_text}"
        redis.set(f"chat_{user_id}", new_history[-1500:], ex=3600)

        bot.reply_to(message, reply_text)
    except Exception as e:
        print(f"Error: {e}")
        bot.reply_to(message, "Maaf kijiyega, mere system mein abhi dikkat hai. Apni API Key check karein.")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
    
