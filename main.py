# -*- coding: utf-8 -*-
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.tl.functions.account import DeleteAccountRequest

API_ID = 22494292           # غيّر إلى api_id مالك
API_HASH = "0bd3915b6b1a0a64b168d0cc852a0e61"     # غيّر إلى api_hash مالك
BOT_TOKEN = "توكن_البوت"7768107017:AAErNtQKYEvJVWN35osSlGNgW4xBq6NxSKs
bot = TelegramClient("bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
user_sessions = {}  # {user_id: TelegramClient instance}

def main_buttons():
    return [
        [Button.inline("📩 إرسال كود الجلسة", b"send_session")],
    ]

@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.respond("👋 مرحباً! أرسل كود الجلسة أو اضغط الزر:", buttons=main_buttons())

@bot.on(events.CallbackQuery(data=b"send_session"))
async def request_session(event):
    await event.edit("📩 أرسل كود الجلسة (StringSession) الخاص بك:")

@bot.on(events.NewMessage)
async def handle_session(event):
    user_id = event.sender_id
    text = event.raw_text.strip()

    # إذا نص طويل (كود سيشن)
    if len(text) > 50 and ' ' not in text:
        try:
            # إنشاء عميل جلسة المستخدم
            client = TelegramClient(StringSession(text), API_ID, API_HASH)
            await client.start()
            me = await client.get_me()

            # خزن الجلسة
            if user_id in user_sessions:
                await user_sessions[user_id].disconnect()
            user_sessions[user_id] = client

            # عرض زر حذف الحساب
            await event.respond(
                f"✅ تم تسجيل الدخول باسم {me.first_name}\n\n"
                "يمكنك الآن حذف الحساب نهائيًا بالضغط على الزر أدناه.",
                buttons=[Button.inline("🗑️ حذف الحساب نهائيًا", b"delete_account")]
            )
        except Exception as e:
            await event.respond(f"❌ فشل تسجيل الدخول: {e}")

@bot.on(events.CallbackQuery(data=b"delete_account"))
async def delete_account(event):
    user_id = event.sender_id
    if user_id not in user_sessions:
        await event.answer("❌ لا توجد جلسة مفعّلة.", alert=True)
        return

    client = user_sessions[user_id]
    try:
        await event.edit("⚠️ جاري حذف الحساب نهائيًا...")
        await client(DeleteAccountRequest(reason="تم الحذف بواسطة البوت"))
        await event.respond("✅ تم حذف الحساب نهائيًا. شكراً لاستخدامك البوت.")
        await client.disconnect()
        user_sessions.pop(user_id, None)
    except Exception as e:
        await event.edit(f"❌ حدث خطأ أثناء الحذف: {e}")

print("🚀 البوت يعمل الآن...")
bot.run_until_disconnected()
