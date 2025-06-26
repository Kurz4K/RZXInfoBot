import os
import json
import time
from config import BASE_DIR, MAX_FILE_SIZE_MB
from core.utils import now_str

def get_user_dir(user_id):
    path = os.path.join(BASE_DIR, str(user_id))
    os.makedirs(path, exist_ok=True)
    return path

def get_uploaded_dir(user_id):
    path = os.path.join(get_user_dir(user_id), "uploaded")
    os.makedirs(path, exist_ok=True)
    return path

def get_generated_dir(user_id):
    path = os.path.join(get_user_dir(user_id), "generated")
    os.makedirs(path, exist_ok=True)
    return path

def get_total_upload_size(user_id):
    path = get_uploaded_dir(user_id)
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            total += os.path.getsize(os.path.join(root, f))
    return total / (1024 * 1024)  # MB

def is_txt_file(file_name):
    return file_name.lower().endswith(".txt")

def save_upload(user_id, file_name, content: bytes):
    user_path = get_uploaded_dir(user_id)
    save_path = os.path.join(user_path, file_name)
    with open(save_path, "wb") as f:
        f.write(content)
    # Save upload time
    meta_path = os.path.join(user_path, f"{file_name}.meta.json")
    json.dump({"uploaded_at": now_str(), "viewed": False}, open(meta_path, "w"), indent=2)
    return save_path
