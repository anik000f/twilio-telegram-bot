import os
import re
import json
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from twilio.rest import Client

# Config
BOT_TOKEN = "7561627181:AAGKJdb-8zBY021M68Q4ca-GcEWQurXMtaE"
ADMIN_ID = 6569537485
DB_FILE = "bot_db.json"

# DB Functions
def load_db():
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"users": {}, "pending_approvals": []}

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Twilio Validate
async def validate_twilio_credentials(sid, token):
    try:
        client = Client(sid, token)
        client.api.accounts(sid).fetch()
        return True
    except:
        return False

# Main Menu
def main_menu(is_admin=False, has_twilio=False):
    buttons = [
        ["🔍 Search Number", "🎲 Random Number"],
        ["📨 Inbox", "🗑 Release Number"],
        ["👤 My Profile"]
    ]
    if not has_twilio:
        buttons.insert(0, ["🔑 Login with Twilio"])
    if is_admin:
        buttons.append(["👮 Admin Panel"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    db = load_db()

    if user_id not in db["users"]:
        db["users"][user_id] = {
            "name": update.effective_user.full_name,
            "twilio": None,
            "numbers": [],
            "approved": user_id == str(ADMIN_ID),
            "join_date": datetime.now().isoformat()
        }
        if user_id != str(ADMIN_ID):
            db["pending_approvals"].append(user_id)
        save_db(db)

    user_data = db["users"][user_id]

    if not user_data["approved"]:
        await update.message.reply_text("⏳ Your account is pending admin approval.")
        return

    await update.message.reply_text(
        "📱 Twilio Number Manager\n\n"
        "Please login with your Twilio credentials first.",
        reply_markup=main_menu(
            is_admin=(user_id == str(ADMIN_ID)),
            has_twilio=bool(user_data["twilio"])
        )
    )

# Handle Twilio Login
async def handle_twilio_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Please enter your Twilio credentials:\n\n"
        "Format: <code>SID|AuthToken</code>",
        parse_mode="HTML"
    )

# Process Twilio Credentials
async def process_twilio_credentials(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()
    db = load_db()

    try:
        sid, token = text.split("|", 1)
        sid, token = sid.strip(), token.strip()

        if not (len(sid) == 34 and sid.startswith("AC") and len(token) == 32):
            raise ValueError("Invalid format")

        if not await validate_twilio_credentials(sid, token):
            raise ValueError("Invalid credentials")

        db["users"][user_id]["twilio"] = {"sid": sid, "token": token}
        save_db(db)

        await update.message.reply_text(
            "✅ Twilio login successful!",
            reply_markup=main_menu(
                is_admin=(user_id == str(ADMIN_ID)),
                has_twilio=True
            )
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

# Admin: Approve User
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != str(ADMIN_ID):
        await update.message.reply_text("❌ You are not authorized to approve users.")
        return

    args = context.args
    if not args:
        await update.message.reply_text("Usage: /approve <user_id>")
        return

    user_id = args[0]
    db = load_db()

    if user_id in db["users"]:
        db["users"][user_id]["approved"] = True
        if user_id in db["pending_approvals"]:
            db["pending_approvals"].remove(user_id)
        save_db(db)
        await update.message.reply_text(f"✅ User {user_id} approved successfully.")
    else:
        await update.message.reply_text("❌ User not found.")

if __name__ == "__main__":
    # Init DB
    if not os.path.exists(DB_FILE):
        save_db({
            "users": {
                str(ADMIN_ID): {
                    "name": "Admin",
                    "twilio": None,
                    "numbers": [],
                    "approved": True,
                    "join_date": datetime.now().isoformat()
                }
            },
            "pending_approvals": []
        })

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(MessageHandler(filters.Regex(r'^🔑 Login with Twilio$'), handle_twilio_login))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^AC\w+\|.+\w$'), process_twilio_credentials))

    print("🤖 Bot is running...")
    app.run_polling()
