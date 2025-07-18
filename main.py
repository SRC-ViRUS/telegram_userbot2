import os
import asyncio
import tempfile
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession

API_ID = 22494292         # ضع API_ID الخاص بك هنا
API_HASH = "0bd3915b6b1a0a64b168d0cc852a0e61"  # ضع API_HASH الخاص بك هنا
BOT_TOKEN = "7768107017:AAErNtQKYEvJVWN35osSlGNgW4xBq6NxSKs"  # ضع توكن البوت هنا

# إعداد مجلدات التخزين
os.makedirs("sessions", exist_ok=True)
os.makedirs("media", exist_ok=True)

bot = TelegramClient("bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# تحميل الجلسات المحفوظة
user_clients = {}

async def load_sessions():
    for filename in os.listdir("sessions"):
        if filename.endswith(".session"):
            path = f"sessions/{filename}"
            client = TelegramClient(path, API_ID, API_HASH)
            await client.start()
            user_clients[client] = True
            print(f"✅ تم تشغيل الجلسة: {filename}")

@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    buttons = [
        [Button.inline("➕ إضافة جلسة جديدة", b"add_session")],
        [Button.inline("📤 إرسال رسالة", b"send_message")],
        [Button.inline("📤 إرسال بالتتابع كل 5 ثواني", b"send_message_slow")],
        [Button.inline("📋 عرض الجلسات", b"list_sessions")],
        [Button.inline("🗑️ مسح جميع الجلسات", b"clear_sessions")]
    ]
    await event.respond("👋 أهلاً بك! اختر الأمر:", buttons=buttons)
    await asyncio.sleep(30)
    await event.delete()

@bot.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode("utf-8")

    if data == "add_session":
        await event.edit("📥 أرسل لي StringSession الخاص بالحساب:")
        @bot.on(events.NewMessage(from_users=event.sender_id))
        async def get_session(ev):
            session_str = ev.raw_text.strip()
            # حفظ الجلسة في ملف
            try:
                client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
                await client.start()
                # حفظ في مجلد sessions
                filename = f"sessions/{ev.sender_id}.session"
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(session_str)
                user_clients[client] = True
                await ev.reply("✅ تم إضافة وتشغيل الجلسة.")
            except Exception as e:
                await ev.reply(f"❌ حدث خطأ: {e}")
            bot.remove_event_handler(get_session)
            await asyncio.sleep(3)
            await ev.delete()
        await event.delete()

    elif data == "send_message":
        await event.edit("✉️ أرسل نص الرسالة أو أرسل صورة/فيديو/ملصق للبوت.\n"
                         "عند إرسال صورة أو ملصق سأطلب منك إذا تريد الإرسال مؤقت أم عادي.")
        @bot.on(events.NewMessage(from_users=event.sender_id))
        async def get_message(ev):
            sender = ev.sender_id
            # تفقد نوع المحتوى
            media = None
            if ev.photo:
                media = await ev.download_media(file=f"media/{ev.id}.jpg")
            elif ev.video:
                media = await ev.download_media(file=f"media/{ev.id}.mp4")
            elif ev.sticker:
                media = await ev.download_media(file=f"media/{ev.id}.webp")
            text = ev.text or ""
            await ev.reply("هل تريد الإرسال: \n🔘 مؤقت (تحذف بعد 3 ثواني)\n🔘 عادي", buttons=[
                Button.inline("مؤقت", b"temp_send"),
                Button.inline("عادي", b"perm_send")
            ])

            @bot.on(events.CallbackQuery(data=b"temp_send"))
            async def temp_send(ev2):
                await send_all(ev.sender_id, text, media, temporary=True)
                await ev2.edit("✅ تم الإرسال المؤقت.")
                bot.remove_event_handler(temp_send)

            @bot.on(events.CallbackQuery(data=b"perm_send"))
            async def perm_send(ev2):
                await send_all(ev.sender_id, text, media, temporary=False)
                await ev2.edit("✅ تم الإرسال العادي.")
                bot.remove_event_handler(perm_send)

            bot.remove_event_handler(get_message)
            await asyncio.sleep(3)
            await ev.delete()
        await event.delete()

    elif data == "send_message_slow":
        # مماثل send_message لكن يرسل كل 5 ثواني من كل حساب
        await event.edit("✉️ أرسل نص الرسالة أو وسائط للإرسال بالتتابع (كل 5 ثواني).")
        # هنا تضيف كود مشابه للـsend_message مع تأخير 5 ثواني لكل جلسة
        await asyncio.sleep(3)
        await event.delete()

    elif data == "list_sessions":
        msg = "📋 الجلسات الحالية:\n"
        for client in user_clients.keys():
            me = await client.get_me()
            msg += f"- {me.first_name} (@{me.username or 'لا يوجد'})\n"
        await event.edit(msg)
        await asyncio.sleep(10)
        await event.delete()

    elif data == "clear_sessions":
        user_clients.clear()
        for file in os.listdir("sessions"):
            if file.endswith(".session"):
                os.remove(f"sessions/{file}")
        await event.edit("✅ تم مسح جميع الجلسات.")
        await asyncio.sleep(3)
        await event.delete()

async def send_all(user_id, text, media_path=None, temporary=False):
    count = 0
    for client in list(user_clients.keys()):
        try:
            me = await client.get_me()
            if media_path:
                msg = await client.send_file(user_id, media_path)
            else:
                msg = await client.send_message(user_id, text)
            count += 1
            if temporary:
                await asyncio.sleep(3)
                await msg.delete()
        except Exception as e:
            print(f"خطأ في حساب {me.id}: {e}")

if __name__ == "__main__":
    async def main():
        print("✅ تشغيل البوت...")
        await load_sessions()
        await bot.run_until_disconnected()
    asyncio.run(main())
