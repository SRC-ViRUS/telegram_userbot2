import asyncio
import os
import json
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest

api_id = 20507759
api_hash = "225d3a24d84c637b3b816d13cc7bd766"
bot_token = "7644214767:AAGOlYEiyF6yFWxiIX_jlwo9Ssj_Cb95oLU"

SESS_FILE = "sessions.json"
sessions = {}
clients = {}

bot = TelegramClient("bot", api_id, api_hash)

def load_sessions():
    if os.path.exists(SESS_FILE):
        with open(SESS_FILE, "r", encoding="utf-8") as f:
            sessions.update(json.load(f))

def save_sessions():
    with open(SESS_FILE, "w", encoding="utf-8") as f:
        json.dump(sessions, f, ensure_ascii=False, indent=2)

async def start_all_sessions():
    for name, sess_str in sessions.items():
        try:
            client = TelegramClient(StringSession(sess_str), api_id, api_hash)
            await client.start()
            clients[name] = client
            print(f"[+] Session started: {name}")
        except Exception as e:
            print(f"[!] Failed to start session {name}: {e}")

def main_menu():
    return [
        [Button.inline("📋 عرض الجلسات", b"list_sessions"), Button.inline("📥 إضافة جلسة", b"add_session")],
        [Button.inline("🗑️ حذف جلسة", b"del_session"), Button.inline("✉️ إرسال رسالة", b"send_message")]
    ]

def sessions_buttons(prefix):
    return [[Button.inline(name, f"{prefix}:{name}".encode())] for name in sessions]

adding_session_state = {}
send_message_state = {}

@bot.on(events.NewMessage(pattern="/start"))
async def start_handler(event):
    await event.respond("🟢 مرحبًا! اختر أحد الخيارات:", buttons=main_menu())

@bot.on(events.CallbackQuery(data=b"list_sessions"))
async def list_sessions_handler(event):
    if not sessions:
        await event.edit("🚫 لا توجد جلسات.", buttons=main_menu())
    else:
        text = "📋 الجلسات:\n" + "\n".join(f"- `{name}`" for name in sessions)
        await event.edit(text, parse_mode="md", buttons=main_menu())

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
        await event.edit(f"🗑️ تم حذف الجلسة `{name}`.", parse_mode="md", buttons=main_menu())
    else:
        await event.answer("❌ الجلسة غير موجودة.", alert=True)

@bot.on(events.CallbackQuery(data=b"add_session"))
async def add_session_start(event):
    adding_session_state[event.sender_id] = {"step": 1}
    await event.edit("🆔 أرسل `api_id`:")

@bot.on(events.NewMessage)
async def new_message_handler(event):
    uid = event.sender_id
    text = event.raw_text.strip()

    if uid in adding_session_state:
        state = adding_session_state[uid]
        step = state["step"]

        if step == 1:
            if not text.isdigit():
                await event.reply("❌ أرسل رقم api_id صحيح:")
                return
            state["api_id"] = int(text)
            state["step"] = 2
            await event.reply("🔑 أرسل api_hash:")
            return

        if step == 2:
            state["api_hash"] = text
            state["step"] = 3
            await event.reply("📱 أرسل رقم الهاتف:")
            return

        if step == 3:
            phone = text
            state["phone"] = phone
            state["client"] = TelegramClient(StringSession(), state["api_id"], state["api_hash"])
            await state["client"].connect()
            try:
                await state["client"].send_code_request(phone)
                state["step"] = 4
                await event.reply("🔢 أرسل كود التحقق:")
            except Exception as e:
                adding_session_state.pop(uid)
                await event.reply(f"❌ خطأ: {e}")
            return

        if step == 4:
            try:
                await state["client"].sign_in(state["phone"], text)
                sessions[state["phone"]] = state["client"].session.save()
                clients[state["phone"]] = state["client"]
                save_sessions()
                adding_session_state.pop(uid)
                await event.reply("✅ تم إضافة الجلسة.", buttons=main_menu())
            except SessionPasswordNeededError:
                state["step"] = 5
                await event.reply("🔐 أرسل كلمة مرور 2FA:")
            except PhoneCodeInvalidError:
                await event.reply("❌ الكود خطأ. حاول مرة أخرى:")
            return

        if step == 5:
            try:
                await state["client"].sign_in(password=text)
                sessions[state["phone"]] = state["client"].session.save()
                clients[state["phone"]] = state["client"]
                save_sessions()
                adding_session_state.pop(uid)
                await event.reply("✅ تم إضافة الجلسة بكلمة مرور.", buttons=main_menu())
            except Exception as e:
                await event.reply(f"❌ خطأ بكلمة المرور: {e}")
                adding_session_state.pop(uid)
            return

    elif uid in send_message_state:
        state = send_message_state[uid]
        step = state["step"]

        if step == 1:
            state["text"] = text
            state["step"] = 2
            await event.reply("📍 إلى من تريد إرسال الرسالة؟ (رابط كروب أو يوزر):")
            return

        if step == 2:
            send_message_state.pop(uid)
            target = text
            await event.reply("📤 يتم الإرسال...")

            for name, client in clients.items():
                try:
                    entity = await client.get_entity(target)
                    await client.send_message(entity, state["text"])
                    await bot.send_message(event.chat_id, f"✅ [{name}] تم الإرسال.")
                except Exception as e:
                    await bot.send_message(event.chat_id, f"❌ [{name}] فشل الإرسال: {e}")
            await bot.send_message(event.chat_id, "✅ انتهى الإرسال.", buttons=main_menu())

@bot.on(events.CallbackQuery(data=b"send_message"))
async def send_msg_btn(event):
    send_message_state[event.sender_id] = {"step": 1}
    await event.edit("📝 أرسل الرسالة الآن:")

async def main():
    load_sessions()
    await bot.start(bot_token=bot_token)
    await start_all_sessions()
    print("✅ البوت يعمل الآن...")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
