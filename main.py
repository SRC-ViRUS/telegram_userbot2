# -*- coding: utf-8 -*-
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
import re, asyncio

API_ID = 22494292
API_HASH = '0bd3915b6b1a0a64b168d0cc852a0e61'
BOT_TOKEN = '7768107017:AAH7ndo7wwLtRDRYLcTNC7ne7gWju3lDvtI'
OWNER_ID = 123456789  # معرفك الرقمي

bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

user_clients = {}
active_session = {}

# حالة انتظار كود السيشن لجلب الرسالة
waiting_for_session_code = set()

def main_buttons():
    return [
        [Button.inline("📩 إرسال كود سيشن", b"send_session"), Button.inline("📬 جلب الرسالة", b"fetch_code")],
        [Button.inline("📋 الجلسات", b"list_sessions"), Button.inline("🚪 إنهاء الجلسات الأخرى", b"logout_all")]
    ]

async def watch_2fa_code(client, user_id):
    @client.on(events.NewMessage(incoming=True))
    async def handler(event):
        text = event.raw_text
        if re.fullmatch(r"\d{5}", text):
            await bot.send_message(user_id, f"📨 تفضل الرمز:\n`{text}`")

@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.respond("👋 أهلاً! اختر من الأزرار:", buttons=main_buttons())

@bot.on(events.CallbackQuery)
async def callback(event):
    uid = event.sender_id
    data = event.data.decode()

    if data == "send_session":
        await event.edit("📩 أرسل كود السيشن الخاص بك الآن:", buttons=main_buttons())

    elif data == "fetch_code":
        waiting_for_session_code.add(uid)
        await event.edit("📬 أرسل كود السيشن الآن، انتظر تسجيل الدخول...")

    elif data == "list_sessions":
        if uid not in user_clients or not user_clients[uid]:
            await event.edit("⚠️ لا توجد جلسات حالياً.", buttons=main_buttons())
            return
        msg = "📋 جلساتك:\n\n"
        for sid, cl in user_clients[uid].items():
            me = await cl.get_me()
            name = me.first_name or me.username or "بدون اسم"
            active = "✅" if active_session.get(uid) == sid else ""
            msg += f"{active} • {name} - {sid}\n"
        await event.edit(msg, buttons=main_buttons())

    elif data == "logout_all":
        if uid in user_clients:
            for sid, cl in user_clients[uid].values():
                await cl.disconnect()
            user_clients[uid] = {}
            active_session.pop(uid, None)
            await event.edit("✅ تم إنهاء جميع الجلسات.", buttons=main_buttons())
        else:
            await event.answer("⚠️ لا توجد جلسات.", alert=True)

@bot.on(events.NewMessage)
async def handle(event):
    uid = event.sender_id
    txt = event.text.strip()

    # استقبال كود السيشن من زر "جلب الرسالة"
    if uid in waiting_for_session_code:
        try:
            client = TelegramClient(StringSession(txt), API_ID, API_HASH)
            await client.start()
            me = await client.get_me()
            sid = str(me.id)

            # حذف الجلسات القديمة لهذا المستخدم
            if uid in user_clients:
                for cl in user_clients[uid].values():
                    await cl.disconnect()
            user_clients[uid] = {sid: client}
            active_session[uid] = sid

            # تشغيل مراقب رمز التحقق الذي يرسل رسالة للـ user_id نفسه
            await watch_2fa_code(client, uid)

            await event.respond(f"✅ تم تسجيل الدخول باسم {me.first_name}. انتظر رمز التحقق عند وصوله.", buttons=main_buttons())
        except Exception as e:
            await event.respond(f"❌ حدث خطأ: {e}", buttons=main_buttons())
        waiting_for_session_code.remove(uid)
        return

    # استقبال StringSession عادي (غير متعلق بجلب رسالة)
    if len(txt) > 50 and ' ' not in txt:
        try:
            client = TelegramClient(StringSession(txt), API_ID, API_HASH)
            await client.start()
            me = await client.get_me()
            sid = str(me.id)

            # حذف الجلسات القديمة
            if uid in user_clients:
                for cl in user_clients[uid].values():
                    await cl.disconnect()
            user_clients[uid] = {sid: client}
            active_session[uid] = sid

            await event.respond(f"✅ تم تسجيل الدخول باسم {me.first_name}", buttons=main_buttons())
        except Exception as e:
            await event.respond(f"❌ حدث خطأ: {e}", buttons=main_buttons())
