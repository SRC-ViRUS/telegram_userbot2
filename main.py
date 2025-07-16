# -*- coding: utf-8 -*-
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
import re, asyncio

# إعدادات البوت
API_ID = 22494292
API_HASH = '0bd3915b6b1a0a64b168d0cc852a0e61'
BOT_TOKEN = '7768107017:AAH7ndo7wwLtRDRYLcTNC7ne7gWju3lDvtI'
OWNER_ID = 123456789  # ← ضع معرفك الرقمي (مثلاً من @userinfobot)

# إنشاء البوت
bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# قاعدة الجلسات
user_clients = {}             # {user_id: {session_id: client}}
active_session = {}           # {user_id: session_id}
waiting_for_code = set()      # من ينتظر جلسة من زر "جلب الرسالة"

# زر الواجهة
def main_buttons():
    return [
        [Button.inline("📩 إرسال كود سيشن", b"send_session"), Button.inline("📬 جلب الرسالة", b"fetch_code")],
        [Button.inline("📋 الجلسات", b"list_sessions"), Button.inline("🚪 إنهاء الجلسات الأخرى", b"logout_all")]
    ]

# يراقب وصول رمز تحقق 5 أرقام
async def watch_code(client, uid):
    @client.on(events.NewMessage(incoming=True))
    async def handler(event):
        text = event.raw_text.strip()
        if re.fullmatch(r"\d{5}", text):
            await bot.send_message(uid, f"📨 تفضل الرمز:\n`{text}`")

# أمر /start
@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.respond("👋 أهلاً بك!\nاختر من الأزرار:", buttons=main_buttons())

# التعامل مع الأزرار
@bot.on(events.CallbackQuery)
async def callback(event):
    uid = event.sender_id
    data = event.data.decode()

    if data == "send_session":
        await event.edit("📩 أرسل كود السيشن الآن لتسجيل الدخول:", buttons=main_buttons())

    elif data == "fetch_code":
        waiting_for_code.add(uid)
        await event.edit("📬 أرسل كود السيشن الآن، وسأنتظر تسجيل الدخول ثم أرسل لك الرمز عند وصوله.", buttons=main_buttons())

    elif data == "list_sessions":
        if uid not in user_clients or not user_clients[uid]:
            await event.edit("⚠️ لا توجد جلسات حالياً.", buttons=main_buttons())
            return
        msg = "📋 الجلسات:\n\n"
        for sid, cl in user_clients[uid].items():
            try:
                me = await cl.get_me()
                name = me.first_name or me.username or "مجهول"
                mark = "✅" if active_session.get(uid) == sid else ""
                msg += f"{mark} • {name} - {sid}\n"
            except:
                continue
        await event.edit(msg.strip(), buttons=main_buttons())

    elif data == "logout_all":
        if uid in user_clients:
            for cl in user_clients[uid].values():
                await cl.disconnect()
            user_clients[uid] = {}
            active_session.pop(uid, None)
            await event.edit("✅ تم إنهاء جميع الجلسات.", buttons=main_buttons())
        else:
            await event.edit("⚠️ لا توجد جلسات.", buttons=main_buttons())

# استقبال كود السيشن
@bot.on(events.NewMessage)
async def handle(event):
    uid = event.sender_id
    txt = event.raw_text.strip()

    if len(txt) > 50 and ' ' not in txt:
        try:
            # تسجيل الدخول بجلسة جديدة
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

            # إذا تم طلب جلب رسالة → مراقبة الرمز
            if uid in waiting_for_code:
                await watch_code(client, uid)
                waiting_for_code.remove(uid)
                await event.respond(f"✅ تم تسجيل الدخول باسم {me.first_name}.\n⏳ سأرسل لك الرمز عند وصوله.", buttons=main_buttons())
            else:
                await event.respond(f"✅ تم تسجيل الدخول باسم {me.first_name}.", buttons=main_buttons())

        except Exception as e:
            if uid in waiting_for_code:
                waiting_for_code.remove(uid)
            await event.respond(f"❌ فشل تسجيل الدخول:\n{e}", buttons=main_buttons())

# تشغيل البوت
bot.run_until_disconnected()
