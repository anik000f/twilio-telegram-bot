import json
import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Bot config
BOT_TOKEN = "7561627181:AAGKJdb-8zBY021M68Q4ca-GcEWQurXMtaE"
ADMIN_ID = 6569537485
ALLOWED_USERS_FILE = "allowed_users.json"

def load_allowed_users():
    if os.path.exists(ALLOWED_USERS_FILE):
        with open(ALLOWED_USERS_FILE, "r") as f:
            data = json.load(f)
            return data.get("users", [])
    else:
        return []

def save_allowed_users(users):
    with open(ALLOWED_USERS_FILE, "w") as f:
        json.dump({"users": users}, f)

def is_authorized(user_id):
    allowed_users = load_allowed_users()
    return user_id in allowed_users

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not is_authorized(user_id):
        await update.message.reply_text("❌ Sorry, you are not authorized to use this bot.")
        return

    keyboard = [["Check Balance", "Buy Number"], ["Release Number", "View OTP"], ["Logout"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("✅ Welcome to your Twilio Telegram Bot!", reply_markup=reply_markup)

async def allow_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not admin!")
        return

    if len(context.args) != 1:
        await update.message.reply_text("⚠️ Usage: /allow <user_id>")
        return

    user_id = int(context.args[0])
    users = load_allowed_users()
    if user_id not in users:
        users.append(user_id)
        save_allowed_users(users)
        await update.message.reply_text(f"✅ User {user_id} allowed successfully!")
    else:
        await update.message.reply_text("ℹ️ User already allowed.")

async def block_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not admin!")
        return

    if len(context.args) != 1:
        await update.message.reply_text("⚠️ Usage: /block <user_id>")
        return

    user_id = int(context.args[0])
    users = load_allowed_users()
    if user_id in users:
        users.remove(user_id)
        save_allowed_users(users)
        await update.message.reply_text(f"✅ User {user_id} blocked!")
    else:
        await update.message.reply_text("ℹ️ User not in allowed list.")

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not admin!")
        return

    users = load_allowed_users()
    if not users:
        await update.message.reply_text("⚠️ No allowed users yet.")
    else:
        await update.message.reply_text("✅ Allowed Users:\n" + "\n".join([str(u) for u in users]))

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("allow", allow_user))
    app.add_handler(CommandHandler("block", block_user))
    app.add_handler(CommandHandler("list_users", list_users))

    app.run_polling()

if __name__ == "__main__":
    main()