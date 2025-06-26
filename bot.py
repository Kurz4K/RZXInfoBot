import os
import logging
import shutil
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, Document, InputFile
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from config import BOT_TOKEN, ADMINS
from core.storage import (
    get_total_upload_size, save_upload, is_txt_file,
    get_uploaded_dir, get_user_dir
)
from core.admin import (
    is_admin, set_group_target, get_group_target, send_file_to_group
)

# ─────────────── Logging ───────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────── /start ───────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("MLBB", callback_data="game_mlbb")],
        [InlineKeyboardButton("CODM (coming soon)", callback_data="game_codm_disabled")]
    ]
    await update.message.reply_text(
        "👋 Hello, Welcome to RZX's Check helper bot.\nPlease select a game for me to help you check.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ─────────────── MLBB Menu ───────────────
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

# ─────────────── Upload .txt File ───────────────
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    doc: Document = update.message.document

    # Validate type
    if not is_txt_file(doc.file_name):
        await update.message.reply_text("❌ Invalid File. Only .txt files are allowed.")
        return

    # Enforce 30MB storage limit
    current_mb = get_total_upload_size(user.id)
    if current_mb + (doc.file_size / (1024 * 1024)) > 30:
        await update.message.reply_text(
            "⚠️ Upload Limit Reached\n"
            "You’ve used your 30MB file storage limit.\n"
            "To upload new files, delete your existing uploads using the /deletedata command."
        )
        return

    await update.message.reply_text("📥 Processing, please wait...")

    # Save to /uploaded
    file = await doc.get_file()
    content = await file.download_as_bytearray()
    save_upload(user.id, doc.file_name, content)

    await update.message.reply_text("✅ File uploaded successfully.\nWhat do you want to do next?")

# ─────────────── /broadcast ───────────────
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("❌ Not authorized.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    message = "📢 RZX Broadcast\n\n" + " ".join(context.args)
    users = get_all_user_ids()
    for uid in users:
        try:
            await context.bot.send_message(uid, message)
        except:
            continue
    await update.message.reply_text("✅ Broadcast sent.")

# Helper: get user list (basic version — replace with real DB later)
def get_all_user_ids():
    base_path = "user_data"
    if not os.path.exists(base_path):
        return []
    return [int(uid) for uid in os.listdir(base_path) if uid.isdigit()]

# ─────────────── /deletedata ───────────────
async def deletedata(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_folder = get_user_dir(user_id)
    if os.path.exists(user_folder):
        shutil.rmtree(user_folder)
        os.makedirs(user_folder)
    await update.message.reply_text("🧹 All your uploaded files have been deleted.\nYou can now upload new `.txt` files.")

# ─────────────── /sendhereX ───────────────
async def set_sendhere(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("❌ Not authorized.")
        return

    command = update.message.text.strip().lower()
    label_map = {
        "/sendhereraw": "raw",
        "/sendheregood": "good",
        "/sendhereaverage": "average",
        "/sendheretrash": "trash",
        "/sendhereincorrect": "incorrect",
        "/sendherebanned": "banned"
    }

    label = label_map.get(command)
    if not label:
        await update.message.reply_text("❌ Invalid command.")
        return

    if set_group_target(label, update.message.chat_id):
        await update.message.reply_text(f"📡 Bot is now active in this group.\nReady to upload: **{label.capitalize()}** files.")
    else:
        await update.message.reply_text("❌ Failed to bind group.")

# ─────────────── Main ───────────────
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("deletedata", deletedata))
    app.add_handler(CommandHandler(
        ["sendhereraw", "sendheregood", "sendhereaverage",
         "sendheretrash", "sendhereincorrect", "sendherebanned"],
        set_sendhere
    ))

    app.add_handler(CallbackQueryHandler(game_choice, pattern="^game_.*|^mlbb_.*"))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

    app.run_polling()

if __name__ == "__main__":
    main()
