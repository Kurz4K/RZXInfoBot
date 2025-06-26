import os

# Telegram Bot token
BOT_TOKEN = os.getenv("BOT_TOKEN")

# OpenAI API key (for GPT fallback)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Comma-separated list of Telegram user IDs who are admins
ADMINS = [int(i) for i in os.getenv("ADMINS", "").split(",") if i]

# Maximum total upload size per user (MB)
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 30))

# How many “Separate Levels” a user can run per day
DAILY_SEPARATION_LIMIT = int(os.getenv("DAILY_SEPARATION_LIMIT", 1))
