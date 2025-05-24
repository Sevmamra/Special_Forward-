import os

class Config:
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    try:
        AUTHORIZED_USER_ID = int(os.getenv("AUTHORIZED_USER_ID", "0"))
    except (ValueError, TypeError):
        AUTHORIZED_USER_ID = 0
    
    # Parse group IDs from environment variable
    GROUP_IDS = []
    group_ids_str = os.getenv("GROUP_IDS", "")
    if group_ids_str:
        try:
            GROUP_IDS = [int(gid.strip()) for gid in group_ids_str.split(",")]
        except ValueError:
            GROUP_IDS = []
