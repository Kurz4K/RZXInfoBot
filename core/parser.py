import re
from core.utils import now_str

LEVEL_RANGES = {
    "0-30": range(0, 31),
    "31-60": range(31, 61),
    "61-99": range(61, 100),
    "100+": range(100, 9999)
}

# Parse line into structured account dict
def parse_line(line: str):
    try:
        parts = line.strip().split(" | ")
        creds = parts[0].split(":")
        uid_full = parts[1].split(" = ")[1]
        uid = uid_full.split(" ")[0]
        server_id = uid_full.split("(")[1].strip(")")
        return {
            "email": creds[0],
            "password": creds[1],
            "uid": uid,
            "server_id": server_id,
            "name": parts[2].split(" = ")[1],
            "rank": parts[3].split(" = ")[1],
            "level": int(parts[4].split(" = ")[1]),
            "country": parts[5].split(" = ")[1],
            "banned": parts[6].split(" = ")[1].lower() == "true",
            "credits": parts[7].split(" = ")[1] if len(parts) > 7 else "Config by RZX"
        }
    except:
        return None

# Clean, formatted preview for each account (as in your viewer)
def clean_format_block(acc):
    return (
        f"📧 Email: {acc['email']}\n"
        f"🔑 Password: {acc['password']}\n"
        f"👤 Username: {acc['name']}\n"
        f"🆔 ID: {acc['uid']} ({acc['server_id']})\n"
        f"🎮 Level: {acc['level']}\n"
        f"🏆 Max Rank: {acc['rank']}\n"
        f"🚫 Status: {'Banned' if acc['banned'] else 'Not Banned'}\n"
        f"🌍 Country: {acc['country']}\n"
        f"📝 Credits: {acc['credits']}"
    )

# For writing back to file
def build_output_line(acc):
    return (
        f"{acc['email']}:{acc['password']} | uid = {acc['uid']} ({acc['server_id']})"
        f" | name = {acc['name']} | max_rank = {acc['rank']} | level = {acc['level']}"
        f" | country = {acc['country']} | is_banned = {acc['banned']} | credits = {acc['credits']}"
    )

# Separate a list of accounts by level range
def separate_by_level(accounts):
    result = {k: [] for k in LEVEL_RANGES}
    for acc in accounts:
        for level_key, level_range in LEVEL_RANGES.items():
            if acc["level"] in level_range:
                result[level_key].append(acc)
                break
    return result
