import asyncio
from telethon import TelegramClient, events, Button

API_ID = 22494292
API_HASH = '0bd3915b6b1a0a64b168d0cc852a0e61'
BOT_TOKEN = '7768107017:AAErNtQKYEvJVWN35osSlGNgW4xBq6NxSKs'
OWNER_ID = 7477836004  # غيّره إلى رقمك من @userinfobot

# إنشاء البوت مرة وحدة فقط
bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# أزرار الواجهة
def main_buttons():
    return [[Button.inline("📥 جلب رسائل Telegram", b"fetch_telegram")]]

# أمر /start
@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    if event.sender_id != OWNER_ID:
        return
    await event.respond("👋 مرحباً! اضغط الزر لجلب آخر 10 رسائل من Telegram الرسمي:", buttons=main_buttons())

# عند الضغط على الزر
@bot.on(events.CallbackQuery)
async def callback(event):
    if event.sender_id != OWNER_ID:
        return
    if event.data == b"fetch_telegram":
        await event.respond("⏳ جاري جلب آخر 10 رسائل من Telegram...")
        try:
            tg_entity = None
            async for dialog in bot.iter_dialogs():
                if dialog.entity.username == "Telegram":
                    tg_entity = dialog.entity
                    break
            if not tg_entity:
                await event.respond("❌ لم يتم العثور على محادثة Telegram الرسمية.", buttons=main_buttons())
                return
            messages = []
            async for msg in bot.iter_messages(tg_entity, limit=10):
                messages.append(msg.text or "[وسائط]")
            result = "\n\n".join(f"🔹 {m}" for m in reversed(messages))
            await event.respond(f"📥 آخر 10 رسائل من Telegram:\n\n{result}", buttons=main_buttons())
        except Exception as e:
            await event.respond(f"❌ فشل أثناء جلب الرسائل:\n{e}", buttons=main_buttons())

# تشغيل البوت داخل حلقة مراقبة
async def run_bot():
    while True:
        try:
            print("🚀 البوت بدأ ويعمل الآن!")
            await bot.run_until_disconnected()
        except Exception as e:
            print(f"❌ حدث خطأ: {e} | سيتم إعادة التشغيل بعد 5 ثوانٍ...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(run_bot())
