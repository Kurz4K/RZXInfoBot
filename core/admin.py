import os
import json
from config import BASE_DIR, ADMINS
from core.utils import readable_size
from telegram import InputFile

SEND_TARGET_FILE = "admin_targets.json"

LABEL_TARGETS = ["raw", "good", "average", "trash", "incorrect", "banned"]

def is_admin(user_id: int):
    return user_id in ADMINS

def set_group_target(label, group_id):
    if label not in LABEL_TARGETS:
        return False
    data = load_group_targets()
    data[label] = group_id
    json.dump(data, open(SEND_TARGET_FILE, "w"), indent=2)
    return True

def get_group_target(label):
    data = load_group_targets()
    return data.get(label)

def load_group_targets():
    if os.path.exists(SEND_TARGET_FILE):
        return json.load(open(SEND_TARGET_FILE))
    return {}

def count_lines(filepath):
    with open(filepath, encoding="utf-8") as f:
        return sum(1 for _ in f)

async def send_file_to_group(context, file_path, type_str, from_user):
    label = type_str.lower()
    group_id = get_group_target(label)
    if not group_id:
        return False

    filename = os.path.basename(file_path)
    size = readable_size(file_path)
    lines = count_lines(file_path)

    caption = (
        f"📎 {filename}\n"
        f"📤 File sent!\n\n"
        f"Type: {type_str}\n"
        f"Lines: {lines}\n"
        f"Size: {size}\n"
        f"From User: @{from_user or 'Unknown'}"
    )

    try:
        with open(file_path, "rb") as f:
            await context.bot.send_document(chat_id=group_id, document=InputFile(f, filename), caption=caption)
        return True
    except Exception as e:
        print("Error sending file:", e)
        return False
 
