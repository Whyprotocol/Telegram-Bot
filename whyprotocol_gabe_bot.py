""" from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
import asyncio

# Replace with your bot token
BOT_TOKEN = '7715966442:AAGyw03io4ZN9_FDHCwFb8eyTwOKJY5AnOU'

# Replace with the group chat ID where the bot should post
GROUP_CHAT_ID = -1002490269384

  # Replace with the actual chat ID of the public group

async def post_message():
    # Initialize the bot
    bot = Bot(BOT_TOKEN)

    # Message text
    text = "Community-driven, owned and shaped by the people who believe in it\n\nClick below to verify you're human"

    # Inline button linking to another Telegram chat
    keyboard = [
        [InlineKeyboardButton("Tap toverify", url="https://t.me/whyprotocolbot")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Path to the local image file
    image_path = "profile.jpeg"  # Replace with the actual file path

    # Send the message with the image
    with open(image_path, 'rb') as photo:
        await bot.send_photo(
            chat_id=GROUP_CHAT_ID,
            photo=photo,
            caption=text,
            reply_markup=reply_markup
        )

if __name__ == "__main__":
    asyncio.run(post_message())
 """

import random
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import TelegramError

import json
import os

JSON_FILE = "user_data.json"  # Path to the JSON file

# States for conversation flow
CAPTCHA, MULTI_CHOICES, DATA_CHOICES, ASK_ROLE, ASK_PHONE, ASK_EMAIL, ASK_DISCORD, SUBMIT_DATA = range(8)

# Store user choices and data
captcha_data = {}
user_choices = {}
user_data = {}
user_roles = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Generate a random CAPTCHA and ask the user."""
    user_id = update.message.from_user.id
    num1, num2, operation, result = generate_captcha()
    captcha_data[user_id] = result

    question = ("Welcome to WHY Community portal! \n\nMy name is Gabe and will help you joining our ecosystem. \n\n" 
                "WHY Protocol - community-driven, owned and shaped by the people who believe in it. \n\n" 
                f"Please solve this CAPTCHA to verify you are a human: What is {num1} {operation} {num2}?")
    await update.message.reply_text(question)
    return CAPTCHA

def generate_captcha():
    """Generate a random CAPTCHA."""
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    if random.choice([True, False]):
        return num1, num2, "+", num1 + num2
    else:
        if num1 < num2:
            num1, num2 = num2, num1
        return num1, num2, "-", num1 - num2

async def check_captcha(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Verify the CAPTCHA answer."""
    user_id = update.message.from_user.id
    user_answer = update.message.text.strip()

    if user_id in captcha_data and user_answer.isdigit() and int(user_answer) == captcha_data[user_id]:
        captcha_data.pop(user_id, None)
        user_choices[user_id] = []
        await send_multi_choice(update, context, user_id)
        return MULTI_CHOICES
    else:
        await update.message.reply_text("Wrong answer. Please try again.")
        return CAPTCHA

async def send_multi_choice(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    """Send multi-selection options."""
    choices = ["Launch Project", "Join Ecosystem", "Not Sure", "Join Community"]
    keyboard = [
        [InlineKeyboardButton(f"{'✅' if choice in user_choices[user_id] else '❌'} {choice}", callback_data=choice)]
        for choice in choices
    ]
    keyboard.append([InlineKeyboardButton("Done", callback_data="done")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            "WHY are you here?\nPlease select your options (toggle ✅/❌). Press 'Done' when finished:",
            reply_markup=reply_markup,
        )
    else:
        await update.message.reply_text(
            "WHY are you here?\nPlease select your options (toggle ✅/❌). Press 'Done' when finished:",
            reply_markup=reply_markup,
        )

async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle multi-choice toggling."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    choice = query.data

    if choice == "done":
        # Provide feedback based on selections
        if user_choices[user_id]:
            selected_text = f"You selected: {', '.join(user_choices[user_id])}"
        else:
            selected_text = "You didn't select any option."

        await query.edit_message_text(f"{selected_text}")
        return await ask_role(update, context)

    # Toggle the selected choice
    if choice in user_choices[user_id]:
        user_choices[user_id].remove(choice)
    else:
        user_choices[user_id].append(choice)

    await send_multi_choice(update, context, user_id)
    return MULTI_CHOICES

async def ask_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask how the user wants to be addressed."""
    keyboard = [
        [InlineKeyboardButton("Founder", callback_data="Founder")],
        [InlineKeyboardButton("Project", callback_data="Project")],
        [InlineKeyboardButton("Investor", callback_data="Investor")],
        [InlineKeyboardButton("Degen", callback_data="Degen")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.message.reply_text(
        "How can (W)e (H)elp (Y)ou and address you? Please select one of the options:", reply_markup=reply_markup
    )
    return ASK_ROLE

async def handle_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user's selected role."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_roles[user_id] = query.data

    await query.edit_message_text(f"You selected: {query.data}")
    return await ask_data_choices(update, context)

async def ask_data_choices(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask the user what data they want to provide."""
    keyboard = [
        [InlineKeyboardButton("Phone number", callback_data="phone")],
        [InlineKeyboardButton("Email address", callback_data="email")],
        [InlineKeyboardButton("Discord username", callback_data="discord")],
        [InlineKeyboardButton("I prefer not to share data", callback_data="none")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.message.reply_text(
        "What contact information would you like to provide in order to get in touch with you regarding WHY Protocol?",
        reply_markup=reply_markup
    )
    return DATA_CHOICES

async def handle_data_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle user's data-sharing preference."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "phone":
        return await ask_for_phone(update, context)
    elif query.data == "email":
        return await ask_for_email(update, context)
    elif query.data == "discord":
        return await ask_for_discord(update, context)
    else:  # User chose not to share data
        # Remove buttons and inform the user
                # Replace with your private group chat ID
        chat_id = "-1002412611337"  # Private group's username or chat ID
        bot = context.bot  # Get the bot instance
        
        # Create an invite link that expires after 1 minute
        invite_link = await bot.create_chat_invite_link(chat_id, expire_date=int((datetime.now() + timedelta(minutes=1)).timestamp()))

        # Send the personal invite link to the user
        await update.callback_query.edit_message_text(
                f"Thank you! Your data has been saved. Here is your personal invite link to the group: {invite_link.invite_link}\nThe link will expire in 1 minute."
            )
       
        await save_user_data(query, context, user_id, is_callback=True)
        return ConversationHandler.END

async def ask_for_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask for phone number."""
    await update.callback_query.edit_message_text("Please provide your phone number:")
    return ASK_PHONE

async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle phone number input."""
    user_id = update.message.from_user.id
    user_data[user_id] = {'phone': update.message.text.strip()}
    await save_user_data(update, context, user_id)
    return SUBMIT_DATA

async def ask_for_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask for email."""
    await update.callback_query.edit_message_text("Please provide your email:")
    return ASK_EMAIL

async def handle_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle email input."""
    user_id = update.message.from_user.id
    user_data[user_id] = {'email': update.message.text.strip()}
    await save_user_data(update, context, user_id)
    return SUBMIT_DATA

async def ask_for_discord(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask for Discord username."""
    await update.callback_query.edit_message_text("Please provide your Discord username:")
    return ASK_DISCORD

async def handle_discord(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle Discord username input."""
    user_id = update.message.from_user.id
    user_data[user_id] = {'discord': update.message.text.strip()}
    await save_user_data(update, context, user_id)
    return SUBMIT_DATA

async def save_user_data(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, is_callback=False) -> None:
    """Save user data to a JSON file."""

    user = update.message.from_user  

    telegram_username = user.username if user.username else f"{user.first_name or ''} {user.last_name or ''}".strip()
    if not telegram_username:
        telegram_username = "N/A"

    phone = user_data.get(user_id, {}).get('phone', "Not provided")
    email = user_data.get(user_id, {}).get('email', "Not provided")
    discord = user_data.get(user_id, {}).get('discord', "Not provided")
    selected_options = ", ".join(user_choices.get(user_id, []))
    role = user_roles.get(user_id, "Not provided")

    user_entry = {
        "telegram_username": telegram_username,
        "selected_options": selected_options,
        "role": role,
        "phone": phone,
        "email": email,
        "discord": discord
    }

    try:
        if os.path.exists(JSON_FILE):
            with open(JSON_FILE, "r") as f:
                data = json.load(f)
        else:
            data = []

        data.append(user_entry)

        with open(JSON_FILE, "w") as f:
            json.dump(data, f, indent=4)

    except Exception as e:
        # Handle file I/O errors
        print(f"Error saving data to JSON: {e}")
    # Generate personal invite link
    try:
        # Replace with your private group chat ID
        chat_id = "-1002412611337"  # Private group's username or chat ID
        bot = context.bot  # Get the bot instance
        invite_link = await bot.export_chat_invite_link(chat_id)  # Expires in 1 minute

        # Send the personal invite link to the user
        if is_callback:
            await update.callback_query.edit_message_text(
                f"Thank you! Your data has been saved. Here is your personal invite link to the group: {invite_link}\nThe link will expire in 1 minute."
            )
        else:
            await update.message.reply_text(
                f"Thank you! Your data has been saved. Here is your personal invite link to the group: {invite_link}\nThe link will expire in 1 minute."
            )
    except TelegramError as e:
        print(f"Error generating invite link: {e}")
        # Fallback if invite link generation fails

def main():
    """Run the bot."""
    application = Application.builder().token("7715966442:AAGyw03io4ZN9_FDHCwFb8eyTwOKJY5AnOU").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CAPTCHA: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_captcha)],
            MULTI_CHOICES: [CallbackQueryHandler(handle_choice)],
            ASK_ROLE: [CallbackQueryHandler(handle_role)],
            DATA_CHOICES: [CallbackQueryHandler(handle_data_choice)],
            ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone)],
            ASK_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_email)],
            ASK_DISCORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_discord)],
            SUBMIT_DATA: [MessageHandler(filters.TEXT & ~filters.COMMAND, lambda update, context: None)],  # Placeholder
        },
        fallbacks=[CommandHandler('start', start)],
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == "__main__":
    main()
