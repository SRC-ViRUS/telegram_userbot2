import os
import asyncio
import nest_asyncio
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession

# إعدادات البوت
API_ID = 22494292
API_HASH = "0bd3915b6b1a0a64b168d0cc852a0e61"
BOT_TOKEN = "توكن_بوتك"

# ملف تخزين الجلسات
SESSIONS_FILE = "sessions.txt"

# الجلسات و الحالات
user_clients = {}
user_states = {}

# تحميل الجلسات من الملف
def load_sessions():
    if os.path.exists(SESSIONS_FILE):
        with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    return []

# حفظ جلسة جديدة
def save_session(sess_str):
    if sess_str not in load_sessions():
        with open(SESSIONS_FILE, "a", encoding="utf-8") as f:
            f.write(sess_str + "\n")

# تشغيل كل الجلسات من الملف
async def start_all_sessions():
    for sess in load_sessions():
        try:
            client = TelegramClient(StringSession(sess), API_ID, API_HASH)
            await client.start()
            user_clients[client] = True
            print("✅ جلسة شغالة")
        except Exception as e:
            print(f"❌ خطأ في تشغيل جلسة: {e}")

# تشغيل بوت التوكن
bot = TelegramClient("bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# أمر /start يعرض القائمة
@bot.on(events.NewMessage(pattern="/start"))
async def show_menu(event):
    buttons = [
        [Button.inline("➕ إضافة جلسة", b"add")],
        [Button.inline("📤 إرسال رسالة", b"send")],
        [Button.inline("📋 عرض الجلسات", b"list")],
        [Button.inline("🗑️ حذف الكل", b"clear")],
    ]
    await event.respond("👋 مرحباً بك، اختر من القائمة:", buttons=buttons)

# أزرار التفاعل
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
        await event.respond("✅ تم حذف جميع الجلسات.")

# استقبال الجلسات أو الرسائل حسب الحالة
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
            await event.reply(f"❌ خطأ أثناء التشغيل: {e}")
        user_states.pop(user_id, None)

    elif state == "await_broadcast":
        count, errors = 0, 0
        for client in list(user_clients.keys()):
            try:
                me = await client.get_me()
                await client.send_message(me.id, text)
                count += 1
            except Exception as e:
                print(f"❌ فشل الإرسال إلى {me.id}: {e}")
                errors += 1
        await event.reply(f"📤 تم إرسال الرسالة إلى {count} جلسة.\n❌ أخطاء: {errors}")
        user_states.pop(user_id, None)

# main loop
async def main():
    print("✅ البوت يعمل الآن...")
    await start_all_sessions()
    await bot.run_until_disconnected()

# إصلاح asyncio loop
if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(main())
