import os
import json
from config import BASE_DIR
from core.parser import parse_line, clean_format_block
from core.utils import now_str

LABELS = ["Good", "Average", "Trash", "Incorrect", "Banned"]

def get_resume_path(user_id, session_id, level):
    resume_dir = os.path.join(BASE_DIR, str(user_id), "generated", session_id)
    os.makedirs(resume_dir, exist_ok=True)
    return os.path.join(resume_dir, f"resume_{level}.json")

def load_resume(user_id, session_id, level):
    path = get_resume_path(user_id, session_id, level)
    if os.path.exists(path):
        return json.load(open(path))
    return {"line": 0, "checked": []}

def save_resume(user_id, session_id, level, data):
    path = get_resume_path(user_id, session_id, level)
    json.dump(data, open(path, "w"), indent=2)

def get_labels_path(folder):
    return os.path.join(folder, "labeled_accounts.json")

def load_labels(folder):
    path = get_labels_path(folder)
    if os.path.exists(path):
        return json.load(open(path))
    return {}

def save_labels(folder, data):
    json.dump(data, open(get_labels_path(folder), "w"), indent=2)

def save_label(user_id, session_id, level, acc, label):
    folder = os.path.join(BASE_DIR, str(user_id), "generated", session_id)
    labels_path = get_labels_path(folder)
    labels = load_labels(folder)

    uid = acc["uid"]
    old_label = labels.get(uid)

    def block(a): return clean_format_block(a) + "\n\n"

    # Remove from old label file
    if old_label and old_label != label:
        old_path = os.path.join(folder, f"{old_label}.txt")
        if os.path.exists(old_path):
            content = open(old_path, encoding="utf-8").read()
            content = content.replace(block(acc), "")
            open(old_path, "w", encoding="utf-8").write(content)

    # Save to new label
    labels[uid] = label
    save_labels(folder, labels)

    new_path = os.path.join(folder, f"{label}.txt")
    with open(new_path, "a", encoding="utf-8") as f:
        f.write(block(acc))

def format_account_message(acc, line_idx, total_lines, label=None, checked=False):
    sorted_text = f"🏷️ Sorted: {label if label else 'Not Yet Sorted'}"
    checked_text = f"✅ Checked: {'Yes' if checked else 'No'}"
    return (
        f"📄 {line_idx + 1} / {total_lines}\n\n"
        f"{clean_format_block(acc)}\n\n"
        f"{sorted_text}\n{checked_text}"
    )
 
