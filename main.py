import json
import time
import asyncio
from telegram import Update, ChatPermissions
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ChatMemberHandler, CallbackContext
)

# Replace with your bot token
BOT_TOKEN = 'YOUR_BOT_TOKEN'

# Load invite tracker
try:
    with open("invite_tracker.json", "r") as f:
        invite_tracker = json.load(f)
except:
    invite_tracker = {}

async def restrict_user(chat_id, user_id, application):
    await application.bot.restrict_chat_member(
        chat_id, user_id,
        ChatPermissions(can_send_messages=False)
    )

async def allow_user(chat_id, user_id, application):
    await application.bot.restrict_chat_member(
        chat_id, user_id,
        ChatPermissions(can_send_messages=True)
    )

async def handle_new_members(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    new_members = update.message.new_chat_members
    inviter_id = update.message.from_user.id

    for member in new_members:
        # Track who invited whom
        if member.id != inviter_id:  # avoid self-invite
            if str(inviter_id) not in invite_tracker:
                invite_tracker[str(inviter_id)] = {"invited": [], "time": 0}
            if member.id not in invite_tracker[str(inviter_id)]["invited"]:
                invite_tracker[str(inviter_id)]["invited"].append(member.id)

    # Check if inviter invited at least 2
    invited = invite_tracker[str(inviter_id)]["invited"]
    if len(invited) >= 2 and invite_tracker[str(inviter_id)]["time"] == 0:
        await allow_user(chat_id, inviter_id, context.application)
        invite_tracker[str(inviter_id)]["time"] = time.time()
        await context.bot.send_message(chat_id, f"<a href='tg://user?id={inviter_id}'>You</a> can now send messages for 24 hours!", parse_mode='HTML')

    with open("invite_tracker.json", "w") as f:
        json.dump(invite_tracker, f)

async def check_expiry(application):
    while True:
        now = time.time()
        for user_id, data in invite_tracker.items():
            if data["time"] > 0 and now - data["time"] > 86400:
                chat_id = YOUR_GROUP_CHAT_ID  # Replace this!
                await restrict_user(chat_id, int(user_id), application)
                data["time"] = 0
                data["invited"] = []
        with open("invite_tracker.json", "w") as f:
            json.dump(invite_tracker, f)
        await asyncio.sleep(60)  # Check every 60 seconds

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("I'm active in the group!")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(ChatMemberHandler(handle_new_members, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(CommandHandler("check", lambda u, c: check_expiry(app)))

    app.run_polling()

if __name__ == "__main__":
    asyncio.run(check_expiry(ApplicationBuilder().token(BOT_TOKEN).build()))
    main()
