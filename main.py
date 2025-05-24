import os
import logging
from typing import Dict, List, Set, Optional
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    BotCommand,
    ForumTopic
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

class BotData:
    def __init__(self):
        self.reset()
        
    def reset(self):
        self.received_items = {
            'videos': 0,
            'files': 0,
            'texts': 0,
            'others': 0
        }
        self.collecting = False
        self.selected_groups: Set[int] = set()
        self.selected_topics: Dict[int, Set[int]] = {}
        self.messages_to_forward: List[Dict] = []
        self.groups_info: Dict[int, Dict] = {}
        self.current_topic_name: Optional[str] = None

bot_data = BotData()

async def fetch_groups_info(context: ContextTypes.DEFAULT_TYPE) -> Dict[int, Dict]:
    """Fetch info for all configured groups"""
    groups_info = {}
    
    for group_id in Config.GROUP_IDS:
        try:
            chat = await context.bot.get_chat(group_id)
            
            # Verify bot is admin
            chat_member = await context.bot.get_chat_member(
                chat_id=group_id,
                user_id=context.bot.id
            )
            
            if chat_member.status not in ['administrator', 'creator']:
                logger.warning(f"Bot is not admin in group {group_id}")
                continue
            
            # Get existing topics
            topics = {}
            try:
                forum_topics = await context.bot.get_forum_topics(chat_id=group_id)
                for topic in forum_topics.topics:
                    topics[topic.message_thread_id] = topic.name
            except Exception as e:
                logger.info(f"Group {group_id} is not a forum or has no topics: {e}")
            
            groups_info[group_id] = {
                'name': chat.title,
                'topics': topics
            }
            
        except Exception as e:
            logger.error(f"Error processing group {group_id}: {e}")
    
    return groups_info

async def create_new_topic(context: ContextTypes.DEFAULT_TYPE, group_id: int, topic_name: str) -> Optional[int]:
    """Create a new topic in the specified group"""
    try:
        result = await context.bot.create_forum_topic(
            chat_id=group_id,
            name=topic_name
        )
        return result.message_thread_id
    except Exception as e:
        logger.error(f"Error creating topic {topic_name} in group {group_id}: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != Config.AUTHORIZED_USER_ID:
        await update.message.reply_text("❌ Unauthorized access!")
        return

    bot_data.groups_info = await fetch_groups_info(context)
    
    welcome_msg = (
        f"ʜᴇʟʟᴏ, {update.effective_user.full_name} ꜱɪʀ!\n\n"
        "ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴏᴜʀ ꜰᴏʀᴡᴀʀᴅɪɴɢ ʙᴏᴛ ꜱᴇʀᴠɪᴄᴇ.\n\n"
        "ꜱɪᴍᴘʟʏ ꜱᴇɴᴅ ᴀɴʏ ᴍᴇꜱꜱᴀɢᴇ, ᴘʜᴏᴛᴏ, ᴠɪᴅᴇᴏ, ᴅᴏᴄᴜᴍᴇɴᴛ, ᴏʀ ꜰɪʟᴇ ʜᴇʀᴇ — ᴀɴᴅ ᴏᴜʀ ʙᴏᴛ ᴡɪʟʟ ɪɴꜱᴛᴀɴᴛʟʏ ꜰᴏʀᴡᴀʀᴅ ɪᴛ ᴛᴏ ʏᴏᴜʀ ᴅᴇꜱɪɢɴᴀᴛᴇᴅ ɢʀᴏᴜᴘ, ᴇɴꜱᴜʀɪɴɢ ꜱᴇᴀᴍʟᴇꜱꜱ ᴀɴᴅ ᴇꜰꜰɪᴄɪᴇɴᴛ ᴅᴇʟɪᴠᴇʀʏ ᴡɪᴛʜᴏᴜᴛ ᴀɴʏ ᴅᴇʟᴀʏ.\n\n"
        "ᴍᴀᴅᴇ ᴡɪᴛʜ ❤️ ʙʏ 𝐂𝐀 𝐈𝐧𝐭𝐞𝐫 𝐗"
    )

    keyboard = [
        [InlineKeyboardButton("Start Process", callback_data="start_process")],
        [InlineKeyboardButton("Refresh Groups", callback_data="refresh_groups")]
    ]
    await update.message.reply_text(welcome_msg, reply_markup=InlineKeyboardMarkup(keyboard))

async def refresh_groups(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Refresh group list manually"""
    query = update.callback_query
    await query.answer()
    
    bot_data.groups_info = await fetch_groups_info(context)
    group_count = len(bot_data.groups_info)
    
    await query.edit_message_text(
        f"♻️ Refreshed group list!\n"
        f"Found {group_count} groups where I'm admin."
    )

async def start_process(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    bot_data.reset()
    bot_data.collecting = True
    await query.edit_message_text(
        "📤 Send me videos, files, text messages etc.\n"
        "When finished, send /done command\n\n"
        "I'll count all received items automatically!"
    )

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
    msg_data = {
        'type': 'video' if message.video else 
               'document' if message.document else 
               'photo' if message.photo else 
               'text',
        'content': message.video or message.document or 
                  (message.photo[-1] if message.photo else None) or 
                  message.text,
        'caption': message.caption,
        'entities': message.entities or message.caption_entities
    }
    bot_data.messages_to_forward.append(msg_data)

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != Config.AUTHORIZED_USER_ID:
        return

    bot_data.collecting = False
    
    report = (
        "📊 Received Items Summary:\n\n"
        f"🎥 Videos - {bot_data.received_items['videos']}\n"
        f"📁 Files - {bot_data.received_items['files']}\n"
        f"📝 Text Messages - {bot_data.received_items['texts']}\n"
        f"📦 Others - {bot_data.received_items['others']}\n\n"
        f"🔢 Total - {sum(bot_data.received_items.values())}"
    )
    
    if not bot_data.groups_info:
        bot_data.groups_info = await fetch_groups_info(context)
    
    if not bot_data.groups_info:
        await update.message.reply_text(
            "❌ No groups found where I'm admin!\n"
            "Please add me to groups and make me admin first."
        )
        return
    
    keyboard = [[InlineKeyboardButton("Select Groups", callback_data="select_groups")]]
    await update.message.reply_text(report, reply_markup=InlineKeyboardMarkup(keyboard))

def create_group_keyboard() -> InlineKeyboardMarkup:
    keyboard = []
    for group_id, group_info in bot_data.groups_info.items():
        is_selected = group_id in bot_data.selected_groups
        emoji = "✅" if is_selected else "◻️"
        keyboard.append([
            InlineKeyboardButton(
                f"{group_info['name']} {emoji}",
                callback_data=f"toggle_group:{group_id}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("Select All", callback_data="select_all_groups"),
        InlineKeyboardButton("Proceed ➡️", callback_data="confirm_send")
    ])
    
    return InlineKeyboardMarkup(keyboard)

async def select_groups(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "👥 Select Groups to Forward:",
        reply_markup=create_group_keyboard()
    )

async def toggle_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    group_id = int(query.data.split(':')[1])
    
    if group_id in bot_data.selected_groups:
        bot_data.selected_groups.remove(group_id)
        if group_id in bot_data.selected_topics:
            del bot_data.selected_topics[group_id]
    else:
        bot_data.selected_groups.add(group_id)
    
    await query.edit_message_reply_markup(create_group_keyboard())

async def select_all_groups(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    bot_data.selected_groups = set(bot_data.groups_info.keys())
    await query.edit_message_reply_markup(create_group_keyboard())

async def confirm_send(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if not bot_data.selected_groups:
        await query.answer("Please select at least one group!", show_alert=True)
        return
    
    # Check which groups have topics
    groups_with_topics = {
        group_id: group_info 
        for group_id, group_info in bot_data.groups_info.items() 
        if group_id in bot_data.selected_groups and group_info['topics']
    }
    
    if groups_with_topics:
        bot_data.selected_topics = {group_id: set() for group_id in groups_with_topics}
        first_group_id = list(groups_with_topics.keys())[0]
        await show_topic_selection(update, context, first_group_id)
    else:
        await forward_messages(update, context)

def create_topic_keyboard(group_id: int) -> InlineKeyboardMarkup:
    group_info = bot_data.groups_info[group_id]
    keyboard = []
    
    for topic_id, topic_name in group_info['topics'].items():
        is_selected = topic_id in bot_data.selected_topics.get(group_id, set())
        emoji = "✅" if is_selected else "◻️"
        keyboard.append([
            InlineKeyboardButton(
                f"{topic_name} {emoji}",
                callback_data=f"toggle_topic:{group_id}:{topic_id}"
            )
        ])
    
    # Navigation buttons if multiple groups
    if len(bot_data.selected_groups) > 1:
        group_ids = list(bot_data.selected_groups)
        current_idx = group_ids.index(group_id)
        nav_buttons = []
        
        if current_idx > 0:
            prev_group_id = group_ids[current_idx - 1]
            nav_buttons.append(
                InlineKeyboardButton("◀️ Prev", callback_data=f"select_topics:{prev_group_id}")
            )
        
        if current_idx < len(group_ids) - 1:
            next_group_id = group_ids[current_idx + 1]
            nav_buttons.append(
                InlineKeyboardButton("Next ▶️", callback_data=f"select_topics:{next_group_id}")
            )
        
        if nav_buttons:
            keyboard.append(nav_buttons)
    
    keyboard.append([
        InlineKeyboardButton("Select All", callback_data=f"select_all_topics:{group_id}"),
        InlineKeyboardButton("Back to Groups", callback_data="select_groups")
    ])
    
    keyboard.append([
        InlineKeyboardButton("Send Now", callback_data="forward_messages")
    ])
    
    return InlineKeyboardMarkup(keyboard)

async def show_topic_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, group_id: int) -> None:
    query = update.callback_query
    await query.answer()
    
    group_info = bot_data.groups_info[group_id]
    await query.edit_message_text(
        f"📚 Select Topics in {group_info['name']}:",
        reply_markup=create_topic_keyboard(group_id)
    )

async def toggle_topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    _, group_id, topic_id = query.data.split(':')
    group_id = int(group_id)
    topic_id = int(topic_id)
    
    if group_id not in bot_data.selected_topics:
        bot_data.selected_topics[group_id] = set()
    
    if topic_id in bot_data.selected_topics[group_id]:
        bot_data.selected_topics[group_id].remove(topic_id)
    else:
        bot_data.selected_topics[group_id].add(topic_id)
    
    await query.edit_message_reply_markup(create_topic_keyboard(group_id))

async def select_all_topics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    group_id = int(query.data.split(':')[1])
    bot_data.selected_topics[group_id] = set(bot_data.groups_info[group_id]['topics'].keys())
    await query.edit_message_reply_markup(create_topic_keyboard(group_id))

async def forward_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query:
        await query.answer()
    
    if not bot_data.messages_to_forward:
        await (query.edit_message_text if query else update.message.reply_text)(
            "❌ No messages to forward!"
        )
        return

    total_messages = len(bot_data.messages_to_forward)
    total_targets = 0
    report = "🚀 Forwarding Report:\n\n"
    
    for group_id in bot_data.selected_groups:
        group_name = bot_data.groups_info[group_id]['name']
        topic_ids = bot_data.selected_topics.get(group_id, {None})
        
        for topic_id in topic_ids:
            topic_name = ""
            if topic_id:
                topic_name = f" (Topic: {bot_data.groups_info[group_id]['topics'][topic_id]})"
            
            report += f"➡️ {group_name}{topic_name}:\n"
            success, failed = 0, 0
            
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
                    success += 1
                except Exception as e:
                    failed += 1
                    logger.error(f"Forwarding failed to {group_id}/{topic_id}: {e}")
            
            total_targets += 1
            report += f"   ✅ {success} | ❌ {failed}\n"
    
    report += (
        f"\n📊 Summary:\n"
        f"• {total_messages} messages\n"
        f"• {len(bot_data.selected_groups)} groups\n"
        f"• {total_targets} total destinations\n"
        f"\n✔️ Forwarding completed!"
    )
    
    # Reset bot state
    bot_data.reset()
    
    await (query.edit_message_text if query else update.message.reply_text)(report)

async def handle_new_topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle when user wants to create a new topic"""
    if update.effective_user.id != Config.AUTHORIZED_USER_ID:
        return

    if not bot_data.selected_groups:
        await update.message.reply_text("Please select groups first!")
        return

    topic_name = update.message.text
    bot_data.current_topic_name = topic_name
    
    keyboard = []
    for group_id in bot_data.selected_groups:
        group_name = bot_data.groups_info[group_id]['name']
        keyboard.append([
            InlineKeyboardButton(
                f"Create in {group_name}",
                callback_data=f"create_topic:{group_id}"
            )
        ])
    
    await update.message.reply_text(
        f"Create topic '{topic_name}' in which groups?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def create_topic_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Actually create the new topic"""
    query = update.callback_query
    await query.answer()
    
    if not bot_data.current_topic_name:
        await query.edit_message_text("No topic name specified!")
        return

    group_id = int(query.data.split(':')[1])
    
    try:
        topic_id = await create_new_topic(context, group_id, bot_data.current_topic_name)
        if topic_id:
            # Update our groups info
            if group_id in bot_data.groups_info:
                bot_data.groups_info[group_id]['topics'][topic_id] = bot_data.current_topic_name
            
            await query.edit_message_text(
                f"✅ Created topic '{bot_data.current_topic_name}' in {bot_data.groups_info[group_id]['name']}"
            )
        else:
            await query.edit_message_text("❌ Failed to create topic!")
    except Exception as e:
        logger.error(f"Error creating topic: {e}")
        await query.edit_message_text("❌ Error creating topic!")

def main() -> None:
    # Verify configuration
    if not Config.TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN not set in environment variables!")
        exit(1)
    
    if Config.AUTHORIZED_USER_ID == 0:
        logger.error("❌ AUTHORIZED_USER_ID not set or invalid!")
        exit(1)

    if not Config.GROUP_IDS:
        logger.error("❌ No GROUP_IDS configured in environment variables!")
        exit(1)

    # Create application
    application = Application.builder().token(Config.TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("done", done))
    application.add_handler(CommandHandler("newtopic", handle_new_topic))
    application.add_handler(CommandHandler("refresh", refresh_groups))
    
    application.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & 
        ~filters.COMMAND & 
        (filters.TEXT | filters.PHOTO | filters.VIDEO | filters.Document.ALL),
        handle_message
    ))
    
    # Callback query handlers
    application.add_handler(CallbackQueryHandler(start_process, pattern="^start_process$"))
    application.add_handler(CallbackQueryHandler(refresh_groups, pattern="^refresh_groups$"))
    application.add_handler(CallbackQueryHandler(select_groups, pattern="^select_groups$"))
    application.add_handler(CallbackQueryHandler(toggle_group, pattern="^toggle_group:"))
    application.add_handler(CallbackQueryHandler(select_all_groups, pattern="^select_all_groups$"))
    application.add_handler(CallbackQueryHandler(confirm_send, pattern="^confirm_send$"))
    application.add_handler(CallbackQueryHandler(show_topic_selection, pattern="^select_topics:"))
    application.add_handler(CallbackQueryHandler(toggle_topic, pattern="^toggle_topic:"))
    application.add_handler(CallbackQueryHandler(select_all_topics, pattern="^select_all_topics:"))
    application.add_handler(CallbackQueryHandler(forward_messages, pattern="^forward_messages$"))
    application.add_handler(CallbackQueryHandler(create_topic_handler, pattern="^create_topic:"))
    
    # Run bot
    logger.info("🤖 Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
