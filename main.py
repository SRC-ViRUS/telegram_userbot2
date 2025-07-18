import asyncio
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession

BOT_TOKEN = "7768107017:AAErNtQKYEvJVWN35osSlGNgW4xBq6NxSKs"
API_ID = 22494292  # بدلها برقمك
API_HASH = "0bd3915b6b1a0a64b168d0cc852a0e61"

bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

user_sessions = {}  # dict: {session_string: TelegramClient instance}

# أوامر زرية رئيسية
@bot.on(events.NewMessage(pattern='/menu'))
async def menu(event):
    buttons = [
        [Button.inline("➕ إضافة جلسة", b'add')],
        [Button.inline("📋 عرض الجلسات", b'list')],
        [Button.inline("📤 إرسال رسالة للجميع", b'send')],
        [Button.inline("🗑️ مسح جميع الجلسات", b'clear')],
    ]
    await event.reply("اختر أمر:", buttons=buttons)

# تعامل مع نقرات الأزرار
@bot.on(events.CallbackQuery)
async def callback(event):
    data = event.data.decode('utf-8')

    if data == 'add':
        await event.edit("أرسل لي StringSession الخاص بالجلسة الجديدة:")
        @bot.on(events.NewMessage(from_users=event.sender_id))
        async def get_session(event2):
            session_str = event2.raw_text.strip()
            if session_str in user_sessions:
                await event2.reply("هذه الجلسة موجودة مسبقًا.")
            else:
                try:
                    client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
                    await client.start()
                    user_sessions[session_str] = client
                    await event2.reply("تم إضافة الجلسة وتشغيلها بنجاح.")
                except Exception as e:
                    await event2.reply(f"خطأ في تشغيل الجلسة: {e}")
            bot.remove_event_handler(get_session)
    elif data == 'list':
        if not user_sessions:
            await event.edit("لا توجد جلسات مضافة حالياً.")
        else:
            text = "الجلسات المضافة:\n"
            for i, sess in enumerate(user_sessions.keys(), 1):
                text += f"{i}. {sess[:20]}...\n"
            await event.edit(text)
    elif data == 'send':
        await event.edit("أرسل لي نص الرسالة التي تريد إرسالها لجميع الجلسات:")
        @bot.on(events.NewMessage(from_users=event.sender_id))
        async def get_msg(event3):
            msg = event3.raw_text.strip()
            count, errors = 0, 0
            for client in user_sessions.values():
                try:
                    me = await client.get_me()
                    await client.send_message(me.id, msg)
                    count += 1
                except Exception:
                    errors += 1
            await event3.reply(f"تم إرسال الرسالة إلى {count} جلسة.\nالأخطاء: {errors}")
            bot.remove_event_handler(get_msg)
    elif data == 'clear':
        for client in user_sessions.values():
            await client.disconnect()
        user_sessions.clear()
        await event.edit("تم مسح جميع الجلسات.")

async def main():
    print("تشغيل البوت...")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
