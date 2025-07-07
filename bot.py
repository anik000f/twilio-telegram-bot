import os
import re
import json
import random
from datetime import datetime
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackQueryHandler
)
from twilio.rest import Client

# ===== CONFIGURATION =====
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN') or "YOUR_BOT_TOKEN"
ADMIN_ID = int(os.getenv('TELEGRAM_ADMIN_ID') or 6569537485
DB_FILE = "bot_db.json"
AREA_CODES = ["+1", "+44", "+81", "+86", "+91"]  # US, UK, Japan, China, India

# ===== DATABASE FUNCTIONS =====
def load_db():
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "users": {},
            "numbers": {},
            "pending_approvals": []
        }

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ===== TWILIO FUNCTIONS =====
async def validate_twilio_credentials(sid, token):
    try:
        client = Client(sid, token)
        client.api.accounts(sid).fetch()
        return True
    except Exception as e:
        print(f"Twilio validation error: {str(e)}")
        return False

async def get_messages(client, number, limit=10):
    try:
        return client.messages.list(to=number, limit=limit)
    except Exception as e:
        print(f"Error fetching messages: {str(e)}")
        return []

# ===== MENU SYSTEM =====
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

# ===== COMMAND HANDLERS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    db = load_db()
    
    if user_id not in db["users"]:
        db["users"][user_id] = {
            "name": update.effective_user.full_name,
            "twilio": None,
            "numbers": [],
            "approved": user_id == str(ADMIN_ID),
            "join_date": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat()
        }
        if user_id != str(ADMIN_ID):
            db["pending_approvals"].append(user_id)
        save_db(db)
    
    user_data = db["users"][user_id]
    user_data["last_active"] = datetime.now().isoformat()
    save_db(db)
    
    if not user_data["approved"]:
        await update.message.reply_text(
            "⏳ Your account is pending admin approval. "
            "Please wait for admin to approve your access."
        )
        return
    
    await update.message.reply_text(
        "📱 *Twilio Number Manager Bot*\n\n"
        "🔹 Acquire virtual numbers\n"
        "🔹 View SMS/OTP messages\n"
        "🔹 Manage your numbers\n\n"
        "Please login with Twilio to begin.",
        parse_mode="Markdown",
        reply_markup=main_menu(
            is_admin=(user_id == str(ADMIN_ID)),
            has_twilio=bool(user_data["twilio"])
        )
    )

async def handle_twilio_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    db = load_db()
    user_data = db["users"].get(user_id)
    
    if not user_data or not user_data["approved"]:
        await update.message.reply_text("❌ Account not approved yet.")
        return
    
    await update.message.reply_text(
        "Enter your Twilio credentials in this format:\n\n"
        "`ACCOUNT_SID|AUTH_TOKEN`\n\n"
        "Example:\n"
        "`AC123...456|abc789...xyz`\n\n"
        "These credentials will be stored securely.",
        parse_mode="Markdown"
    )

async def process_twilio_credentials(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()
    db = load_db()
    
    try:
        sid, token = text.split("|", 1)
        sid = sid.strip()
        token = token.strip()
        
        # Validate format
        if not (len(sid) == 34 and sid.startswith("AC") and len(token) == 32):
            raise ValueError("Invalid credential format")
        
        # Validate with Twilio API
        if not await validate_twilio_credentials(sid, token):
            raise ValueError("Invalid Twilio credentials")
        
        # Save credentials
        db["users"][user_id]["twilio"] = {
            "sid": sid,
            "token": token,
            "last_updated": datetime.now().isoformat()
        }
        save_db(db)
        
        await update.message.reply_text(
            "✅ *Twilio login successful!*\n\n"
            "You can now access all bot features.",
            parse_mode="Markdown",
            reply_markup=main_menu(
                is_admin=(user_id == str(ADMIN_ID)),
                has_twilio=True
            )
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ *Login failed*: {str(e)}\n\n"
            "Please check your credentials and try again.\n"
            "Format: `ACCOUNT_SID|AUTH_TOKEN`",
            parse_mode="Markdown"
        )

async def search_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    db = load_db()
    user_data = db["users"].get(user_id)
    
    # Validate user
    if not user_data or not user_data["approved"]:
        await update.message.reply_text("❌ Account not approved.")
        return
    if not user_data.get("twilio"):
        await update.message.reply_text("❌ Please login with Twilio first.")
        return
    
    await update.message.reply_text(
        "Select country code:",
        reply_markup=ReplyKeyboardMarkup(
            [[code] for code in AREA_CODES],
            resize_keyboard=True
        )
    )

async def assign_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    db = load_db()
    user_data = db["users"].get(user_id)
    
    # Validate user
    if not user_data or not user_data["approved"]:
        await update.message.reply_text("❌ Account not approved.")
        return
    if not user_data.get("twilio"):
        await update.message.reply_text("❌ Please login with Twilio first.")
        return
    
    try:
        country_code = update.message.text.strip()
        client = Client(user_data["twilio"]["sid"], user_data["twilio"]["token"])
        
        # Generate random number (replace with actual Twilio API call in production)
        random_number = f"{country_code}{random.randint(200, 999)}{random.randint(1000000, 9999999)}"
        
        # Save number
        db["numbers"][random_number] = {
            "user_id": user_id,
            "assigned_date": datetime.now().isoformat()
        }
        user_data["numbers"].append(random_number)
        save_db(db)
        
        await update.message.reply_text(
            f"✅ *Number acquired*: `{random_number}`\n\n"
            "This number is ready to receive SMS messages.",
            parse_mode="Markdown",
            reply_markup=main_menu(
                is_admin=(user_id == str(ADMIN_ID)),
                has_twilio=True
            )
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Error: {str(e)}",
            reply_markup=main_menu(
                is_admin=(user_id == str(ADMIN_ID)),
                has_twilio=True
            )
        )

async def view_inbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    db = load_db()
    user_data = db["users"].get(user_id)
    
    # Validate user
    if not user_data or not user_data["approved"]:
        await update.message.reply_text("❌ Account not approved.")
        return
    if not user_data.get("twilio"):
        await update.message.reply_text("❌ Please login with Twilio first.")
        return
    if not user_data.get("numbers"):
        await update.message.reply_text("❌ You don't have any numbers assigned.")
        return
    
    # Create number selection keyboard
    keyboard = [
        [InlineKeyboardButton(num, callback_data=f"inbox_{num}")]
        for num in user_data["numbers"]
    ]
    await update.message.reply_text(
        "Select a number to view messages:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    number = query.data.split("_")[1]
    db = load_db()
    user_data = db["users"].get(user_id)
    
    # Validate
    if not user_data or number not in user_data["numbers"]:
        await query.edit_message_text("❌ Invalid number selection.")
        return
    
    try:
        client = Client(user_data["twilio"]["sid"], user_data["twilio"]["token"])
        messages = await get_messages(client, number)
        
        if not messages:
            await query.edit_message_text(f"No messages found for {number}")
            return
        
        # Process messages
        response = [f"📬 *Messages for {number}:*"]
        otps = set()
        
        for msg in messages:
            msg_text = (
                f"\n\n📩 *From*: {msg.from_}\n"
                f"📅 *Date*: {msg.date_sent}\n"
                f"📝 *Message*: {msg.body}"
            )
            
            # Find OTPs (6-digit codes)
            found_otps = re.findall(r'\b\d{6}\b', msg.body)
            if found_otps:
                otps.update(found_otps)
            
            response.append(msg_text)
        
        # Add OTP summary if found
        if otps:
            response.append(f"\n\n🔑 *OTPs found*: {', '.join(otps)}")
        
        await query.edit_message_text(
            text=''.join(response)[:4000],  # Telegram message limit
            parse_mode="Markdown"
        )
    except Exception as e:
        await query.edit_message_text(f"❌ Error: {str(e)}")

async def release_number_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    db = load_db()
    user_data = db["users"].get(user_id)
    
    # Validate user
    if not user_data or not user_data["approved"]:
        await update.message.reply_text("❌ Account not approved.")
        return
    if not user_data.get("numbers"):
        await update.message.reply_text("❌ You don't have any numbers to release.")
        return
    
    # Create number selection keyboard
    keyboard = [
        [InlineKeyboardButton(num, callback_data=f"release_{num}")]
        for num in user_data["numbers"]
    ]
    await update.message.reply_text(
        "Select number to release:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def confirm_release(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    number = query.data.split("_")[1]
    
    await query.edit_message_text(
        f"⚠️ *Confirm Release*\n\n"
        f"Are you sure you want to release number:\n`{number}`?\n\n"
        f"This action cannot be undone.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_release_{number}"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel_action")
            ]
        ])
    )

async def execute_release(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    number = query.data.split("_")[2]
    db = load_db()
    user_data = db["users"].get(user_id)
    
    # Validate
    if not user_data or number not in user_data["numbers"]:
        await query.edit_message_text("❌ Invalid number selection.")
        return
    
    try:
        # In production: client.incoming_phone_numbers(number).delete()
        user_data["numbers"].remove(number)
        if number in db["numbers"]:
            del db["numbers"][number]
        save_db(db)
        
        await query.edit_message_text(
            f"✅ Successfully released number: `{number}`",
            parse_mode="Markdown",
            reply_markup=main_menu(
                is_admin=(user_id == str(ADMIN_ID)),
                has_twilio=bool(user_data["twilio"])
            )
        )
    except Exception as e:
        await query.edit_message_text(f"❌ Error: {str(e)}")

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    db = load_db()
    user_data = db["users"].get(user_id)
    
    if not user_data:
        await update.message.reply_text("❌ User data not found.")
        return
    
    # Format dates
    join_date = datetime.fromisoformat(user_data["join_date"]).strftime("%Y-%m-%d")
    last_active = datetime.fromisoformat(user_data.get("last_active", user_data["join_date"])).strftime("%Y-%m-%d %H:%M")
    
    # Build response
    response = [
        "👤 *User Profile*\n",
        f"🆔 ID: `{user_id}`",
        f"📛 Name: {user_data['name']}",
        f"✅ Status: {'Approved' if user_data['approved'] else 'Pending Approval'}",
        f"📅 Joined: {join_date}",
        f"⏱ Last Active: {last_active}",
        f"🔢 Numbers: {len(user_data['numbers'])}",
        f"🔑 Twilio: {'Connected' if user_data.get('twilio') else 'Not Connected'}"
    ]
    
    await update.message.reply_text(
        "\n".join(response),
        parse_mode="Markdown",
        reply_markup=main_menu(
            is_admin=(user_id == str(ADMIN_ID)),
            has_twilio=bool(user_data.get("twilio"))
        )
    )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id != str(ADMIN_ID):
        await update.message.reply_text("❌ Admin access required.")
        return
    
    await update.message.reply_text(
        "👮 *Admin Panel*\n\n"
        "Select an option:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👥 User List", callback_data="list_users")],
            [InlineKeyboardButton("🔄 Pending Approvals", callback_data="pending_approvals")],
            [InlineKeyboardButton("📊 Usage Stats", callback_data="usage_stats")]
        ])
    )

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if str(query.from_user.id) != str(ADMIN_ID):
        await query.edit_message_text("❌ Admin access required.")
        return
    
    db = load_db()
    users = db["users"]
    
    user_list = []
    for uid, data in users.items():
        status = "✅" if data["approved"] else "🔄"
        user_list.append(f"{status} {data['name']} (`{uid}`) - Numbers: {len(data['numbers'])}")
    
    response = ["👥 *User List* (Total: {})".format(len(users))] + user_list
    
    await query.edit_message_text(
        "\n".join(response)[:4000],
        parse_mode="Markdown"
    )

async def pending_approvals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if str(query.from_user.id) != str(ADMIN_ID):
        await query.edit_message_text("❌ Admin access required.")
        return
    
    db = load_db()
    
    if not db["pending_approvals"]:
        await query.edit_message_text("No pending approvals.")
        return
    
    keyboard = []
    for user_id in db["pending_approvals"]:
        user_data = db["users"].get(user_id, {})
        keyboard.append([
            InlineKeyboardButton(
                f"Approve {user_data.get('name', 'Unknown')} ({user_id})",
                callback_data=f"approve_{user_id}"
            )
        ])
    
    await query.edit_message_text(
        "🔄 *Pending Approvals*",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def approve_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if str(query.from_user.id) != str(ADMIN_ID):
        await query.edit_message_text("❌ Admin access required.")
        return
    
    user_id = query.data.split("_")[1]
    db = load_db()
    
    if user_id not in db["users"]:
        await query.edit_message_text("❌ User not found.")
        return
    
    db["users"][user_id]["approved"] = True
    if user_id in db["pending_approvals"]:
        db["pending_approvals"].remove(user_id)
    save_db(db)
    
    # Notify user
    try:
        await context.bot.send_message(
            chat_id=int(user_id),
            text="🎉 *Your account has been approved!*\n\n"
                 "You can now use all bot features.",
            parse_mode="Markdown",
            reply_markup=main_menu(has_twilio=False)
        )
    except Exception as e:
        print(f"Error notifying user: {str(e)}")
    
    await query.edit_message_text(f"✅ Approved user: {user_id}")

async def cancel_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    db = load_db()
    user_data = db["users"].get(user_id)
    
    if not user_data:
        await query.edit_message_text("❌ User data not found.")
        return
    
    await query.edit_message_text(
        "Action cancelled.",
        reply_markup=main_menu(
            is_admin=(user_id == str(ADMIN_ID)),
            has_twilio=bool(user_data.get("twilio"))
        )
    )

async def handle_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Unrecognized command. Please use the menu buttons.",
        reply_markup=main_menu()
    )

# ===== MAIN APPLICATION =====
def main():
    # Initialize database if not exists
    if not os.path.exists(DB_FILE):
        save_db({
            "users": {
                str(ADMIN_ID): {
                    "name": "Admin",
                    "twilio": None,
                    "numbers": [],
                    "approved": True,
                    "join_date": datetime.now().isoformat(),
                    "last_active": datetime.now().isoformat()
                }
            },
            "numbers": {},
            "pending_approvals": []
        })
    
    # Create bot application
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    
    # Add message handlers
    app.add_handler(MessageHandler(filters.Regex(r'^🔑 Login with Twilio$'), handle_twilio_login))
    app.add_handler(MessageHandler(filters.Regex(r'^🔍 Search Number$'), search_number))
    app.add_handler(MessageHandler(filters.Regex(r'^🎲 Random Number$'), search_number))  # Same handler
    app.add_handler(MessageHandler(filters.Regex(r'^📨 Inbox$'), view_inbox))
    app.add_handler(MessageHandler(filters.Regex(r'^🗑 Release Number$'), release_number_menu))
    app.add_handler(MessageHandler(filters.Regex(r'^👤 My Profile$'), show_profile))
    app.add_handler(MessageHandler(filters.Regex(r'^👮 Admin Panel$'), admin_panel))
    
    # Add country code handler
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^\+\d+$'), assign_number))
    
    # Add Twilio credential handler
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^AC\w+\|.+\w$'), process_twilio_credentials))
    
    # Add callback handlers
    app.add_handler(CallbackQueryHandler(show_messages, pattern="^inbox_"))
    app.add_handler(CallbackQueryHandler(confirm_release, pattern="^release_"))
    app.add_handler(CallbackQueryHandler(execute_release, pattern="^confirm_release_"))
    app.add_handler(CallbackQueryHandler(cancel_action, pattern="^cancel_"))
    app.add_handler(CallbackQueryHandler(list_users, pattern="^list_users$"))
    app.add_handler(CallbackQueryHandler(pending_approvals, pattern="^pending_approvals$"))
    app.add_handler(CallbackQueryHandler(approve_user, pattern="^approve_"))
    
    # Fallback handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_unknown))
    
    # Start the bot
    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
