# -*- coding: utf-8 -*-
"""
بوت Telegram لجلب رسائل 777000 عبر StringSession
المطور: الصعب
"""

import logging, asyncio
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession

# إعداد التوكن
BOT_TOKEN = "7768107017:AAErNtQKYEvJVWN35osSlGNgW4xBq6NxSKs"
API_ID = 22494292    # غيره حسب حسابك
API_HASH = "0bd3915b6b1a0a64b168d0cc852a0e61"

logging.basicConfig(level=logging.INFO)
bot = TelegramClient("bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# قائمة الانتظار للجلسات
user_sessions = {}

# عند بدء /start
@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.respond(
        "مرحباً بك في بوت جلب الرسائل 👋\n\nاضغط الزر أدناه لإرسال كود الجلسة.",
        buttons=[Button.inline("📩 جلب الرسائل", b"get_messages")]
    )

# عند الضغط على الزر
@bot.on(events.CallbackQuery(data=b"get_messages"))
async def ask_session(event):
    await event.respond("أرسل الآن كود الجلسة `StringSession` الخاص بك:")
    user_sessions[event.sender_id] = {"step": "awaiting_session"}

# عندما يرسل المستخدم كود الجلسة
@bot.on(events.NewMessage)
async def handle_messages(event):
    user_id = event.sender_id
    if user_id in user_sessions and user_sessions[user_id]["step"] == "awaiting_session":
        session_str = event.raw_text.strip()
        try:
            await event.respond("📡 جاري تسجيل الدخول...")
            client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
            await client.connect()

            if not await client.is_user_authorized():
                await event.respond("❌ فشل تسجيل الدخول. تأكد أن الكود صالح.")
                return

            await event.respond("✅ تم تسجيل الدخول. جاري جلب الرسائل من 777000...")
            messages = await client.get_messages(777000, limit=10)

            if not messages:
                await event.respond("❗ لا توجد رسائل.")
            else:
                for msg in reversed(messages):
                    if msg.message:
                        await event.respond(f"📨 {msg.message}")

            await client.disconnect()

        except Exception as e:
            await event.respond(f"حدث خطأ: {e}")
        finally:
            user_sessions.pop(user_id, None)

# تشغيل البوت
print("🚀 البوت يعمل الآن.")
bot.run_until_disconnected()
