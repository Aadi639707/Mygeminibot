import os
import telebot
import requests
from flask import Flask, request
from upstash_redis import Redis
from groq import Groq # Groq library import karenge

# 1. API Keys and Tokens (Environment Variables se aayenge)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY") # Ab Groq ki key use hogi
REDIS_URL = os.getenv("REDIS_URL")
REDIS_TOKEN = os.getenv("REDIS_TOKEN")

# 2. Setup
bot = telebot.TeleBot(TOKEN)
redis = Redis(url=REDIS_URL, token=REDIS_TOKEN)
app = Flask(__name__)

# Groq Client Setup
groq_client = Groq(api_key=GROQ_API_KEY)

# 3. Webhook Route
@app.route('/')
def home():
    return "Bot is Running with Groq!"

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
    bot.reply_to(message, "Namaste! Main Groq AI bot hoon. Aap mujhse kuch bhi pooch sakte hain aur images bhi bana sakte hain!")

@bot.message_handler(func=lambda message: message.text and message.text.lower().startswith("generate image of"))
def generate_image(message):
    prompt = message.text[len("generate image of"):].strip()
    if not prompt:
        bot.reply_to(message, "Please provide a description for the image. Example: 'generate image of a cat in space'")
        return

    bot.reply_to(message, "Sure, generating your image... please wait a moment!")
    try:
        # Using Pollinations AI for image generation
        # Pollinations API documentation: https://docs.pollinations.ai/
        image_url = f"https://image.pollinations.ai/prompt/{prompt}"
        
        # Telegram ko image URL bhej rahe hain
        bot.send_photo(message.chat.id, image_url, caption=f"Here is your image of: {prompt}")

    except Exception as e:
        print(f"Image generation error: {e}")
        bot.reply_to(message, "Sorry, I couldn't generate the image right now.")

@bot.message_handler(func=lambda message: True)
def chat_with_groq(message):
    user_id = str(message.from_user.id)
    user_input = message.text

    try:
        # Chat History from Redis
        history = redis.get(f"chat_{user_id}")
        
        messages = []
        if history:
            # History ko list of dicts mein convert karein
            # Isko parse karna padega, yahan simple string se kaam chala rahe hain
            messages.append({"role": "user", "content": history}) 
        
        messages.append({"role": "user", "content": user_input})

        # Generate Response from Groq
        chat_completion = groq_client.chat.completions.create(
            messages=messages,
            model="llama3-8b-8192", # Aap Mixtral ya dusra model bhi choose kar sakte hain
            # seed=1337, # Optional, consistent responses ke liye
        )
        reply_text = chat_completion.choices[0].message.content

        # Update History in Redis
        new_history = f"{history}\nUser: {user_input}\nAI: {reply_text}" if history else f"User: {user_input}\nAI: {reply_text}"
        redis.set(f"chat_{user_id}", new_history[-2000:], ex=3600) # Last 2000 chars, 1 hour memory

        bot.reply_to(message, reply_text)

    except Exception as e:
        print(f"Groq chat error: {e}")
        bot.reply_to(message, "Maaf kijiyega, abhi Groq AI mein thodi dikkat aa rahi hai.")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
    
