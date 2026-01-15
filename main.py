import os
import telebot
from flask import Flask, request
from upstash_redis import Redis
from groq import Groq

# 1. Setup - Variables Render se fetch honge
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
REDIS_URL = os.getenv("REDIS_URL")
REDIS_TOKEN = os.getenv("REDIS_TOKEN")
ADMIN_ID = 7757213781  # Aapki Admin ID

bot = telebot.TeleBot(TOKEN)
redis = Redis(url=REDIS_URL, token=REDIS_TOKEN)
app = Flask(__name__)
groq_client = Groq(api_key=GROQ_API_KEY)

@app.route('/')
def home(): 
    return "Chat Gpt Plus Bot is Running!"

@app.route('/telegram', methods=['POST'])
def telegram_webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Forbidden', 403

# 2. START COMMAND - User ID save karne ke liye
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.from_user.id)
    # User ko database mein register karna
    redis.sadd("bot_users", user_id)
    bot.reply_to(message, "Namaste! Main **Chat Gpt Plus Bot** hoon. Main aapke messages aur images banane ke liye taiyar hoon!")

# 3. BROADCAST COMMAND - Sirf aapke liye
@bot.message_handler(commands=['broadcast'])
def broadcast_msg(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ Maaf kijiyega, ye command sirf Admin ke liye hai.")
        return
    
    text = message.text.replace("/broadcast", "").strip()
    if not text:
        bot.reply_to(message, "Usage: `/broadcast Hello dosto`")
        return
    
    users = redis.smembers("bot_users")
    if not users:
        bot.reply_to(message, "Database khali hai! Pehle users ko `/start` karne kahein.")
        return

    count = 0
    for user in users:
        try:
            # Bytes handling fix
            u_id = user.decode('utf-8') if isinstance(user, bytes) else str(user)
            bot.send_message(u_id, text)
            count += 1
        except:
            continue
            
    bot.reply_to(message, f"✅ Message {count} users ko bhej diya gaya hai!")

# 4. IMAGE GENERATION LOGIC
@bot.message_handler(func=lambda message: any(word in message.text.lower() for word in ["image", "photo", "banao", "draw", "pic"]))
def generate_image(message):
    user_text = message.text.lower()
    for word in ["generate", "image", "banao", "create", "draw", "photo", "ki", "ek", "kro", "make"]:
        user_text = user_text.replace(word, "")
    
    prompt = user_text.strip()
    if not prompt:
        bot.reply_to(message, "Kripya batayein ki kya banana hai?")
        return

    bot.reply_to(message, "Theek hai, main aapke liye image bana raha hoon... 🎨")
    try:
        image_url = f"https://image.pollinations.ai/prompt/{prompt}?width=1024&height=1024&nologo=true"
        bot.send_photo(message.chat.id, image_url, caption=f"Ye rahi aapki image: {prompt}")
    except:
        bot.reply_to(message, "Technical error: Image nahi ban saki.")

# 5. CHAT AI LOGIC (Groq)
@bot.message_handler(func=lambda message: True)
def chat_with_ai(message):
    user_id = str(message.from_user.id)
    try:
        history = redis.get(f"chat_{user_id}") or ""
        # Bytes decoding for history
        if isinstance(history, bytes): history = history.decode('utf-8')
        
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system", 
                    "content": "Your name is Chat Gpt Plus Bot. Always reply in natural Hinglish. You can generate images if asked."
                },
                {"role": "user", "content": f"History: {history}\nUser: {message.text}"}
            ],
            model="llama-3.3-70b-versatile",
        )
        reply = chat_completion.choices[0].message.content
        
        # Memory update
        new_history = f"{history}\nUser: {message.text}\nAI: {reply}"
        redis.set(f"chat_{user_id}", new_history[-1000:], ex=3600)
        
        bot.reply_to(message, reply)
    except Exception as e:
        print(f"Error: {e}")
        bot.reply_to(message, "Maaf kijiyega, main abhi busy hoon.")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
    
