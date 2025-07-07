import os
import re
import json
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackQueryHandler
)
from twilio.rest import Client

# বেসিক কনফিগারেশন
BOT_TOKEN = "7561627181:AAGKJdb-8zBY021M68Q4ca-GcEWQurXMtaE"  # আপনার বট টোকেন
ADMIN_ID = 6569537485  # আপনার টেলিগ্রাম আইডি
DB_FILE = "bot_db.json"
AREA_CODES = ["+1", "+44", "+81", "+86", "+91"]  # US, UK, Japan, China, India

# ডাটাবেস ফাংশন
def load_db():
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"users": {}, "pending_approvals": []}

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# টুইলিও ভ্যালিডেশন
async def validate_twilio_credentials(sid, token):
    try:
        client = Client(sid, token)
        client.api.accounts(sid).fetch()  # টেস্ট রিকুয়েস্ট
        return True
    except:
        return False

# মেনু সিস্টেম
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

async def handle_twilio_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Please enter your Twilio credentials:\n\n"
        "Format: <code>SID|AuthToken</code>\n\n"
        "Example:\n"
        "<code>ACa2b3c4d5e6f7g8h9i0j1k2l3m4n5o6|34a5b6c7d8e9f0g1h2i3j4k5l6m7d8</code>",
        parse_mode="HTML"
    )

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

# ... (বাকি ফাংশনগুলো আগের মতোই থাকবে)

if __name__ == "__main__":
    # ডাটাবেস ইনিশিয়ালাইজ
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
    
    # বট অ্যাপ্লিকেশন তৈরি
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # হ্যান্ডলার যোগ
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex(r'^🔑 Login with Twilio$'), handle_twilio_login))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^AC\w+\|.+\w$'), process_twilio_credentials))
    
    # ... (অন্যান্য হ্যান্ডলার যোগ করুন)
    
    print("🤖 বট চালু হয়েছে...")
    app.run_polling()
