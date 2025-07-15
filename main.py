from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.tl.functions.account import UpdateProfileRequest, UpdateUsernameRequest
from telethon.errors import SessionPasswordNeededError

API_ID = 22494292
API_HASH = '0bd3915b6b1a0a64b168d0cc852a0e61'
BOT_TOKEN = '7768107017:AAH7ndo7wwLtRDRYLcTNC7ne7gWju3lDvtI'

bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
user_clients = {}

def main_buttons():
    return [
        [Button.inline("أرسل StringSession", b"send_session")],
        [Button.inline("عرض رقمي", b"show_phone")],
        [Button.inline("مسح بيانات الحساب", b"clear_profile")]
    ]

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond("مرحباً! استخدم الأزرار أدناه للتحكم:", buttons=main_buttons())

@bot.on(events.CallbackQuery)
async def callback(event):
    sender_id = event.sender_id
    data = event.data.decode('utf-8')

    if data == "send_session":
        await event.edit("📩 أرسل لي StringSession الخاص بك كرسالة نصية.", buttons=main_buttons())

    elif data == "show_phone":
        info = user_clients.get(sender_id)
        if not info:
            await event.answer("❌ لم ترسل StringSession بعد.", alert=True)
            return
        client = info["client"]
        me = await client.get_me()
        await event.answer(f"رقم هاتفك: {me.phone or 'غير متوفر'}", alert=True)

    elif data == "clear_profile":
        info = user_clients.get(sender_id)
        if not info:
            await event.answer("❌ لم ترسل StringSession بعد.", alert=True)
            return
        client = info["client"]
        success, msg = await clear_profile(client)
        await event.edit(msg, buttons=main_buttons())

async def clear_profile(client):
    try:
        await client(UpdateProfileRequest(
            first_name="",
            last_name="",
            about=""
        ))
        await client(UpdateUsernameRequest(username=None))
        return True, "✅ تم مسح الاسم، النبذة، ومعرف المستخدم بنجاح."
    except Exception as e:
        return False, f"❌ حدث خطأ أثناء مسح البيانات: {e}"

@bot.on(events.NewMessage)
async def handle_session(event):
    text = event.text.strip()
    sender_id = event.sender_id

    # استقبال StringSession
    if len(text) > 50 and ' ' not in text and sender_id not in user_clients:
        try:
            client = TelegramClient(StringSession(text), API_ID, API_HASH)
            await client.start()
            me = await client.get_me()
            user_clients[sender_id] = {"client": client, "name": me.first_name}
            await event.respond(f"✅ تم تسجيل الدخول باسم {me.first_name}.\n"
                                f"📱 رقم الهاتف: {me.phone or 'غير متوفر'}",
                                buttons=main_buttons())
        except SessionPasswordNeededError:
            await event.respond("🔐 الحساب محمي بـ 2FA، يرجى إرسال كلمة المرور (قيد التطوير).")
        except Exception as e:
            await event.respond(f"❌ خطأ: {e}")

bot.run_until_disconnected()
