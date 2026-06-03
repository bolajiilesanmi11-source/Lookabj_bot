import os
import io
import logging
import asyncio
import requests
from PIL import Image
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from fastapi import FastAPI
import uvicorn

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

# SWITCHED to a specialized model perfectly tuned for high-quality minimalist logos
API_URL = "https://api-inference.huggingface.co/models/artificialguybr/LogoRedmond-LogoV2-LogoLora"
headers = {"Authorization": f"Bearer {HF_TOKEN}"}

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "Looka AI Bot is running!"}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to Looka AI Logo Bot!\n\n"
        "Just type a description of the logo you want, and I'll generate it.\n"
        "Example: 'A futuristic eagle icon for a tech security startup, vector, minimalist, sleek design'"
    )

async def generate_logo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_prompt = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_photo")
    status_message = await update.message.reply_text("🎨 Creating your logo... Please wait up to 20 seconds.")

    # Tailored prompt parameters optimized specifically for LogoRedmond
    enhanced_prompt = f"LogoRedmond, clean vector logo of {user_prompt}, minimalist style, flat design, sharp details, white background"
    payload = {
        "inputs": enhanced_prompt,
        "options": {"wait_for_model": True} # <--- Crucial! Forces the bot to wait if the AI model is waking up
    }

    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, 
            lambda: requests.post(API_URL, headers=headers, json=payload, timeout=45)
        )
        
        if response.status_code == 200:
            image_bytes = response.content
            image = Image.open(io.BytesIO(image_bytes))
            
            bio = io.BytesIO()
            bio.name = 'logo.png'
            image.save(bio, 'PNG')
            bio.seek(0)

            await status_message.delete()
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=bio, caption="✨ Here is your Looka AI logo!")
        else:
            # If Hugging Face throws an explicit error, let's notify the user accurately
            await status_message.edit_text("❌ The AI generation engine is busy or experiencing high traffic. Please try again in a few moments.")
            logger.error(f"HF API Error: Code {response.status_code} - {response.text}")
            
    except Exception as e:
        await status_message.edit_text("❌ Something went wrong while processing the image formatting.")
        logger.error(f"Internal Bot Error: {e}")

async def run_bot():
    if not TELEGRAM_TOKEN or not HF_TOKEN:
        logger.critical("Missing Environment Variables!")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_logo))
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    logger.info("Telegram Bot Polling started.")

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(run_bot())

if __name__ == '__main__':
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("bot:app", host="0.0.0.0", port=port)
