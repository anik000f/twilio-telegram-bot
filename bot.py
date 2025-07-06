import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

# ====== তোমার সেটিংস ======
BOT_TOKEN = "7561627181:AAGKJdb-8zBY021M68Q4ca-GcEWQurXMtaE"
ADMIN_ID = 6569537485  # numeric, string না
ALLOWED_USERS = [ADMIN_ID]  # এখানেই যাদের access দিতে চাও, তাদের ID বসাতে পারো

# ====== Start Command ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("❌ Sorry, you are not allowed to use this bot.")
        return

    keyboard = [["Buy Number", "View Numbers"], ["Delete Number", "Get OTP"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("✅ Welcome! Choose an option:", reply_markup=reply_markup)

# ====== Message Handler ======
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("❌ You are not authorized.")
        return

    text = update.message.text

    if text == "Buy Number":
        await update.message.reply_text("☎️ Buying new number... (Demo response)")
    elif text == "View Numbers":
        await update.message.reply_text("📄 Your numbers: [Demo list]")
    elif text == "Delete Number":
        await update.message.reply_text("🗑️ Deleting number... (Demo response)")
    elif text == "Get OTP":
        await update.message.reply_text("🔑 Your OTP: 123456 (Demo response)")
    else:
        await update.message.reply_text("⚠️ Unknown command.")

# ====== Main Function ======
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
