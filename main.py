import json
import time
import asyncio
from telegram import Update, ChatPermissions
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ChatMemberHandler,
    CallbackContext, MessageHandler, filters
)

BOT_TOKEN = "YOUR_BOT_TOKEN"  # <-- Replace this with your token

# Load or initialize tracking file
try:
    with open("invite_tracker.json", "r") as f:
        invite_tracker = json.load(f)
except:
    invite_tracker = {}

async def restrict_user(group_id, user_id, app):
    await app.bot.restrict_chat_member(
        group_id, user_id,
        ChatPermissions(can_send_messages=False)
    )

async def allow_user(group_id, user_id, app):
    await app.bot.restrict_chat_member(
        group_id, user_id,
        ChatPermissions(can_send_messages=True)
    )

# When new members are added
async def handle_new_members(update: Update, context: CallbackContext):
    group_id = update.effective_chat.id
    inviter = update.message.from_user
    new_members = update.message.new_chat_members

    for member in new_members:
        # Send welcome message to new member
        await context.bot.send_message(
            chat_id=group_id,
            text=f"👋 Welcome <a href='tg://user?id={member.id}'>{member.first_name}</a>!\nPlease add 2 people for message in our group.",
            parse_mode='HTML'
        )

        # Track inviter's invited list
        if member.id != inviter.id:
            uid = str(inviter.id)
            if uid not in invite_tracker:
                invite_tracker[uid] = {
                    "invited": [],
                    "time": 0,
                    "group_id": group_id
                }
            if member.id not in invite_tracker[uid]["invited"]:
                invite_tracker[uid]["invited"].append(member.id)

    # Allow messaging if 2 invited
    uid = str(inviter.id)
    if uid in invite_tracker:
        if len(invite_tracker[uid]["invited"]) >= 2 and invite_tracker[uid]["time"] == 0:
            await allow_user(group_id, inviter.id, context.application)
            invite_tracker[uid]["time"] = time.time()
            await context.bot.send_message(
                group_id,
                f"<a href='tg://user?id={inviter.id}'>{inviter.first_name}</a> can now message for 24 hours!",
                parse_mode='HTML'
            )

    with open("invite_tracker.json", "w") as f:
        json.dump(invite_tracker, f)

# Background task to check 24-hour limit
async def check_expiry(app):
    while True:
        now = time.time()
        for uid, data in invite_tracker.items():
            if data["time"] > 0 and now - data["time"] > 86400:
                try:
                    await restrict_user(data["group_id"], int(uid), app)
                    data["time"] = 0
                    data["invited"] = []
                    print(f"Muted user {uid}")
                except Exception as e:
                    print(f"Error muting {uid}: {e}")
        with open("invite_tracker.json", "w") as f:
            json.dump(invite_tracker, f)
        await asyncio.sleep(60)

# Command to start the bot
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("🤖 Bot is active and monitoring invites!")

# Main function
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(ChatMemberHandler(handle_new_members, ChatMemberHandler.CHAT_MEMBER))

    asyncio.create_task(check_expiry(app))
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
