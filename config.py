import os

class Config:
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    AUTHORIZED_USER_ID = int(os.getenv("AUTHORIZED_USER_ID"))  # Your Telegram user ID
    ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID", -1001234567890))  # Your admin group ID
