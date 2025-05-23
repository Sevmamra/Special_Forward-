import os

class Config:
    # Get bot token from environment variables
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    
    # Get authorized user ID (make sure to set this in .env)
    try:
        AUTHORIZED_USER_ID = int(os.getenv("AUTHORIZED_USER_ID", "0"))
    except (ValueError, TypeError):
        AUTHORIZED_USER_ID = 0  # Default invalid ID
    
    # Admin group ID (optional)
    try:
        ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID", "0"))
    except (ValueError, TypeError):
        ADMIN_GROUP_ID = 0
