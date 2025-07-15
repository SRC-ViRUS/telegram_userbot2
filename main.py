# -*- coding: utf-8 -*-
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.tl.functions.account import (
    UpdateProfileRequest, UpdateUsernameRequest, DeleteAccountRequest
)
from telethon.errors import SessionPasswordNeededError
import re

API_ID   = 22494292
API_HASH = '0bd3915b6b1a0a64b168d0cc852a0e61'
BOT_TOKEN = '7768107017:AAH7ndo7wwLtRDRYLcTNC7ne7gWju3lDvtI'

bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

user_clients           = {}   # {uid: {"client": TelegramClient}}
pending_delete         = {}   # حذف الحساب نهائياً
pending_new_username   = {}   # بعد مسح البيانات – اسم مستخدم جديد
pending_change_name    = {}   # انتظار الاسم الجديد
pending_change_uname   = {}   # انتظار يوزر جديد

# ---------- أزرار الواجهة ----------
def main_buttons():
    return [
        [Button.inline("📩 أرسل StringSession", b"send_session")],
        [Button.inline("📱 عرض رقم الهاتف",       b"show_phone")],
        [Button.inline("🗑️ مسح بيانات الحساب",    b"clear_profile")],
        [Button.inline("🖼️ حذف جميع الصور",       b"delete_photos")],
        [Button.inline("✏️ تغيير الاسم",          b"change_name")],
        [Button.inline("🔄 تغيير اسم المستخدم",   b"change_uname")],
        [Button.inline("⚠️ حذف الحساب نهائياً",  b"delete_account")],
        [Button.inline("📋 عرض الجلسات",         b"list_sessions")],
        [Button.inline("🚪 إنهاء جميع الجلسات عدا حسابك", b"logout_all")]
    ]

# ---------- /start ----------
@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond("مرحباً! استخدم الأزرار أدناه للتحكم:", buttons=main_buttons())

# ---------- التعامل مع الأزرار ----------
@bot.on(events.CallbackQuery)
async def callback(event):
    uid  = event.sender_id
    data = event.data.decode()

    # === إرسال جلسة ===
    if data == "send_session":
        await event.edit("📩 أرسل لي StringSession الخاص بك كرسالة نصية.", buttons=main_buttons())

    # === عرض رقم الهاتف ===
    elif data == "show_phone":
        info = user_clients.get(uid)
        if not info:
            await event.answer("❌ لم ترسل StringSession بعد.", alert=True); return
        me = await info["client"].get_me()
        await event.answer(f"رقم هاتفك: {me.phone or 'غير متوفر'}", alert=True)

    # === مسح البيانات (اسم + نبذة + حذف يوزر) ===
    elif data == "clear_profile":
        info = user_clients.get(uid)
        if not info:
            await event.answer("❌ لم ترسل StringSession بعد.", alert=True); return
        ok, msg = await clear_profile(info["client"])
        if ok:
            pending_new_username[uid] = True
            await event.edit(msg + "\n\n✏️ أرسل اسم المستخدم الجديد (بدون @) أو /skip لتجاوز:", 
                             buttons=[[Button.inline("إلغاء", b"cancel_new_username")]])
        else:
            await event.edit(msg, buttons=main_buttons())

    # --- إلغاء انتظار اسم مستخدم جديد بعد المسح ---
    elif data == "cancel_new_username":
        pending_new_username.pop(uid, None)
        await event.edit("❌ تم الإلغاء.", buttons=main_buttons())

    # === حذف كلّ صور البروفايل ===
    elif data == "delete_photos":
        info = user_clients.get(uid)
        if not info:
            await event.answer("❌ لم ترسل StringSession بعد.", alert=True); return
        ok, msg = await delete_all_photos(info["client"])
        await event.edit(msg, buttons=main_buttons())

    # === بدء تغيير الاسم ===
    elif data == "change_name":
        if uid not in user_clients:
            await event.answer("❌ لم ترسل StringSession بعد.", alert=True); return
        pending_change_name[uid] = True
        await event.edit("✏️ أرسل الاسم الجديد (يمكنك كتابة: الاسم أو الاسم اللقب)\nأو /cancel للإلغاء.",
                         buttons=[[Button.inline("إلغاء", b"cancel_change_name")]])

    elif data == "cancel_change_name":
        pending_change_name.pop(uid, None)
        await event.edit("❌ تم إلغاء تغيير الاسم.", buttons=main_buttons())

    # === بدء تغيير اليوزر ===
    elif data == "change_uname":
        if uid not in user_clients:
            await event.answer("❌ لم ترسل StringSession بعد.", alert=True); return
        pending_change_uname[uid] = True
        await event.edit("🔄 أرسل اسم المستخدم الجديد (بدون @) أو /cancel للإلغاء.",
                         buttons=[[Button.inline("إلغاء", b"cancel_change_uname")]])

    elif data == "cancel_change_uname":
        pending_change_uname.pop(uid, None)
        await event.edit("❌ تم إلغاء تغيير اسم المستخدم.", buttons=main_buttons())

    # === حذف الحساب نهائياً ===
    elif data == "delete_account":
        await event.edit("⚠️ هل أنت متأكد من حذف حسابك نهائياً؟\n"
                         "أرسل كلمة مرور 2FA للتأكيد أو /cancel للإلغاء.",
                         buttons=[[Button.inline("إلغاء", b"cancel_delete")]])
        pending_delete[uid] = True

    elif data == "cancel_delete":
        pending_delete.pop(uid, None)
        await event.edit("❌ تم إلغاء حذف الحساب.", buttons=main_buttons())

    # === عرض الجلسات ===
    elif data == "list_sessions":
        if not user_clients:
            await event.edit("⚠️ لا توجد جلسات.", buttons=main_buttons()); return
        txt = "📋 الجلسات:\n"
        for i, (u, info) in enumerate(user_clients.items(), 1):
            me = await info["client"].get_me()
            txt += f"{i}- {u} | {me.first_name}\n"
        await event.edit(txt, buttons=main_buttons())

    # === إنهاء كل الجلسات الأخرى ===
    elif data == "logout_all":
        cnt = 0
        for other_uid, info in list(user_clients.items()):
            if other_uid == uid: continue
            await info["client"].disconnect()
            user_clients.pop(other_uid); cnt += 1
        await event.edit(f"✅ تم إنهاء {cnt} جلسة.", buttons=main_buttons())

# ---------- استقبال الرسائل (جلسة أو أوامر نصية) ----------
@bot.on(events.NewMessage)
async def handle_msg(event):
    uid  = event.sender_id
    txt  = event.text.strip()

    # -------- انتظار كلمة مرور حذف الحساب --------
    if uid in pending_delete:
        if txt.lower() == "/cancel":
            pending_delete.pop(uid); await event.respond("❌ تم الإلغاء.", buttons=main_buttons()); return
        info = user_clients.get(uid)
        if not info:
            pending_delete.pop(uid); await event.respond("❌ لا توجد جلسة."); return
        try:
            await info["client"](DeleteAccountRequest(reason=txt))
            await info["client"].disconnect()
            user_clients.pop(uid); pending_delete.pop(uid)
            await event.respond("✅ تم حذف الحساب نهائياً.")
        except Exception as e:
            await event.respond(f"❌ فشل حذف الحساب: {e}")
        return

    # -------- انتظار اسم مستخدم جديد بعد مسح البيانات --------
    if uid in pending_new_username:
        if txt.lower() in ("/cancel", "/skip"):
            pending_new_username.pop(uid); await event.respond("تم التجاوز.", buttons=main_buttons()); return
        uname = txt.lstrip("@")
        if not re.match(r"^[a-zA-Z0-9_]{5,32}$", uname):
            await event.respond("❌ اسم مستخدم غير صالح."); return
        ok, msg = await set_username(user_clients[uid]["client"], uname)
