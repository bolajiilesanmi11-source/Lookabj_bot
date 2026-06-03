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

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")
API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
headers = {"Authorization": f"Bearer {HF_TOKEN}"}

# Create a dummy FastAPI app for Render's health checks
app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "Bot is running perfectly!"}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to Looka AI Logo Bot!\n\n"
        "Just type a description of the logo you want, and I'll generate it.\n"
        "Example: 'A minimalist vector logo of a coffee shop, modern, blue and gold'"
    )

async def generate_logo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_prompt = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_photo")
    status_message = await update.message.reply_text("🎨 Creating your logo... Please wait about 15 seconds.")

    enhanced_prompt = f"Professional logo, {user_prompt}, vector graphics, minimalist, flat design, white background, high resolution"

    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, 
            lambda: requests.post(API_URL, headers=headers, json={"inputs": enhanced_prompt}, timeout=30)
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
            await status_message.edit_text("❌ The AI server is currently busy. Please try again in a few moments.")
            logger.error(f"HF API Error: {response.text}")
            
    except Exception as e:
        await status_message.edit_text("❌ Something went wrong while generating your logo.")
        logger.error(f"Error: {e}")

async def run_bot():
    """Starts the Telegram Bot loop."""
    if not TELEGRAM_TOKEN or not HF_TOKEN:
        logger.critical("Missing Environment Variables!")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_logo))
    
    # Initialize and start polling
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    logger.info("Telegram Bot Polling started.")

@app.on_event("startup")
async def startup_event():
    # Run the Telegram bot asynchronously alongside the web server
    asyncio.create_task(run_bot())

if __name__ == '__main__':
    # Get port from Render environment, default to 8000 locally
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("bot:app", host="0.0.0.0", port=port)
