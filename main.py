from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.tl.functions.account import (
    UpdateProfileRequest,
    UpdateUsernameRequest,
    DeleteAccountRequest
)
from telethon.errors import SessionPasswordNeededError

API_ID = 22494292
API_HASH = '0bd3915b6b1a0a64b168d0cc852a0e61'
BOT_TOKEN = '7768107017:AAH7ndo7wwLtRDRYLcTNC7ne7gWju3lDvtI'

bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
user_clients = {}
pending_delete = {}  # لتخزين حالة انتظار حذف الحساب

def main_buttons():
    return [
        [Button.inline("📩 أرسل StringSession", b"send_session")],
        [Button.inline("📱 عرض رقم الهاتف", b"show_phone")],
        [Button.inline("🗑️ مسح بيانات الحساب", b"clear_profile")],
        [Button.inline("⚠️ حذف الحساب نهائياً", b"delete_account")],
        [Button.inline("📋 عرض الجلسات", b"list_sessions")],
        [Button.inline("🚪 إنهاء جميع الجلسات عدا حسابك", b"logout_all")]
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

    elif data == "delete_account":
        await event.edit(
            "⚠️ هل أنت متأكد من حذف حسابك نهائياً؟\n"
            "أرسل كلمة المرور (2FA) لتأكيد الحذف أو /cancel للإلغاء.",
            buttons=[[Button.inline("إلغاء", b"cancel_delete")]]
        )
        pending_delete[sender_id] = {"step": "awaiting_password"}

    elif data == "cancel_delete":
        pending_delete.pop(sender_id, None)
        await event.edit("❌ تم إلغاء حذف الحساب.", buttons=main_buttons())

    elif data == "list_sessions":
        if not user_clients:
            await event.edit("⚠️ لا توجد جلسات مسجلة حالياً.", buttons=main_buttons())
            return
        text = "📋 الجلسات الحالية:\n"
        for uid, info in user_clients.items():
            client = info["client"]
            try:
                me = await client.get_me()
                name = f"{me.first_name} {me.last_name or ''}".strip()
            except:
                name = "غير متوفر"
            text += f"- معرف: {uid} | الاسم: {name}\n"
        await event.edit(text, buttons=main_buttons())

    elif data == "logout_all":
        count = 0
        for uid, info in list(user_clients.items()):
            if uid == sender_id:
                continue
            client = info["client"]
            await client.disconnect()
            user_clients.pop(uid)
            count += 1
        await event.edit(f"✅ تم إنهاء {count} جلسة من جميع الجلسات عدا جلستك.", buttons=main_buttons())

@bot.on(events.NewMessage)
async def handle_session(event):
    text = event.text.strip()
    sender_id = event.sender_id

    # انتظار كلمة المرور لتأكيد حذف الحساب
    if sender_id in pending_delete:
        if text.lower() == '/cancel':
            pending_delete.pop(sender_id)
            await event.respond("❌ تم إلغاء حذف الحساب.", buttons=main_buttons())
            return

        password = text
        info = user_clients.get(sender_id)
        if not info:
            await event.respond("❌ لم ترسل StringSession بعد. أرسلها أولاً.")
            pending_delete.pop(sender_id)
            return
        client = info["client"]

        try:
            await client(DeleteAccountRequest(reason=password))
            await client.disconnect()
            user_clients.pop(sender_id)
            pending_delete.pop(sender_id)
            await event.respond("✅ تم حذف الحساب نهائياً. مع السلامة!", buttons=main_buttons())
        except Exception as e:
            await event.respond(f"❌ فشل حذف الحساب: {e}\n"
                                "تأكد من أن كلمة المرور صحيحة أو أن الحساب ليس محميًا بكلمة مرور أخرى.")
        return

    # استقبال StringSession
    if len(text) > 50 and ' ' not in text and sender_id not in user_clients:
        try:
            client = TelegramClient(StringSession(text), API_ID, API_HASH)
            await client.start()
            me = await client.get_me()
            user_clients[sender_id] = {"client": client, "name": me.first_name}
            await event.respond(
                f"✅ تم تسجيل الدخول باسم {me.first_name}.\n"
                f"📱 رقم الهاتف: {me.phone or 'غير متوفر'}",
                buttons=main_buttons()
            )
        except SessionPasswordNeededError:
            await event.respond("🔐 الحساب محمي بـ 2FA، يرجى إرسال كلمة المرور (قيد التطوير).")
        except Exception as e:
            await event.respond(f"❌ خطأ: {e}")

async def clear_profile(client):
    try:
        await client(UpdateProfileRequest(
            first_name=".",    # لا يمكن تركه فارغاً
            last_name="",
            about=""
        ))
        # محاولة حذف اسم المستخدم (username) بدون تعيين بديل
        await client(UpdateUsernameRequest(username=None))
        return True, "✅ تم مسح الاسم والنبذة وحذف اسم المستخدم (username) بنجاح."
    except Exception as e:
        return False, f"❌ حدث خطأ أثناء مسح البيانات: {e}"

bot.run_until_disconnected()
