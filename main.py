from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
import asyncio

API_ID = 22494292
API_HASH = '0bd3915b6b1a0a64b168d0cc852a0e61'
BOT_TOKEN = '7768107017:AAH7ndo7wwLtRDRYLcTNC7ne7gWju3lDvtI'
OWNER_ID = 123456789  # ضع معرفك الرقمي (من @userinfobot)

bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.respond("👋 أهلاً بك، أرسل كود السيشن الآن للحصول على آخر 5 رسائل من Telegram.")

@bot.on(events.NewMessage)
async def handle(event):
    if event.sender_id != OWNER_ID:
        return  # تجاهل أي شخص غيرك

    session_str = event.raw_text.strip()

    if len(session_str) < 50 or ' ' in session_str:
        await event.reply("❌ هذا ليس كود سيشن صالح.")
        return

    try:
        user_client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
        await user_client.start()
        me = await user_client.get_me()

        await event.reply(f"✅ تم تسجيل الدخول إلى {me.first_name}. جاري جلب آخر 5 رسائل...")

        # البحث عن "Telegram" كمُرسل
        async for dialog in user_client.iter_dialogs():
            if dialog.entity.username == "Telegram":
                telegram_entity = dialog.entity
                break
        else:
            await event.reply("❌ لم يتم العثور على محادثة مع Telegram.")
            return

        # جلب آخر 5 رسائل
        messages = []
        async for msg in user_client.iter_messages(telegram_entity, limit=5):
            messages.append(msg.text or "[وسائط]")

        result = "\n\n".join(f"🔹 {m}" for m in reversed(messages))
        await event.reply(f"📨 آخر 5 رسائل من Telegram:\n\n{result}")

        await user_client.disconnect()

    except Exception as e:
        await event.reply(f"❌ خطأ: {e}")
