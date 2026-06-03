import os
import io
import logging
import asyncio
import requests
from PIL import Image
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Enable logging to see errors in Render console
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Fetch environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

# Hugging Face API setup (Using Stable Diffusion XL for logos)
API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
headers = {"Authorization": f"Bearer {HF_TOKEN}"}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message when /start is issued."""
    await update.message.reply_text(
        "👋 Welcome to Looka AI Logo Bot!\n\n"
        "Just type a description of the logo you want, and I'll generate it for you.\n"
        "Example: 'A minimalist vector logo of a coffee shop, modern, blue and gold color'"
    )

async def generate_logo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the text prompt and generates the logo."""
    user_prompt = update.message.text
    
    # 1. Send "typing..." action so user knows the bot is working
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_photo")
    status_message = await update.message.reply_text("🎨 Creating your logo... Please wait about 15 seconds.")

    # 2. Optimize prompt specifically for clean logos
    enhanced_prompt = f"Professional logo, {user_prompt}, vector graphics, minimalist, flat design, white background, high resolution"

    # 3. Call AI API asynchronously so the bot doesn't freeze
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, 
            lambda: requests.post(API_URL, headers=headers, json={"inputs": enhanced_prompt}, timeout=30)
        )
        
        if response.status_value == 200:
            # Convert bytes to an image
            image_bytes = response.content
            image = Image.open(io.BytesIO(image_bytes))
            
            # Save to an in-memory file to send to Telegram
            bio = io.BytesIO()
            bio.name = 'logo.png'
            image.save(bio, 'PNG')
            bio.seek(0)

            # Delete the status message and send the photo
            await status_message.delete()
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=bio, caption="✨ Here is your Looka AI logo!")
        else:
            await status_message.edit_text("❌ The AI server is currently busy. Please try again in a few moments.")
            logger.error(f"HF API Error: {response.text}")
            
    except Exception as e:
        await status_message.edit_text("❌ Something went wrong while generating your logo.")
        logger.error(f"Error: {e}")

def main():
    """Start the bot using Long Polling."""
    if not TELEGRAM_TOKEN or not HF_TOKEN:
        logger.critical("Missing Environment Variables! Please check TELEGRAM_TOKEN and HF_TOKEN.")
        return

    # Build the application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, generate_logo))

    # Run the bot
    logger.info("Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
