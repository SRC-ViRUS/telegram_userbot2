from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
import asyncio, re

API_ID = 22494292
API_HASH = '0bd3915b6b1a0a64b168d0cc852a0e61'
BOT_TOKEN = '7768107017:AAH7ndo7wwLtRDRYLcTNC7ne7gWju3lDvtI'
OWNER_ID = 123456789  # ضع معرفك الرقمي من @userinfobot

bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
clients = {}  # {user_id: client}
watching_code = {}  # من ينتظر جلب الكود
session_active = {}  # الجلسة الحالية لكل مستخدم

# عرض الأزرار
def main_buttons():
    return [
        [Button.inline("📩 كود سيشن", b"send_session"), Button.inline("📬 جلب رمز", b"fetch_code")],
        [Button.inline("📥 آخر 5 رسائل", b"fetch_telegram")],
        [Button.inline("📖 قائمة الأوامر", b"help"), Button.inline("🚪 إنهاء الجلسة", b"logout")]
    ]

# ملاحظة: يراقب الكود التحقق 5 أرقام
async def watch_code_messages(client, user_id):
    @client.on(events.NewMessage(incoming=True))
    async def handler(event):
        msg = event.raw_text.strip()
        match = re.search(r"\b\d{5}\b", msg)
        if match:
            await bot.send_message(user_id, f"📨 تفضل الرمز:\n`{match.group(0)}`")

# أمر /start
@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.respond("👋 مرحباً بك! اختر من الأزرار:", buttons=main_buttons())

# الأزرار
@bot.on(events.CallbackQuery)
async def callback(event):
    uid = event.sender_id
    data = event.data.decode()

    if data == "send_session":
        await event.edit("📩 أرسل كود السيشن الآن:", buttons=main_buttons())

    elif data == "fetch_code":
        watching_code[uid] = True
        await event.edit("📬 أرسل كود السيشن لجلب رمز التحقق عند وصوله:", buttons=main_buttons())

    elif data == "fetch_telegram":
        if uid not in clients:
            await event.answer("❌ لا توجد جلسة حالياً.", alert=True)
            return
        try:
            tg_entity = None
            async for dialog in clients[uid].iter_dialogs():
                if dialog.entity.username == "Telegram":
                    tg_entity = dialog.entity
                    break
            if not tg_entity:
                await event.edit("❌ لا توجد محادثة مع Telegram.", buttons=main_buttons())
                return
            messages = []
            async for msg in clients[uid].iter_messages(tg_entity, limit=5):
                messages.append(msg.text or "[وسائط]")
            text = "\n\n".join(f"🔹 {m}" for m in reversed(messages))
            await event.edit(f"📥 آخر 5 رسائل من Telegram:\n\n{text}", buttons=main_buttons())
        except Exception as e:
            await event.edit(f"❌ خطأ أثناء الجلب: {e}", buttons=main_buttons())

    elif data == "logout":
        if uid in clients:
            await clients[uid].disconnect()
            del clients[uid]
        session_active.pop(uid, None)
        await event.edit("🚪 تم إنهاء الجلسة الحالية.", buttons=main_buttons())

    elif data == "help":
        msg = (
            "📖 **قائمة الأوامر:**\n\n"
            "• `📩 كود سيشن` – إرسال كود تسجيل دخول (StringSession)\n"
            "• `📬 جلب رمز` – يسجل الدخول ويراقب الكود (5 أرقام)\n"
            "• `📥 آخر 5 رسائل` – يجلب آخر 5 رسائل من Telegram الرسمي\n"
            "• `🚪 إنهاء الجلسة` – فصل الجلسة الحالية\n"
        )
        await event.edit(msg, buttons=main_buttons())

# استقبال كود سيشن
@bot.on(events.NewMessage)
async def receive_session(event):
    uid = event.sender_id
    txt = event.raw_text.strip()

    if uid != OWNER_ID:
        return

    if len(txt) > 50 and ' ' not in txt:
        try:
            # تسجيل الدخول
            client = TelegramClient(StringSession(txt), API_ID, API_HASH)
            await client.start()
            me = await client.get_me()

            # حذف الجلسة القديمة
            if uid in clients:
                await clients[uid].disconnect()

            clients[uid] = client
            session_active[uid] = me.id

            # إذا هو طالب رمز تحقق
            if watching_code.pop(uid, False):
                await watch_code_messages(client, uid)
                await event.respond(f"✅ تم الدخول: {me.first_name}\n📡 سيتم إرسال الرمز إذا وصل.")

            else:
                await event.respond(f"✅ تم تسجيل الدخول باسم: {me.first_name}", buttons=main_buttons())

        except Exception as e:
            watching_code.pop(uid, None)
            await event.respond(f"❌ فشل تسجيل الدخول:\n{e}", buttons=main_buttons())
