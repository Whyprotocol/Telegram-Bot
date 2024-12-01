import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, CallbackQueryHandler, filters, ContextTypes
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Google Sheets setup
SERVICE_ACCOUNT_FILE = "gabebot_service.json"  # Replace with your JSON key file path
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = "1wut_DkJIp_CQXlsMQIi8-eaQRyoR7HGQU-xtxG6twvo"  # Replace with your spreadsheet ID

credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
sheets_service = build("sheets", "v4", credentials=credentials)

# States for conversation flow
CAPTCHA, MULTI_CHOICES, DATA_CHOICES, ASK_PHONE, ASK_EMAIL, ASK_DISCORD, SUBMIT_DATA = range(7)

# Store user choices and data
captcha_data = {}
user_choices = {}
user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Generate a random CAPTCHA and ask the user."""
    user_id = update.message.from_user.id
    num1, num2, operation, result = generate_captcha()
    captcha_data[user_id] = result

    question = f"Welcome to GabeAI! Community-driven, owned and shaped by the people who believe in it. WHY are you here?. Please solve this CAPTCHA to verify you are a human: What is {num1} {operation} {num2}?"
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
    choices = ["Launch Project", "Join Community", "I Don’t Know", "Join The Revolution"]
    keyboard = [
        [InlineKeyboardButton(f"{'✅' if choice in user_choices[user_id] else '❌'} {choice}", callback_data=choice)]
        for choice in choices
    ]
    keyboard.append([InlineKeyboardButton("Done", callback_data="done")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            "Please select your options (toggle ✅/❌). Press 'Done' when finished:",
            reply_markup=reply_markup,
        )
    else:
        await update.message.reply_text(
            "Please select your options (toggle ✅/❌). Press 'Done' when finished:",
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

        # Remove the multi-choice options
        await query.edit_message_text(f"{selected_text}",)


        # Now, proceed to ask data choices (this runs after the feedback message is sent)
        return await ask_data_choices(update, context)

    # Toggle the selected choice
    if choice in user_choices[user_id]:
        user_choices[user_id].remove(choice)
    else:
        user_choices[user_id].append(choice)

    await send_multi_choice(update, context, user_id)
    return MULTI_CHOICES

async def ask_data_choices(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask the user what data they want to provide, including the selected options."""
    keyboard = [
        [InlineKeyboardButton("Phone number", callback_data="phone")],
        [InlineKeyboardButton("Email address", callback_data="email")],
        [InlineKeyboardButton("Discord username", callback_data="discord")],
        [InlineKeyboardButton("I prefer not to share data", callback_data="none")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send the message with the selected options and the question about data
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
        await query.edit_message_text("Thank you! We will not collect additional data from you. Please join us at @whyprotocolchat")
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
    """Save user data to Google Sheets."""
    if is_callback:
        user = update.from_user  # Access user info from the CallbackQuery
    else:
        user = update.message.from_user  # Access user info from the Message

    telegram_username = user.username if user.username else f"{user.first_name or ''} {user.last_name or ''}".strip()
    if not telegram_username:
        telegram_username = "N/A"

    # Prepare data to save
    phone = user_data.get(user_id, {}).get('phone', "Not provided")
    email = user_data.get(user_id, {}).get('email', "Not provided")
    discord = user_data.get(user_id, {}).get('discord', "Not provided")
    selected_options = ", ".join(user_choices.get(user_id, []))

    # Save data to Google Sheets
    values = [[telegram_username, selected_options, phone, email, discord]]
    sheets_service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range="GabeBot",
        valueInputOption="USER_ENTERED",
        body={"values": values},
    ).execute()

    # Confirm with user
    if is_callback:
         return ConversationHandler.END
    else:
     await update.message.reply_text("Thank you! Your choices have been saved. Please join us at @whyprotocolchat")
     return ConversationHandler.END


def main():
    """Run the bot."""
    application = Application.builder().token("8054141332:AAF-OnD2HRYk6Iq9pKOs1wAdzwDxQL1-Mmc").build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CAPTCHA: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_captcha)],
            MULTI_CHOICES: [CallbackQueryHandler(handle_choice)],
            DATA_CHOICES: [CallbackQueryHandler(handle_data_choice)],
            ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone)],
            ASK_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_email)],
            ASK_DISCORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_discord)],
        },
        fallbacks=[CommandHandler('start', start)],
    )
    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == "__main__":
    main()
