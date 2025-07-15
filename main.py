# -*- coding: utf-8 -*-
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.tl.functions.account import (
    UpdateProfileRequest, UpdateUsernameRequest
)
from telethon.tl.functions.photos import DeletePhotosRequest
from telethon.errors import SessionPasswordNeededError
import re, asyncio

# إعدادات API
API_ID   = 22494292
API_HASH = '0bd3915b6b1a0a64b168d0cc852a0e61'
BOT_TOKEN = '7768107017:AAH7ndo7wwLtRDRYLcTNC7ne7gWju3lDvtI'

# تشغيل البوت
bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# تخزين الجلسات وحالات المستخدم
user_clients = {}
pending_new_username = {}
pending_change_name = {}
pending_change_uname = {}

# أزرار الواجهة الرئيسية
def main_buttons():
    return [
        [Button.inline("📩 جلسة جديدة", b"send_session"), Button.inline("📱 رقم الهاتف", b"show_phone")],
        [Button.inline("🗑️ مسح البيانات", b"clear_profile"), Button.inline("🖼️ حذف الصور", b"delete_photos")],
        [Button.inline("✏️ تغيير الاسم", b"change_name"), Button.inline("🔄 تغيير اليوزر", b"change_uname")],
        [Button.inline("📋 الجلسات", b"list_sessions"), Button.inline("🚪 إنهاء الجلسات الأخرى", b"logout_all")]
    ]

@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.respond("مرحباً بك! 👋\nاختر من الأزرار:", buttons=main_buttons())

@bot.on(events.CallbackQuery)
async def callback(event):
    uid = event.sender_id
    data = event.data.decode()

    if data == "send_session":
        await event.edit("📩 أرسل StringSession الآن.", buttons=main_buttons())

    elif data == "show_phone":
        cl = user_clients.get(uid)
        if not cl:
            await event.answer("❌ لا توجد جلسة.", alert=True)
            return
        me = await cl.get_me()
        await event.answer(f"📱 {me.phone or 'غير متوفر'}", alert=True)

    elif data == "clear_profile":
        cl = user_clients.get(uid)
        if not cl:
            await event.answer("❌ لا توجد جلسة", alert=True)
            return
        try:
            await cl(UpdateProfileRequest(first_name=".", last_name="", about=""))
            await cl(UpdateUsernameRequest(username=""))
            pending_new_username[uid] = True
            await event.edit("🗑️ تم مسح الاسم والنبذة واليوزر.\n✏️ أرسل اليوزر الجديد (بدون @) أو /skip", buttons=[[Button.inline("إلغاء", b"cancel_uname")]])
        except Exception as e:
            await event.edit(f"❌ خطأ أثناء المسح: {e}", buttons=main_buttons())

    elif data == "cancel_uname":
        pending_new_username.pop(uid, None)
        await event.edit("❌ تم الإلغاء.", buttons=main_buttons())

    elif data == "delete_photos":
        cl = user_clients.get(uid)
        if not cl:
            await event.answer("❌ لا توجد جلسة", alert=True)
            return
        try:
            photos = await cl.get_profile_photos("me")
            await cl(DeletePhotosRequest(id=photos))
            await event.edit("🖼️ تم حذف جميع صور الحساب.", buttons=main_buttons())
        except Exception as e:
            await event.edit(f"❌ فشل: {e}", buttons=main_buttons())

    elif data == "change_name":
        if uid not in user_clients:
            await event.answer("❌ لا توجد جلسة", alert=True)
            return
        pending_change_name[uid] = True
        await event.edit("✏️ أرسل الاسم الجديد الآن (مثلاً: علي أو علي جاسم)", buttons=[])

    elif data == "change_uname":
        if uid not in user_clients:
            await event.answer("❌ لا توجد جلسة", alert=True)
            return
        pending_change_uname[uid] = True
        await event.edit("🔄 أرسل اليوزر الجديد (بدون @)", buttons=[])

    elif data == "list_sessions":
        if not user_clients:
            await event.edit("⚠️ لا توجد جلسات حالياً.", buttons=main_buttons())
            return
        msg = "📋 الجلسات:\n\n" + "\n".join(
            f"• {await (cl.get_me()).first_name} - {id}" for id, cl in user_clients.items()
        )
        await event.edit(msg, buttons=main_buttons())

    elif data == "logout_all":
        cnt = 0
        for other_uid, cl in list(user_clients.items()):
            if other_uid == uid:
                continue
            await cl.disconnect()
            user_clients.pop(other_uid)
            cnt += 1
        await event.edit(f"✅ تم إنهاء {cnt} جلسة أخرى.", buttons=main_buttons())

@bot.on(events.NewMessage)
async def handle(event):
    uid = event.sender_id
    txt = event.text.strip()

    if uid in pending_new_username:
        if txt.lower() in ("/skip", "/cancel"):
            pending_new_username.pop(uid, None)
            await event.respond("تم تجاوز تعيين اليوزر.", buttons=main_buttons())
            return
        try:
            await user_clients[uid](UpdateUsernameRequest(username=txt.strip("@")))
            await event.respond(f"✅ تم تعيين اليوزر الجديد @{txt.strip('@')}", buttons=main_buttons())
        except Exception as e:
            await event.respond(f"❌ فشل: {e}", buttons=main_buttons())
        pending_new_username.pop(uid, None)

    elif uid in pending_change_name:
        names = txt.split(maxsplit=1)
        first = names[0]
        last = names[1] if len(names) == 2 else ""
        try:
            await user_clients[uid](UpdateProfileRequest(first_name=first, last_name=last))
            await event.respond("✅ تم تغيير الاسم.", buttons=main_buttons())
        except Exception as e:
            await event.respond(f"❌ فشل: {e}", buttons=main_buttons())
        pending_change_name.pop(uid, None)

    elif uid in pending_change_uname:
        try:
            await user_clients[uid](UpdateUsernameRequest(username=txt.strip("@")))
            await event.respond(f"✅ تم تغيير اليوزر إلى @{txt.strip('@')}", buttons=main_buttons())
        except Exception as e:
            await event.respond(f"❌ فشل: {e}", buttons=main_buttons())
        pending_change_uname.pop(uid, None)

    elif len(txt) > 50 and ' ' not in txt and uid not in user_clients:
        try:
            client = TelegramClient(StringSession(txt), API_ID, API_HASH)
            await client.start()
            user_clients[uid] = client
            me = await client.get_me()
            await event.respond(f"✅ تم تسجيل الدخول باسم {me.first_name}", buttons=main_buttons())
        except SessionPasswordNeededError:
            await event.respond("🔐 الحساب محمي بـ 2FA، غير مدعوم حالياً.")
        except Exception as e:
            await event.respond(f"❌ خطأ: {e}")

# إصلاح لأي خطأ محتمل في sender.bot
@bot.on(events.Raw)
async def fix_sender(event):
    if hasattr(event, "sender") and not hasattr(event.sender, "bot"):
        setattr(event.sender, "bot", False)

# تشغيل البوت حتى الانفصال
bot.run_until_disconnected()
