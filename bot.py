import json
import time
import os
from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

# --- Environment Variables ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
LOG_URL = os.environ.get("LOG_URL") 

LOG_FILE = "run.jsonl"

# Keeps the last few messages per chat, so multi-turn questions work —
# "answer the LAST message" still needs the earlier ones for context.
conversation_history = {}

def log_event(event: dict):
    event["timestamp"] = time.time()
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(event) + "\n")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_text = update.message.text
    log_event({"type": "incoming", "chat_id": chat_id, "text": user_text})

    history = conversation_history.setdefault(chat_id, [])
    history.append({"role": "user", "content": user_text})

    # Ask the AI to work out the answer. The system prompt tells it exactly how to
    # format the final reply — this is the part that MUST match what the question asked.
    system_prompt = (
        "You are a careful data analyst. The user's LAST message asks a data-analysis "
        "question and tells you exactly what JSON shape to reply with. Work out the "
        "real answer (use any public data you know, e.g. MOSPI statistics, general "
        "world knowledge, or arithmetic on numbers given in the message). "
        "Reply with ONLY that exact JSON object and absolutely nothing else — no "
        "explanation, no markdown, no code fences, just the raw JSON."
    )
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        full_prompt = system_prompt + "\n\n"
        for msg in history[-6:]:
            full_prompt += f"{msg['role']}: {msg['content']}\n"
            
        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {"temperature": 0.0}
        }
        
        import requests
        res = requests.post(url, json=payload).json()
        
        if "candidates" in res:
            reply_text = res["candidates"][0]["content"]["parts"][0]["text"].strip()
        else:
            reply_text = json.dumps({"answer": f"Gemini API Error: {json.dumps(res)}"})
    except Exception as e:
        reply_text = json.dumps({"answer": f"API Error: {str(e)}"})
        
    history.append({"role": "assistant", "content": reply_text})

    # Make sure we actually reply with valid JSON containing "log_url"
    try:
        parsed = json.loads(reply_text)
    except json.JSONDecodeError:
        # Model added extra text — try to pull out just the {...} part.
        start, end = reply_text.find("{"), reply_text.rfind("}")
        if start != -1 and end != -1:
            parsed = json.loads(reply_text[start:end + 1])
        else:
            parsed = {"answer": reply_text}
            
    parsed["log_url"] = LOG_URL
    final_reply = json.dumps(parsed)

    log_event({"type": "outgoing", "chat_id": chat_id, "text": final_reply})
    await update.message.reply_text(final_reply)

if __name__ == "__main__":
    if TELEGRAM_BOT_TOKEN == "PASTE_YOUR_BOTFATHER_TOKEN_HERE" or not TELEGRAM_BOT_TOKEN:
        print("WARNING: TELEGRAM_BOT_TOKEN not set!")
    
    # --- RENDER WEB SERVICE HACK ---
    # Render requires a web port to be open for Free Web Services.
    import threading
    import http.server
    import socketserver
    
    def start_dummy_server():
        port = int(os.environ.get("PORT", 10000))
        Handler = http.server.SimpleHTTPRequestHandler
        try:
            with socketserver.TCPServer(("", port), Handler) as httpd:
                httpd.serve_forever()
        except:
            pass
            
    threading.Thread(target=start_dummy_server, daemon=True).start()
    # -------------------------------
    
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot is running... (Ctrl+C to stop)")
    app.run_polling()
