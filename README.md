# Twilio Telegram Bot (with Admin Control)

## Setup

1. Deploy to Railway or any server.
2. Add these Environment Variables if using Twilio:
   - TWILIO_ACCOUNT_SID
   - TWILIO_AUTH_TOKEN

## Commands

- /start — Start the bot (only allowed users)
- /allow <user_id> — Allow new user (admin only)
- /block <user_id> — Block user (admin only)
- /list_users — List allowed users (admin only)