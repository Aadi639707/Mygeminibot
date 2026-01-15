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
    return "Chat Gpt Plus Bot is Running with Strong Memory!"

@app.route('/telegram', methods=['POST'])
def telegram_webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Forbidden', 403

# 2. START COMMAND - User registration
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.from_user.id)
    redis.sadd("bot_users", user_id)
    bot.reply_to(message, "Namaste! Main **Chat Gpt Plus Bot** hoon. Meri memory ab pehle se zyada strong hai, main aapki purani baatein nahi bhoolunga!")

# 3. BROADCAST COMMAND - Fix for Bytes/String
@bot.message_handler(commands=['broadcast'])
def broadcast_msg(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ Admin access denied.")
        return
    
    text = message.text.replace("/broadcast", "").strip()
    if not text:
        bot.reply_to(message, "Sahi tarika: `/broadcast Hello Everyone`")
        return
    
    users = redis.smembers("bot_users")
    if not users:
        bot.reply_to(message, "Database khali hai!")
        return

    count = 0
    for user in users:
        try:
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
        bot.reply_to(message, "Kya banana hai? Prompt dein.")
        return

    bot.reply_to(message, "Theek hai, main image bana raha hoon... thoda wait karein! 🎨")
    try:
        image_url = f"https://image.pollinations.ai/prompt/{prompt}?width=1024&height=1024&nologo=true"
        bot.send_photo(message.chat.id, image_url, caption=f"Ye rahi aapki image: {prompt}")
    except:
        bot.reply_to(message, "Error: Image generation fail ho gaya.")

# 5. STRONG MEMORY CHAT LOGIC
@bot.message_handler(func=lambda message: True)
def chat_with_ai(message):
    user_id = str(message.from_user.id)
    try:
        # Purani memory fetch karna (Memory Retention Fix)
        history = redis.get(f"chat_{user_id}")
        if history and isinstance(history, bytes):
            history = history.decode('utf-8')
        else:
            history = ""

        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system", 
                    "content": "Your name is Chat Gpt Plus Bot. You have an excellent memory. If the user mentions something from earlier in the chat history, acknowledge it. Always reply in natural Hinglish."
                },
                {"role": "user", "content": f"Previous Conversations for Context:\n{history}\n\nNew Message: {message.text}"}
            ],
            model="llama-3.3-70b-versatile",
        )
        reply = chat_completion.choices[0].message.content
        
        # History update: 4000 characters (Large memory) aur 24 hours (86400 seconds) expiry
        new_history = f"{history}\nUser: {message.text}\nAI: {reply}"
        redis.set(f"chat_{user_id}", new_history[-4000:], ex=86400)
        
        bot.reply_to(message, reply)
    except Exception as e:
        print(f"Chat Error: {e}")
        bot.reply_to(message, "Maaf kijiyega, system thoda busy hai.")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
