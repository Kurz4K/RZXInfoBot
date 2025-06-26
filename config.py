import os

# Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN")

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Admins
ADMINS = [int(i) for i in os.getenv("ADMINS", "").split(",") if i]

# File limits
MAX_FILE_SIZE_MB       = int(os.getenv("MAX_FILE_SIZE_MB", 30))
DAILY_SEPARATION_LIMIT = int(os.getenv("DAILY_SEPARATION_LIMIT", 1))

# Base storage directory for all user files
BASE_DIR = os.getenv("BASE_DIR", "user_data")
