import asyncio
import os
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession

BOT_TOKEN = "7768107017:AAErNtQKYEvJVWN35osSlGNgW4xBq6NxSKs"
API_ID = 22494292
API_HASH = "0bd3915b6b1a0a64b168d0cc852a0e61"

SESSIONS_FILE = "sessions.txt"

def load_sessions():
    sessions = []
    if os.path.exists(SESSIONS_FILE):
        with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
            sessions = [line.strip() for line in f if line.strip()]
    return sessions

def save_session(session_str):
    with open(SESSIONS_FILE, "a", encoding="utf-8") as f:
        f.write(session_str + "\n")

user_clients = {}

bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

async def start_all_sessions():
    sessions = load_sessions()
    for i, sess in enumerate(sessions, 1):
        client = TelegramClient(StringSession(sess), API_ID, API_HASH)
        await client.start()
        user_clients[client] = True
        print(f"تم تشغيل جلسة رقم {i}")

async def send_message_all(text, event):
    count = 0
    errors = 0
    for client in list(user_clients.keys()):
        try:
            me = await client.get_me()
            await client.send_message(me.id, text)
            count += 1
        except Exception as e:
            errors += 1
            print(f"خطأ في حساب {me.id}: {e}")
    await event.edit(f"تم إرسال الرسالة إلى {count} حساب.\nالأخطاء: {errors}")
    await asyncio.sleep(3)
    await event.delete()

async def delete_message_later(event, delay=3):
    await asyncio.sleep(delay)
    try:
        await event.delete()
    except:
        pass

# عرض القائمة مع أزرار
@bot.on(events.NewMessage(pattern=r"^/menu$"))
async def menu_handler(event):
    buttons = [
        [Button.inline("➕ إضافة جلسة", b"add_session")],
        [Button.inline("📤 إرسال رسالة للجميع", b"send_all")],
        [Button.inline("🗑️ مسح جميع الجلسات", b"clear_sessions")],
        [Button.inline("📋 عرض الجلسات", b"list_sessions")],
    ]
    await event.respond("اختر أمر من القائمة:", buttons=buttons)
    await asyncio.sleep(30)
    await event.delete()

@bot.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode("utf-8")

    if data == "add_session":
        await event.edit("📥 أرسل لي الـ StringSession الخاص بالحساب.")
        @bot.on(events.NewMessage(from_users=event.sender_id))
        async def get_session(event2):
            session_str = event2.raw_text.strip()
            save_session(session_str)
            client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
            await client.start()
            user_clients[client] = True
            await event2.reply("✅ تم إضافة وتشغيل الجلسة الجديدة.")
            await asyncio.sleep(3)
            await event2.delete()
            bot.remove_event_handler(get_session)
        await event.delete()

    elif data == "send_all":
        await event.edit("✉️ أرسل لي نص الرسالة التي تريد إرسالها لجميع الحسابات.")
        @bot.on(events.NewMessage(from_users=event.sender_id))
        async def get_text(event2):
            text = event2.raw_text.strip()
            if not text:
                await event2.reply("❌ النص فارغ. حاول مرة أخرى.")
                await asyncio.sleep(3)
                await event2.delete()
                return
            await send_message_all(text, event2)
            bot.remove_event_handler(get_text)
        await event.delete()

    elif data == "clear_sessions":
        user_clients.clear()
        if os.path.exists(SESSIONS_FILE):
            os.remove(SESSIONS_FILE)
        await event.edit("✅ تم حذف جميع الجلسات.")
        await asyncio.sleep(3)
        await event.delete()

    elif data == "list_sessions":
        sessions = load_sessions()
        if not sessions:
            await event.edit("⚠️ لا توجد جلسات حالياً.")
        else:
            msg = "📋 قائمة الجلسات:\n"
            for i, sess in enumerate(sessions, 1):
                msg += f"{i}. {sess[:20]}... (مخفف)\n"
            await event.edit(msg)
        await asyncio.sleep(10)
        await event.delete()

async def main():
    print("تشغيل البوت...")
    await start_all_sessions()
    print("تم تشغيل جميع الجلسات.")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
