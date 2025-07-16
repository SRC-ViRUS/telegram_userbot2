from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
import asyncio

# إعدادات
API_ID = 22494292
API_HASH = '0bd3915b6b1a0a64b168d0cc852a0e61'
BOT_TOKEN = '7768107017:AAH7ndo7wwLtRDRYLcTNC7ne7gWju3lDvtI'
OWNER_ID = 7477836004  # رقمك من @userinfobot

bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
sessions = {}  # لتخزين الجلسة حسب المستخدم

# زر واحد
def main_buttons():
    return [[Button.inline("📥 جلب رسائل Telegram", b"fetch_telegram")]]

# بدء البوت
@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    if event.sender_id != OWNER_ID:
        return
    await event.respond("👋 مرحباً بك! اضغط الزر لجلب الرسائل من Telegram:", buttons=main_buttons())

# لما يضغط الزر
@bot.on(events.CallbackQuery)
async def callback(event):
    if event.sender_id != OWNER_ID:
        return
    if event.data == b"fetch_telegram":
        await event.respond("📩 أرسل كود السيشن الآن:")
        sessions[event.sender_id] = "awaiting_session"

# استقبال كود السيشن
@bot.on(events.NewMessage)
async def handle_session(event):
    uid = event.sender_id
    txt = event.raw_text.strip()

    if uid != OWNER_ID:
        return

    if sessions.get(uid) == "awaiting_session":
        if len(txt) < 50 or ' ' in txt:
            await event.reply("❌ كود سيشن غير صالح.")
            return
        try:
            client = TelegramClient(StringSession(txt), API_ID, API_HASH)
            await client.start()
            me = await client.get_me()
            await event.reply(f"✅ تم تسجيل الدخول: {me.first_name}\n⏳ جاري جلب آخر 10 رسائل من Telegram...")

            # البحث عن محادثة Telegram الرسمية
            tg = None
            async for dialog in client.iter_dialogs():
                if dialog.entity.username == "Telegram":
                    tg = dialog.entity
                    break

            if not tg:
                await event.reply("❌ لم يتم العثور على محادثة Telegram الرسمية.")
                await client.disconnect()
                return

            # جلب آخر 10 رسائل
            count = 0
            async for msg in client.iter_messages(tg, limit=10):
                text = msg.text or "[وسائط]"
                await event.reply(f"🔹 {text}")
                count += 1

            await event.reply(f"✅ تم إرسال {count} رسالة.")
            await client.disconnect()
            sessions.pop(uid)

        except Exception as e:
            await event.reply(f"❌ فشل: {e}")
            sessions.pop(uid, None)
