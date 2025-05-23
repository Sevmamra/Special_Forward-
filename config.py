import os

class Config:
    TOKEN = os.getenv("7763888885:AAGGtCSMRc0tvvGCFJwRMmYJBR819JfiOmQ")
    AUTHORIZED_USER_ID = int(os.getenv("6567162029"))  # Your Telegram user ID
    ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID", -1002501498159))  # Your admin group ID
