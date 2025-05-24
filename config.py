import os

class Config:
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    try:
        AUTHORIZED_USER_ID = int(os.getenv("AUTHORIZED_USER_ID", "0"))
    except (ValueError, TypeError):
        AUTHORIZED_USER_ID = 0
