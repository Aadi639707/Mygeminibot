import google.generativeai as genai
from upstash_redis import Redis

# --- CONFIGURATION ---
# Replace with your actual keys
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
REDIS_URL = "YOUR_UPSTASH_REDIS_URL"
REDIS_TOKEN = "YOUR_UPSTASH_REDIS_TOKEN"

# Initialize Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Initialize Redis Memory
redis = Redis(url=REDIS_URL, token=REDIS_TOKEN)

def get_ai_response(user_id, user_input):
    """
    Handles the chat logic, memory, and language adaptation.
    """
    
    # 1. Handle Reset Command
    if user_input.strip().lower() == "/reset":
        redis.delete(user_id)
        return "System: Memory cleared. We can start a new topic now!"

    # 2. Retrieve Chat History from Redis
    # We store history as a string. If no history, it's an empty string.
    chat_history = redis.get(user_id) or ""

    # 3. System Instructions for the AI
    # This ensures it copies my persona and stays on topic.
    system_instruction = (
        "You are an advanced AI assistant, a copy of Gemini. "
        "Rules:\n"
        "1. Stick to the current topic strictly until the user says '/reset'.\n"
        "2. Respond in the EXACT same language the user uses (English, Hindi, Hinglish, etc.).\n"
        "3. Be helpful, insightful, and empathetic.\n"
        "4. If the user asks for an image, describe it vividly (Note: Image API can be added later).\n"
    )

    # 4. Create the full prompt with context
    full_prompt = f"{system_instruction}\n\nChat History:\n{chat_history}\n\nUser: {user_input}\nAI:"

    try:
        # 5. Generate Response
        response = model.generate_content(full_prompt)
        bot_output = response.text

        # 6. Update History in Redis (Saves the conversation)
        updated_history = f"{chat_history}\nUser: {user_input}\nAI: {bot_output}"
        # Setting an expiry (optional) - e.g., memory lasts for 24 hours (86400 seconds)
        redis.set(user_id, updated_history, ex=86400)

        return bot_output

    except Exception as e:
        return f"Error: {str(e)}"

# --- TESTING THE BOT ---
if __name__ == "__main__":
    print("Bot is running! (Type '/reset' to clear memory or 'exit' to stop)")
    user_name = "User_123" # This acts as a unique ID for the user
    
    while True:
        user_msg = input("\nYou: ")
        if user_msg.lower() == "exit":
            break
            
        response = get_ai_response(user_name, user_msg)
        print(f"\nBot: {response}")
