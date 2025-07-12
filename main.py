import asyncio
import os
import json
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.errors import UserAlreadyParticipantError, SessionPasswordNeededError, PhoneCodeInvalidError
from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream import AudioPiped

api_id = 20507759
api_hash = "225d3a24d84c637b3b816d13cc7bd766"
bot_token = "7644214767:AAGOlYEiyF6yFWxiIX_jlwo9Ssj_Cb95oLU"

SESS_FILE = "sessions.json"
sessions = {}
clients = {}
calls = {}

bot = TelegramClient("bot", api_id, api_hash)

# تحميل وحفظ الجلسات
def load_sessions():
    global sessions
    if os.path.exists(SESS_FILE):
        with open(SESS_FILE, "r", encoding="utf-8") as f:
            sessions.update(json.load(f))

def save_sessions():
    with open(SESS_FILE, "w", encoding="utf-8") as f:
        json.dump(sessions, f, ensure_ascii=False, indent=2)

# تشغيل جميع الجلسات وتحضير pytgcalls
async def start_all_sessions():
    for name, sess_str in sessions.items():
        try:
            client = TelegramClient(StringSession(sess_str), api_id, api_hash)
            await client.start()
            clients[name] = client
            call = PyTgCalls(client)
            await call.start()
            calls[name] = call
            print(f"[+] Session started: {name}")
        except Exception as e:
            print(f"[!] Failed to start session {name}: {e}")

# أزرار الواجهة الرئيسية
def main_menu():
    return [
        [Button.inline("🚀 صعود الاتصال", b"connect"), Button.inline("🛑 نزول الاتصال", b"disconnect")],
        [Button.inline("📋 عرض الجلسات", b"list_sessions"), Button.inline("📥 إضافة جلسة", b"add_session")],
        [Button.inline("🗑️ حذف جلسة", b"del_session"), Button.inline("✉️ إرسال رسالة", b"send_message")]
    ]

def sessions_buttons(prefix):
    return [[Button.inline(name, f"{prefix}:{name}".encode())] for name in sessions]

# تخزين حالة إضافة جلسة وحالة إرسال رسالة
adding_session_state = {}
send_message_state = {}
waiting_for_connect_link = set()

# /start
@bot.on(events.NewMessage(pattern="/start"))
async def start_handler(event):
    await event.respond("🟢 مرحبًا! اختر أحد الخيارات:", buttons=main_menu())

# عرض الجلسات
@bot.on(events.CallbackQuery(data=b"list_sessions"))
async def list_sessions_handler(event):
    if not sessions:
        await event.edit("🚫 لا توجد جلسات مخزنة.", buttons=main_menu())
    else:
        text = "📋 الجلسات المخزنة:\n" + "\n".join(f"- `{name}`" for name in sessions)
        await event.edit(text, parse_mode="md", buttons=main_menu())

# حذف جلسة - خطوة اختيار الجلسة
@bot.on(events.CallbackQuery(data=b"del_session"))
async def del_session_step1(event):
    if not sessions:
        await event.answer("🚫 لا توجد جلسات.", alert=True)
        return
    await event.edit("🗑️ اختر جلسة للحذف:", buttons=sessions_buttons("del"))

@bot.on(events.CallbackQuery(pattern=b"del:(.+)"))
async def del_session_confirm(event):
    name = event.data.decode().split(":",1)[1]
    if name in sessions:
        sessions.pop(name)
        save_sessions()
        cl = clients.pop(name, None)
        if cl:
            await cl.disconnect()
        call = calls.pop(name, None)
        if call:
            await call.stop()
        await event.edit(f"🗑️ تم حذف الجلسة `{name}`.", parse_mode="md", buttons=main_menu())
    else:
        await event.answer("❌ الجلسة غير موجودة.", alert=True)

# إضافة جلسة - حوار خطوة بخطوة
@bot.on(events.CallbackQuery(data=b"add_session"))
async def add_session_start(event):
    adding_session_state[event.sender_id] = {"step": 1}
    await event.edit("🆔 أدخل `api_id` الخاص بجلسة تيليجرام:")

@bot.on(events.NewMessage)
async def add_session_handler(event):
    uid = event.sender_id
    text = event.raw_text.strip()

    if uid in adding_session_state:
        state = adding_session_state[uid]
        step = state["step"]

        if step == 1:
            if not text.isdigit():
                await event.reply("❌ `api_id` يجب أن يكون أرقام فقط، أعد المحاولة:")
                return
            state["api_id"] = int(text)
            state["step"] = 2
            await event.reply("🔑 أدخل `api_hash`:")
            return

        if step == 2:
            state["api_hash"] = text
            state["step"] = 3
            await event.reply("📱 أدخل رقم الهاتف كاملاً مع رمز الدولة (+964...) :")
            return

        if step == 3:
            state["phone"] = text
            state["client"] = TelegramClient(StringSession(), state["api_id"], state["api_hash"])
            await state["client"].connect()
            try:
                await state["client"].send_code_request(text)
                state["step"] = 4
                await event.reply("🔢 أدخل كود التحقق الذي وصلك:")
            except Exception as e:
                adding_session_state.pop(uid)
                await event.reply(f"❌ حدث خطأ أثناء إرسال كود التحقق: {e}")
            return

        if step == 4:
            client = state["client"]
            try:
                await client.sign_in(state["phone"], text)
            except SessionPasswordNeededError:
                state["step"] = 5
                await event.reply("🔐 أدخل كلمة مرور 2FA:")
                return
            except PhoneCodeInvalidError:
                await event.reply("❌ الكود غير صحيح، حاول مجدداً:")
                return
            except Exception as e:
                adding_session_state.pop(uid)
                await event.reply(f"❌ حدث خطأ أثناء تسجيل الدخول: {e}")
                return

            sessions[state["phone"]] = client.session.save()
            save_sessions()
            clients[state["phone"]] = client
            call = PyTgCalls(client)
            await call.start()
            calls[state["phone"]] = call
            adding_session_state.pop(uid)
            await event.reply("✅ تم إضافة الجلسة وتشغيلها بنجاح.", buttons=main_menu())
            return

        if step == 5:
            try:
                await state["client"].sign_in(password=text)
                sessions[state["phone"]] = state["client"].session.save()
                save_sessions()
                clients[state["phone"]] = state["client"]
                call = PyTgCalls(state["client"])
                await call.start()
                calls[state["phone"]] = call
                adding_session_state.pop(uid)
                await event.reply("✅ تم إضافة الجلسة وتشغيلها بنجاح.", buttons=main_menu())
            except Exception as e:
                adding_session_state.pop(uid)
                await event.reply(f"❌ خطأ في كلمة المرور: {e}")
            return

# إرسال رسالة - بدء الحوار
@bot.on(events.CallbackQuery(data=b"send_message"))
async def send_message_start(event):
    send_message_state[event.sender_id] = {"step": 1}
    await event.edit("📝 اكتب الرسالة التي تريد إرسالها لجميع الحسابات:")

@bot.on(events.NewMessage)
async def send_message_handler(event):
    uid = event.sender_id
    text = event.raw_text.strip()

    if uid in send_message_state:
        state = send_message_state[uid]
        step = state["step"]

        if step == 1:
            state["text"] = text
            state["step"] = 2
            await event.reply("📍 إلى من تريد إرسال الرسالة؟ (يوزر @، آيدي، أو رابط كروب/قناة):")
            return

        if step == 2:
            target = text
            message = state["text"]
            send_message_state.pop(uid)
            await event.reply("🚀 جارٍ إرسال الرسالة...")

            for name, client in clients.items():
                try:
                    entity = await client.get_entity(target)
                    await client.send_message(entity, message)
                    await bot.send_message(event.chat_id, f"✅ [{name}] أرسل الرسالة.")
                except Exception as e:
                    await bot.send_message(event.chat_id, f"❌ [{name}] فشل الإرسال: {e}")

            await bot.send_message(event.chat_id, "✅ انتهى الإرسال.", buttons=main_menu())

# زر صعود الاتصال
@bot.on(events.CallbackQuery(data=b"connect"))
async def connect_handler(event):
    waiting_for_connect_link.add(event.sender_id)
    await event.edit("📨 أرسل رابط الكروب أو القناة أو رابط الدعوة للصعود:")

# زر نز
