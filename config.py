import os

BOT_TOKEN = os.getenv("7603235551:AAGg1z0JT1RaD2B820ga0cAynicq_xFRrfk")
OPENAI_API_KEY = os.getenv("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")
ADMINS = [int(i) for i in os.getenv("ADMINS", "").split(",") if i]

BASE_DIR = "user_data"
MAX_FILE_SIZE_MB = 30
DAILY_SEPARATION_LIMIT = 1
GPT_MODEL = "gpt-4o"
