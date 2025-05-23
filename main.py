import os
import logging
from typing import Dict, List, Set
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from config import Config

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot states and data storage
class BotData:
    def __init__(self):
        self.received_items = {
            'videos': 0,
            'files': 0,
            'texts': 0,
            'others': 0
        }
        self.collecting = False
        self.selected_groups: Set[int] = set()
        self.selected_topics: Dict[int, Set[int]] = {}  # {group_id: set(topic_ids)}
        self.messages_to_forward: List[Dict] = []
        self.groups_info: Dict[int, Dict] = {}  # {group_id: {'name': str, 'topics': Dict[int, str]}}

bot_data = BotData()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != Config.AUTHORIZED_USER_ID:
        await update.message.reply_text("❌ Unauthorized access!")
        return

    name = update.effective_user.full_name
    welcome_msg = (
        f"ʜᴇʟʟᴏ, {name} ꜱɪʀ!\n\n"
        "ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴏᴜʀ ꜰᴏʀᴡᴀʀᴅɪɴɢ ʙᴏᴛ ꜱᴇʀᴠɪᴄᴇ.\n\n"
        "ꜱɪᴍᴘʟʏ ꜱᴇɴᴅ ᴀɴʏ ᴍᴇꜱꜱᴀɢᴇ, ᴘʜᴏᴛᴏ, ᴠɪᴅᴇᴏ, ᴅᴏᴄᴜᴍᴇɴᴛ, ᴏʀ ꜰɪʟᴇ ʜᴇʀᴇ — ᴀɴᴅ ᴏᴜʀ ʙᴏᴛ ᴡɪʟʟ ɪɴꜱᴛᴀɴᴛʟʏ ꜰᴏʀᴡᴀʀᴅ ɪᴛ ᴛᴏ ʏᴏᴜʀ ᴅᴇꜱɪɢɴᴀᴛᴇᴅ ɢʀᴏᴜᴘ, ᴇɴꜱᴜʀɪɴɢ ꜱᴇᴀᴍʟᴇꜱꜱ ᴀɴᴅ ᴇꜰꜰɪᴄɪᴇɴᴛ ᴅᴇʟɪᴠᴇʀʏ ᴡɪᴛʜᴏᴜᴛ ᴀɴʏ ᴅᴇʟᴀʏ.\n\n"
        "ᴍᴀᴅᴇ ᴡɪᴛʜ ❤️ ʙʏ 𝐂𝐀 𝐈𝐧𝐭𝐞𝐫 𝐗"
    )

    keyboard = [[InlineKeyboardButton("Start process", callback_data="start_process")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_msg, reply_markup=reply_markup)

async def start_process(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != Config.AUTHORIZED_USER_ID:
        await query.message.reply_text("❌ Unauthorized access!")
        return

    bot_data.collecting = True
    bot_data.received_items = {'videos': 0, 'files': 0, 'texts': 0, 'others': 0}
    bot_data.messages_to_forward = []
    
    await query.edit_message_text("Send me videos, files, text, etc. When done, send /done")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not bot_data.collecting or update.effective_user.id != Config.AUTHORIZED_USER_ID:
        return

    message = update.message
    
    # Count received items
    if message.video:
        bot_data.received_items['videos'] += 1
    elif message.document:
        bot_data.received_items['files'] += 1
    elif message.text and not message.text.startswith('/'):
        bot_data.received_items['texts'] += 1
    else:
        bot_data.received_items['others'] += 1
    
    # Store message for forwarding
    bot_data.messages_to_forward.append({
        'type': 'video' if message.video else 
               'document' if message.document else 
               'photo' if message.photo else 
               'text',
        'content': message.video or message.document or 
                  (message.photo[-1] if message.photo else None) or 
                  message.text,
        'caption': message.caption,
        'entities': message.entities or message.caption_entities
    })

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != Config.AUTHORIZED_USER_ID:
        return

    bot_data.collecting = False
    
    report = (
        f"Received videos - {bot_data.received_items['videos']}\n"
        f"Received files - {bot_data.received_items['files']}\n"
        f"Received text msgs - {bot_data.received_items['texts']}\n"
        f"Other - {bot_data.received_items['others']}\n\n"
        f"Total - {sum(bot_data.received_items.values())}"
    )
    
    keyboard = [[InlineKeyboardButton("GROUPS", callback_data="select_groups")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(report, reply_markup=reply_markup)

async def select_groups(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != Config.AUTHORIZED_USER_ID:
        return

    # In a real implementation, you would fetch the groups your bot is in
    # For this example, we'll use some dummy data
    bot_data.groups_info = {
        -1001234567890: {
            'name': "𝐂𝐀 𝐈𝐧𝐭𝐞𝐫 𝐗",
            'topics': {
                123: "Topic 1",
                124: "Topic 2"
            }
        },
        -1009876543210: {
            'name': "Another Group",
            'topics': {
                125: "Main Topic"
            }
        }
    }
    
    keyboard = []
    for group_id, group_info in bot_data.groups_info.items():
        group_name = group_info['name']
        is_selected = group_id in bot_data.selected_groups
        emoji = "✅" if is_selected else "◻️"
        keyboard.append([
            InlineKeyboardButton(
                f"{group_name} {emoji}",
                callback_data=f"toggle_group:{group_id}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("Select all", callback_data="select_all_groups"),
        InlineKeyboardButton("Send", callback_data="confirm_send")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Select groups to forward to:", reply_markup=reply_markup)

async def toggle_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != Config.AUTHORIZED_USER_ID:
        return

    group_id = int(query.data.split(':')[1])
    
    if group_id in bot_data.selected_groups:
        bot_data.selected_groups.remove(group_id)
        if group_id in bot_data.selected_topics:
            del bot_data.selected_topics[group_id]
    else:
        bot_data.selected_groups.add(group_id)
    
    await select_groups(update, context)

async def select_all_groups(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != Config.AUTHORIZED_USER_ID:
        return

    bot_data.selected_groups = set(bot_data.groups_info.keys())
    await select_groups(update, context)

async def confirm_send(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != Config.AUTHORIZED_USER_ID:
        return

    if not bot_data.selected_groups:
        await query.edit_message_text("Please select at least one group!")
        return
    
    # For groups with topics, show topic selection
    groups_with_topics = {
        group_id: group_info 
        for group_id, group_info in bot_data.groups_info.items() 
        if group_id in bot_data.selected_groups and group_info['topics']
    }
    
    if groups_with_topics:
        bot_data.selected_topics = {group_id: set() for group_id in groups_with_topics}
        await show_topic_selection(update, context, list(groups_with_topics.keys())[0])
    else:
        await forward_messages(update, context)

async def show_topic_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, group_id: int) -> None:
    query = update.callback_query
    
    group_info = bot_data.groups_info[group_id]
    keyboard = []
    
    for topic_id, topic_name in group_info['topics'].items():
        is_selected = topic_id in bot_data.selected_topics[group_id]
        emoji = "✅" if is_selected else "◻️"
        keyboard.append([
            InlineKeyboardButton(
                f"{topic_name} {emoji}",
                callback_data=f"toggle_topic:{group_id}:{topic_id}"
            )
        ])
    
    # Navigation buttons
    nav_buttons = []
    current_idx = list(bot_data.selected_groups).index(group_id)
    
    if current_idx > 0:
        prev_group_id = list(bot_data.selected_groups)[current_idx - 1]
        nav_buttons.append(
            InlineKeyboardButton("◀️ Previous", callback_data=f"select_topics:{prev_group_id}")
        )
    
    if current_idx < len(bot_data.selected_groups) - 1:
        next_group_id = list(bot_data.selected_groups)[current_idx + 1]
        nav_buttons.append(
            InlineKeyboardButton("Next ▶️", callback_data=f"select_topics:{next_group_id}")
        )
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([
        InlineKeyboardButton("Select all topics", callback_data=f"select_all_topics:{group_id}"),
        InlineKeyboardButton("Back to groups", callback_data="select_groups")
    ])
    
    keyboard.append([
        InlineKeyboardButton("Send now", callback_data="forward_messages")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        f"Select topics in {group_info['name']}:",
        reply_markup=reply_markup
    )

async def toggle_topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != Config.AUTHORIZED_USER_ID:
        return

    _, group_id, topic_id = query.data.split(':')
    group_id = int(group_id)
    topic_id = int(topic_id)
    
    if topic_id in bot_data.selected_topics[group_id]:
        bot_data.selected_topics[group_id].remove(topic_id)
    else:
        bot_data.selected_topics[group_id].add(topic_id)
    
    await show_topic_selection(update, context, group_id)

async def select_all_topics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != Config.AUTHORIZED_USER_ID:
        return

    group_id = int(query.data.split(':')[1])
    bot_data.selected_topics[group_id] = set(bot_data.groups_info[group_id]['topics'].keys())
    
    await show_topic_selection(update, context, group_id)

async def forward_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query:
        await query.answer()
    
    if update.effective_user.id != Config.AUTHORIZED_USER_ID:
        return

    success_count = 0
    failed_count = 0
    report = "Forwarding report:\n\n"
    
    for group_id in bot_data.selected_groups:
        group_name = bot_data.groups_info[group_id]['name']
        topic_ids = bot_data.selected_topics.get(group_id, {None})
        
        for topic_id in topic_ids:
            topic_name = ""
            if topic_id:
                topic_name = f" (Topic: {bot_data.groups_info[group_id]['topics'][topic_id]})"
            
            report += f"➡️ {group_name}{topic_name}:\n"
            
            for msg in bot_data.messages_to_forward:
                try:
                    if msg['type'] == 'text':
                        await context.bot.send_message(
                            chat_id=group_id,
                            message_thread_id=topic_id,
                            text=msg['content'],
                            entities=msg['entities']
                        )
                    elif msg['type'] == 'photo':
                        await context.bot.send_photo(
                            chat_id=group_id,
                            message_thread_id=topic_id,
                            photo=msg['content'],
                            caption=msg['caption'],
                            caption_entities=msg['entities']
                        )
                    elif msg['type'] == 'video':
                        await context.bot.send_video(
                            chat_id=group_id,
                            message_thread_id=topic_id,
                            video=msg['content'],
                            caption=msg['caption'],
                            caption_entities=msg['entities']
                        )
                    elif msg['type'] == 'document':
                        await context.bot.send_document(
                            chat_id=group_id,
                            message_thread_id=topic_id,
                            document=msg['content'],
                            caption=msg['caption'],
                            caption_entities=msg['entities']
                        )
                    success_count += 1
                    report += "   ✅\n"
                except Exception as e:
                    failed_count += 1
                    report += f"   ❌ (Error: {str(e)})\n"
    
    report += f"\nTotal: {success_count} successful, {failed_count} failed"
    
    # Reset bot data
    bot_data.selected_groups = set()
    bot_data.selected_topics = {}
    bot_data.messages_to_forward = []
    
    await (query.edit_message_text if query else update.message.reply_text)(report)

def main() -> None:
    application = Application.builder().token(Config.TOKEN).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("done", done))
    
    # Message handler
    application.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & 
        ~filters.COMMAND & 
        (filters.TEXT | filters.PHOTO | filters.VIDEO | filters.DOCUMENT),
        handle_message
    ))
    
    # Callback query handlers
    application.add_handler(CallbackQueryHandler(start_process, pattern="^start_process$"))
    application.add_handler(CallbackQueryHandler(select_groups, pattern="^select_groups$"))
    application.add_handler(CallbackQueryHandler(toggle_group, pattern="^toggle_group:"))
    application.add_handler(CallbackQueryHandler(select_all_groups, pattern="^select_all_groups$"))
    application.add_handler(CallbackQueryHandler(confirm_send, pattern="^confirm_send$"))
    application.add_handler(CallbackQueryHandler(show_topic_selection, pattern="^select_topics:"))
    application.add_handler(CallbackQueryHandler(toggle_topic, pattern="^toggle_topic:"))
    application.add_handler(CallbackQueryHandler(select_all_topics, pattern="^select_all_topics:"))
    application.add_handler(CallbackQueryHandler(forward_messages, pattern="^forward_messages$"))
    
    # Run the bot
    application.run_polling()

if __name__ == "__main__":
    main()
