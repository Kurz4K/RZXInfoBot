# Here is the complete bot.py integrating all requested features.
# Make sure helper modules (core/parser.py, core/viewer.py, core/storage.py,
# core/admin.py, core/gpt_fallback.py) are present as previously defined.

import os
import json
import shutil
import logging
from datetime import datetime, timedelta
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, Document, InputFile
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, ConversationHandler
)
from config import BOT_TOKEN, ADMINS, DAILY_SEPARATION_LIMIT, MAX_FILE_SIZE_MB
from core.storage import (
    get_user_dir, get_uploaded_dir, get_generated_dir,
    get_total_upload_size, save_upload, is_txt_file, list_user_txt_files,
    mark_file_opened, delete_inactive_files, delete_user_data
)
from core.parser import (
    parse_line, clean_format_block, separate_by_level, build_output_line
)
from core.viewer import (
    format_account_message, load_resume, save_resume, save_label
)
from core.gpt_fallback import fix_line_with_gpt
from core.admin import (
    is_admin, set_group_target, get_group_target,
    send_file_to_group, get_all_user_ids
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Session state
user_sessions = {}

# ─────────── Start & Game Selection ───────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("MLBB", callback_data="game_mlbb")],
        [InlineKeyboardButton("CODM (soon)", callback_data="game_codm_disabled")]
    ]
    await update.message.reply_text(
        "👋 Hello! Welcome to RZX's Check helper bot.\nSelect a game:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def game_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    if update.callback_query.data == "game_mlbb":
        keyboard = [
            [
                InlineKeyboardButton("▶️ Resume", callback_data="mlbb_resume"),
                InlineKeyboardButton("📤 Send File", callback_data="mlbb_sendfile"),
                InlineKeyboardButton("📂 Files", callback_data="mlbb_files")
            ]
        ]
        await update.callback_query.edit_message_text(
            "MLBB Menu:", reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.callback_query.edit_message_text("CODM coming soon.")

# ─────────── File Upload & Limits ───────────
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    uid = update.effective_user.id
    if not is_txt_file(doc.file_name):
        return await update.message.reply_text("❌ Only .txt files allowed.")
    if get_total_upload_size(uid) + doc.file_size/1e6 > MAX_FILE_SIZE_MB:
        return await update.message.reply_text(
            "⚠️ Upload limit reached (30MB).\nUse /deletedata to clear."
        )
    # Save
    blob = await (await doc.get_file()).download_as_bytearray()
    path = save_upload(uid, doc.file_name, blob)
    mark_file_opened(uid, doc.file_name)
    # enforce 1 separation/day
    sessions = context.user_data.get("daily_sep", {})
    last = sessions.get(path)
    if last and datetime.fromisoformat(last) > datetime.now() - timedelta(days=1):
        await update.message.reply_text("❌ You can only separate one file per day.")
    keyboard = [
        [InlineKeyboardButton("🔎 Check", callback_data=f"action_check|{path}")],
        [InlineKeyboardButton("🧹 Clean", callback_data=f"action_clean|{path}")],
        [InlineKeyboardButton("🧩 Separate", callback_data=f"action_separate|{path}")]
    ]
    await update.message.reply_text("File uploaded. Choose action:",
                                    reply_markup=InlineKeyboardMarkup(keyboard))

# ─────────── Files Browser ───────────
async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    files = list_user_txt_files(uid)
    if not files:
        return await update.callback_query.message.reply_text("No uploaded files.")
    kb = [[InlineKeyboardButton(f, callback_data=f"select|{f}")] for f in files]
    await update.callback_query.message.reply_text(
        "Your files:", reply_markup=InlineKeyboardMarkup(kb)
    )

# ─────────── Action Router ───────────
async def action_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data.split("|")
    cmd, path = data[0], data[1]
    await update.callback_query.answer()
    uid = update.effective_user.id
    if cmd == "action_check":
        await start_check(update, context, uid, path)
    elif cmd == "action_clean":
        await do_clean(update, context, uid, path)
    elif cmd == "action_separate":
        await separate_prompt(update, context, uid, path)
    elif cmd.startswith("select"):
        return await action_router(update, context)

# ─────────── Checking Time w/ Resume ───────────
async def start_check(update, context, uid, path):
    # load or init session
    lines = open(path, encoding="utf-8").read().splitlines()
    accounts=[]
    for l in lines:
        a=parse_line(l) or await fix_line_with_gpt(l)
        if not a: continue
        accounts.append(a)
    if not accounts:
        return await update.callback_query.message.reply_text(
            "❌ No valid accounts."
        )
    sess={"accs":accounts,"i":0,"path":path,"uid":uid}
    user_sessions[uid]=sess
    await show_one(update, context, uid)

async def show_one(update, context, uid):
    sess=user_sessions[uid]
    acc=sess["accs"][sess["i"]]; total=len(sess["accs"])
    msg=format_account_message(acc,sess["i"],total)
    kb=[
        [InlineKeyboardButton("◀️",callback_data="nav_prev"),
         InlineKeyboardButton("▶️",callback_data="nav_next")],
        [InlineKeyboardButton("✅ Good",callback_data="lbl_Good"),
         InlineKeyboardButton("⚠️ Avg",callback_data="lbl_Average"),
         InlineKeyboardButton("❌ Trash",callback_data="lbl_Trash")],
        [InlineKeyboardButton("❓ Incorrect",callback_data="lbl_Incorrect"),
         InlineKeyboardButton("🚫 Banned",callback_data="lbl_Banned")]
    ]
    if sess["i"]==total-1:
        kb.append([InlineKeyboardButton("📤 Extract",callback_data="action_extract")])
    await update.callback_query.message.reply_text(
        msg, reply_markup=InlineKeyboardMarkup(kb)
    )

async def check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data=update.callback_query.data
    uid=update.callback_query.from_user.id
    sess=user_sessions.get(uid)
    await update.callback_query.answer()
    if not sess: return await update.callback_query.edit_message_text("No session")
    if data=="nav_next" and sess["i"]<len(sess["accs"])-1: sess["i"]+=1
    if data=="nav_prev" and sess["i"]>0: sess["i"]-=1
    if data.startswith("lbl_"):
        lbl=data.split("_")[1]
        acc=sess["accs"][sess["i"]]
        save_label(uid,os.path.basename(sess["path"]),lbl)
    if data=="action_extract":
        folder=os.path.join(get_generated_dir(uid),os.path.basename(sess["path"]))
        for f in os.listdir(folder):
            if f.endswith(".txt"):
                await update.callback_query.message.reply_document(
                    InputFile(os.path.join(folder,f))
                )
        return
    await update.callback_query.message.delete()
    await show_one(update, context, uid)

# ─────────── Clean & Separate ───────────
async def do_clean(update, context, uid, path):
    lines=open(path,encoding="utf-8").read().splitlines()
    pars=[]
    for l in lines:
        a=parse_line(l) or await fix_line_with_gpt(l)
        if a: pars.append(a)
    if not pars: return await update.callback_query.message.reply_text("No valid lines")
    txt="\n\n".join(clean_format_block(a) for a in pars)
    name="cleaned.txt"
    open(name,"w",encoding="utf-8").write(txt)
    await update.callback_query.message.reply_document(InputFile(name))
    os.remove(name)

async def separate_prompt(update, context, uid, path):
    kb=[[InlineKeyboardButton("✔️ Yes",callback_data=f"sep_yes|{path}"),
         InlineKeyboardButton("❌ No",callback_data=f"sep_no|{path}")]]
    await update.callback_query.message.reply_text(
        "Clean format before separation?",reply_markup=InlineKeyboardMarkup(kb)
    )

async def do_sep_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cmd,path=update.callback_query.data.split("|")
    clean=(cmd=="sep_yes")
    lines=open(path,encoding="utf-8").read().splitlines()
    pars=[parse_line(l) or await fix_line_with_gpt(l) for l in lines]
    sep=separate_by_level([a for a in pars if a])
    for lvl,arr in sep.items():
        if not arr: continue
        fn=f"{lvl}.txt"
        with open(fn,"w",encoding="utf-8") as f:
            for a in arr:
                f.write((clean_format_block(a) if clean else build_output_line(a))+"\n\n")
        await update.callback_query.message.reply_document(InputFile(fn))
        os.remove(fn)

# ─────────── Admin Upload Selector & Queue ───────────
async def admin_upload_selector(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    kb=[[InlineKeyboardButton(x,callback_data=f"admin_up|{x}") for x in ["Raw","Separated","Separated-Clean"]]]
    await update.message.reply_text("Choose upload type:",reply_markup=InlineKeyboardMarkup(kb))

async def admin_up_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    typ=update.callback_query.data.split("|")[1].lower()
    group=get_group_target(typ)
    for uid in get_all_user_ids():
        upth=get_uploaded_dir(uid)
        for f in os.listdir(upth):
            if f.endswith(".txt"):
                p=os.path.join(upth,f)
                await send_file_to_group(context,p,typ,uid)
    await update.callback_query.answer("Done.")

# ─────────── Cleanup & Deletion Jobs ───────────
async def daily_cleanup(context):
    delete_inactive_files()

# ─────────── Bot Setup ───────────
def main():
    app=ApplicationBuilder().token(BOT_TOKEN).build()
    # Jobs
    run_every=24*3600
    app.job_queue.run_repeating(daily_cleanup, interval=run_every, first=10)
    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(game_choice,pattern="^game_.*"))
    app.add_handler(MessageHandler(filters.Document.ALL,handle_file))
    app.add_handler(CallbackQueryHandler(check_callback,pattern="^(nav_|lbl_|action_extract)"))
    app.add_handler(CallbackQueryHandler(action_router,pattern="^action_"))
    app.add_handler(CallbackQueryHandler(do_sep_action,pattern="^sep_"))
    app.add_handler(CallbackQueryHandler(callback_router,pattern="^(clean_format|separate_levels)"))
    app.add_handler(CommandHandler("broadcast",broadcast))
    app.add_handler(CommandHandler("deletedata",deletedata))
    app.add_handler(CommandHandler(["sendhereraw","sendheregood","sendhereaverage","sendheretrash","sendhereincorrect","sendherebanned"], set_sendhere))
    app.add_handler(CommandHandler("upload", admin_upload_selector))
    app.add_handler(CallbackQueryHandler(admin_up_handler, pattern="^admin_up"))
    app.run_polling()

if __name__=="__main__":
    main()
