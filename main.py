import os
import asyncio
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession

API_ID = 22494292
API_HASH = "0bd3915b6b1a0a64b168d0cc852a0e61"
BOT_TOKEN = "7768107017:AAErNtQKYEvJVWN35osSlGNgW4xBq6NxSKs"

SESSIONS_FILE = "sessions.txt"
user_clients = {}
user_states = {}

# تحميل الجلسات من ملف
def load_sessions():
    if os.path.exists(SESSIONS_FILE):
        with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    return []

# حفظ جلسة جديدة
def save_session(sess_str):
    sessions = load_sessions()
    if sess_str not in sessions:
        with open(SESSIONS_FILE, "a", encoding="utf-8") as f:
            f.write(sess_str + "\n")

# تشغيل جميع الجلسات
async def start_all_sessions():
    for sess in load_sessions():
        try:
            client = TelegramClient(StringSession(sess), API_ID, API_HASH)
            await client.start()
            user_clients[client] = True
            print("✅ جلسة شغالة")
        except Exception as e:
            print(f"❌ خطأ في تشغيل جلسة: {e}")

# إنشاء البوت
bot = TelegramClient("bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# أمر /start يعرض قائمة الأوامر
@bot.on(events.NewMessage(pattern="/start"))
async def show_menu(event):
    buttons = [
        [Button.inline("➕ إضافة جلسة", b"add")],
        [Button.inline("📤 إرسال رسالة", b"send")],
        [Button.inline("📋 عرض الجلسات", b"list")],
        [Button.inline("🗑️ حذف الكل", b"clear")],
    ]
    await event.respond("👋 مرحباً بك، اختر من الأوامر:", buttons=buttons)

# زر يتم الضغط عليه
@bot.on(events.CallbackQuery)
async def on_button(event):
    user_id = event.sender_id
    data = event.data.decode()

    if data == "add":
        user_states[user_id] = "await_session"
        await event.respond("📥 أرسل StringSession الآن.")
    
    elif data == "send":
        user_states[user_id] = "await_broadcast"
        await event.respond("✉️ أرسل نص الرسالة الآن.")
    
    elif data == "list":
        sessions = load_sessions()
        if not sessions:
            await event.respond("⚠️ لا توجد جلسات حالياً.")
        else:
            msg = "📋 الجلسات:\n"
            for i, s in enumerate(sessions, 1):
                msg += f"{i}. {s[:20]}...\n"
            await event.respond(msg)
    
    elif data == "clear":
        user_clients.clear()
        if os.path.exists(SESSIONS_FILE):
            os.remove(SESSIONS_FILE)
        await event.respond("✅ تم حذف كل الجلسات.")

# استقبال نصوص الجلسات أو الرسائل
@bot.on(events.NewMessage)
async def handle_text(event):
    user_id = event.sender_id
    state = user_states.get(user_id)
    text = event.raw_text.strip()

    if state == "await_session":
        try:
            save_session(text)
            client = TelegramClient(StringSession(text), API_ID, API_HASH)
            await client.start()
            user_clients[client] = True
            await event.reply("✅ تم إضافة الجلسة بنجاح.")
        except Exception as e:
            await event.reply(f"❌ خطأ: {e}")
        user_states.pop(user_id, None)

    elif state == "await_broadcast":
        count, errors = 0, 0
        for client in list(user_clients.keys()):
            try:
                me = await client.get_me()
                await client.send_message(me.id, text)
                count += 1
            except Exception as e:
                print(f"❌ فشل في {me.id}: {e}")
                errors += 1
        await event.reply(f"📤 تم الإرسال إلى {count} جلسة.\n❌ أخطاء: {errors}")
        user_states.pop(user_id, None)

# تشغيل البوت
async def main():
    print("✅ تشغيل البوت...")
    await start_all_sessions()
    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
