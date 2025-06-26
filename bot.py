import os
import logging
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, Document
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from config import BOT_TOKEN, ADMINS
from core.storage import (
    get_total_upload_size, save_upload, is_txt_file,
    get_uploaded_dir
)

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Track user state (simple in-memory for now)
user_states = {}

# ─────────────────────────────────────────────────────────────

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("MLBB", callback_data="game_mlbb")],
        [InlineKeyboardButton("CODM (coming soon)", callback_data="game_codm_disabled")]
    ]
    await update.message.reply_text(
        "👋 Hello, Welcome to RZX's Check helper bot.\nPlease select a game for me to help you check.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Game button handler
async def game_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "game_mlbb":
        keyboard = [
            [InlineKeyboardButton("▶️ Resume", callback_data="mlbb_resume")],
            [InlineKeyboardButton("📤 Send File", callback_data="mlbb_sendfile")],
            [InlineKeyboardButton("📂 Files", callback_data="mlbb_files")]
        ]
        await query.edit_message_text("🕹️ MLBB Menu:\nWhat would you like to do?",
                                      reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await query.edit_message_text("🚧 CODM is not available yet.")

# Document (.txt) upload
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    doc: Document = update.message.document

    # Only allow .txt
    if not is_txt_file(doc.file_name):
        await update.message.reply_text("❌ Invalid File. Only .txt files are allowed.")
        return

    # Check storage limit
    current_mb = get_total_upload_size(user.id)
    if current_mb + (doc.file_size / (1024 * 1024)) > 30:
        await update.message.reply_text(
            "⚠️ Upload Limit Reached\n"
            "You’ve used your 30MB file storage limit.\n"
            "To upload new files, delete your existing uploads using the /deletedata command."
        )
        return

    await update.message.reply_text("📥 Processing, please wait...")

    # Save file to /uploaded/
    file = await doc.get_file()
    content = await file.download_as_bytearray()
    saved_path = save_upload(user.id, doc.file_name, content)

    await update.message.reply_text("✅ File uploaded successfully.\nWhat do you want to do next?")
    # You'll hook this into a decision menu later (Check, Clean Format, Separate Levels)

# ─────────────────────────────────────────────────────────────

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(game_choice, pattern="^game_.*|^mlbb_.*"))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

    app.run_polling()

if __name__ == "__main__":
    main()
