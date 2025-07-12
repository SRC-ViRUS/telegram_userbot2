import asyncio
import json
import os
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.errors import UserAlreadyParticipantError

# بيانات الاتصال
api_id = 20507759
api_hash = "225d3a24d84c637b3b816d13cc7bd766"
bot_token = "7644214767:AAGOlYEiyF6yFWxiIX_jlwo9Ssj_Cb95oLU"

# تحميل الجلسات من ملف
if os.path.exists("sessions.json"):
    with open("sessions.json", "r") as f:
        sessions = json.load(f)
else:
    sessions = {}

# تعريف المتغيرات العامة
clients = {}
current_chat = None
bot = TelegramClient("bot", api_id, api_hash)

# تشغيل كل الجلسات
async def start_all_sessions():
    for name, string in sessions.items():
        try:
            client = TelegramClient(StringSession(string), api_id, api_hash)
            await client.start()
            clients[name] = client
            print(f"✅ Session started: {name}")
        except Exception as e:
            print(f"❌ Failed to start session {name}: {e}")

# أزرار الواجهة
def get_main_buttons():
    return [
        [Button.inline("🚀 صعود الاتصال", b"connect")],
        [Button.inline("🛑 نزول الاتصال", b"disconnect")]
    ]

# بدء البوت
@bot.on(events.NewMessage(pattern="/start"))
async def start_handler(event):
    await event.respond("👋 أهلاً بك، استخدم الأزرار التالية للتحكم:", buttons=get_main_buttons())

# زر صعود الاتصال
@bot.on(events.CallbackQuery(data=b"connect"))
async def connect_button(event):
    await event.answer()
    await event.edit("📨 أرسل الآن رابط الكروب أو رابط الاتصال:")

    try:
        msg = await bot.wait_for(events.NewMessage(from_users=event.sender_id), timeout=60)
        link = msg.raw_text.strip()

        try:
            if "joinchat" in link or "+" in link:
                hash_part = link.split("+")[-1]
                result = await bot(ImportChatInviteRequest(hash_part))
                entity = result.chats[0]
            else:
                entity = await bot.get_entity(link)
        except Exception as e:
            await event.respond(f"❌ فشل في قراءة الرابط: {e}", buttons=get_main_buttons())
            return

        global current_chat
        current_chat = entity

        await event.respond("🔁 جاري صعود الحسابات واحداً تلو الآخر...")

        for name, client in clients.items():
            try:
                await client(JoinChannelRequest(entity))
                await asyncio.sleep(1)
                await event.respond(f"✅ [{name}] انضم وصعد الاتصال")
            except UserAlreadyParticipantError:
                await event.respond(f"✅ [{name}] موجود مسبقاً وصعد الاتصال")
            except Exception as e:
                await event.respond(f"❌ [{name}] خطأ: {e}")

        await event.respond("✅ تم صعود جميع الحسابات!", buttons=get_main_buttons())

    except asyncio.TimeoutError:
        await event.respond("⏰ انتهى الوقت. أعد المحاولة.", buttons=get_main_buttons())

# زر نزول الاتصال
@bot.on(events.CallbackQuery(data=b"disconnect"))
async def disconnect_button(event):
    await event.answer()

    if not current_chat:
        await event.edit("⚠️ لم يتم تحديد كروب بعد. اضغط صعود أولاً.", buttons=get_main_buttons())
        return

    await event.edit("🔁 جاري نزول الحسابات من الكروب...")

    for name, client in clients.items():
        try:
            await client(LeaveChannelRequest(current_chat))
            await asyncio.sleep(1)
            await event.respond(f"⬇️ [{name}] خرج من الكروب")
        except Exception as e:
            await event.respond(f"❌ [{name}] خطأ: {e}")

    await event.respond("✅ تم نزول جميع الحسابات!", buttons=get_main_buttons())

# تشغيل البوت
async def main():
    await bot.start(bot_token=bot_token)
    await start_all_sessions()
    print("✅ البوت يعمل الآن...")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
