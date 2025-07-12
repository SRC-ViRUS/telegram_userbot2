import asyncio
import json
import os
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.errors import UserAlreadyParticipantError, SessionPasswordNeededError

# بيانات الاتصال
api_id = 20507759
api_hash = "225d3a24d84c637b3b816d13cc7bd766"
bot_token = "7644214767:AAGOlYEiyF6yFWxiIX_jlwo9Ssj_Cb95oLU"

SESS_FILE = "sessions.json"  # ملف تخزين الجلسات

# متغيرات عامة
sessions = {}
clients = {}
current_chat = None
adding_state = {}

bot = TelegramClient("bot", api_id, api_hash)

def load_sessions():
    global sessions
    if os.path.exists(SESS_FILE):
        with open(SESS_FILE, "r", encoding="utf-8") as f:
            sessions = json.load(f)
    else:
        sessions = {}

def save_sessions():
    with open(SESS_FILE, "w", encoding="utf-8") as f:
        json.dump(sessions, f, ensure_ascii=False, indent=2)

async def start_all_sessions():
    for name, s in sessions.items():
        try:
            client = TelegramClient(StringSession(s), api_id, api_hash)
            await client.start()
            clients[name] = client
            print(f"[+] Session started: {name}")
        except Exception as e:
            print(f"[!] Failed {name}: {e}")

def main_menu():
    return [
        [Button.inline("🚀 صعود الاتصال", b"connect"), Button.inline("🛑 نزول الاتصال", b"disconnect")],
        [Button.inline("📋 عرض الجلسات", b"list")],
        [Button.inline("📥 إضافة جلسة", b"add"), Button.inline("🗑️ حذف جلسة", b"del")],
        [Button.inline("🔁 إعادة تشغيل الجلسات", b"reload")]
    ]

def sessions_buttons(prefix: str):
    return [[Button.inline(name, f"{prefix}:{name}".encode())] for name in sessions]

@bot.on(events.NewMessage(pattern="/start"))
async def start_cmd(e):
    await e.respond("👋 أهلاً بك – اختر من الأزرار:", buttons=main_menu())

@bot.on(events.CallbackQuery(data=b"list"))
async def list_sessions(e):
    load_sessions()
    txt = "📋 **الجلسات الحالية:**\n"
    if not sessions:
        txt += "لا توجد أي جلسة محفوظة."
    else:
        for i, name in enumerate(sessions, 1):
            txt += f"{i}. `{name}`\n"
    await e.edit(txt, buttons=main_menu())

@bot.on(events.CallbackQuery(data=b"reload"))
async def reload_sessions(e):
    await e.answer("⏳ جارٍ إعادة تشغيل الجلسات...")
    for c in clients.values():
        await c.disconnect()
    clients.clear()
    load_sessions()
    await start_all_sessions()
    await e.edit("✅ تمت إعادة التشغيل.", buttons=main_menu())

@bot.on(events.CallbackQuery(data=b"connect"))
async def ask_link(e):
    await e.answer()
    await e.edit("📨 أرسل الآن رابط الكروب أو القناة أو الدعوة:")

    async def wait_for_link():
        while True:
            msg = await bot.wait_for(events.NewMessage(from_users=e.sender_id))
            if msg.text:
                return msg.text.strip()

    try:
        link = await wait_for_link()

        if "joinchat" in link or "+" in link:
            code = link.split("+")[-1]
            ent = (await bot(ImportChatInviteRequest(code))).chats[0]
        else:
            ent = await bot.get_entity(link)

    except Exception as err:
        await e.respond(f"❌ الرابط غير صالح أو غير معروف:\n`{err}`", buttons=main_menu())
        return

    global current_chat
    current_chat = ent

    await e.respond("🔁 جارٍ صعود الحسابات...")
    for name, cl in clients.items():
        try:
            await cl(JoinChannelRequest(ent))
            await asyncio.sleep(1)
            await bot.send_message(e.chat_id, f"✅ [{name}] صعد الاتصال")
        except UserAlreadyParticipantError:
            await bot.send_message(e.chat_id, f"✅ [{name}] موجود مسبقاً")
        except Exception as ex:
            await bot.send_message(e.chat_id, f"❌ [{name}] خطأ: {ex}")

    await bot.send_message(e.chat_id, "✅ تم صعود جميع الحسابات.", buttons=main_menu())

@bot.on(events.CallbackQuery(data=b"disconnect"))
async def leave_all(e):
    await e.answer()
    if not current_chat:
        await e.edit("⚠️ لا يوجد كروب مُحدد.", buttons=main_menu())
        return
    await e.edit("🔁 جارٍ نزول الحسابات...")
    for name, cl in clients.items():
        try:
            await cl(LeaveChannelRequest(current_chat))
            await asyncio.sleep(1)
            await bot.send_message(e.chat_id, f"⬇️ [{name}] خرج")
        except Exception as ex:
            await bot.send_message(e.chat_id, f"❌ [{name}] خطأ: {ex}")
    await bot.send_message(e.chat_id, "✅ تم نزول الجميع.", buttons=main_menu())

@bot.on(events.CallbackQuery(data=b"del"))
async def choose_del(e):
    if not sessions:
        await e.answer("🚫 لا توجد جلسات")
        return
    await e.edit("🗑️ اختر جلسة لحذفها:", buttons=sessions_buttons("del"))

@bot.on(events.CallbackQuery(pattern=b"del:(.+)"))
async def delete_session(e):
    name = e.data.decode().split(":",1)[1]
    await e.answer()
    sessions.pop(name, None)
    save_sessions()
    cl = clients.pop(name, None)
    if cl:
        await cl.disconnect()
    await e.edit(f"🗑️ حُذفت الجلسة `{name}`.", buttons=main_menu())

@bot.on(events.CallbackQuery(data=b"add"))
async def add_start(e):
    await e.answer()
    adding_state[e.sender_id] = {"step": 1}
    await e.edit("📥 **إضافة جلسة جديدة**\nأرسل `api_id`:")

@bot.on(events.NewMessage)
async def add_flow(msg):
    uid = msg.sender_id
    if uid not in adding_state:
        return

    state = adding_state[uid]
    step = state["step"]

    if step == 1:
        if not msg.text.isdigit():
            await msg.reply("❌ api_id يجب أن يكون رقمًا. أعد الإرسال.")
            return
        state["api_id"] = int(msg.text)
        state["step"] = 2
        await msg.reply("🔑 أرسل `api_hash`:")

    elif step == 2:
        state["api_hash"] = msg.text.strip()
        state["step"] = 3
        await msg.reply("📞 أرسل رقم الهاتف (مع +):")

    elif step == 3:
        phone = msg.text.strip()
        state["phone"] = phone
        state["step"] = 4
        state["client"] = TelegramClient(StringSession(), state["api_id"], state["api_hash"])
        await state["client"].connect()
        try:
            await state["client"].send_code_request(phone)
            await msg.reply("✉️ تم إرسال كود التفعيل، أرسله الآن:")
        except Exception as ex:
            await msg.reply(f"❌ خطأ الإرسال: {ex}")
            adding_state.pop(uid)
            await state["client"].disconnect()

    elif step == 4:
        code = msg.text.strip().replace(" ", "")
        cl = state["client"]
        try:
            await cl.sign_in(state["phone"], code)
        except SessionPasswordNeededError:
            state["step"] = 5
            await msg.reply("🔐 يوجد تحقق ثنائي.\nأرسل كلمة المرور:")
            return
        sess_name = f"{state['phone']}"
        sess_str = cl.session.save()
        sessions[sess_name] = sess_str
        save_sessions()
        clients[sess_name] = cl
        adding_state.pop(uid)
        await msg.reply(f"✅ تم إضافة الجلسة `{sess_name}`.", buttons=main_menu())

    elif step == 5:
        pwd = msg.text.strip()
        cl = state["client"]
        try:
            await cl.sign_in(password=pwd)
            sess_name = f"{state['phone']}"
            sess_str = cl.session.save()
            sessions[sess_name] = sess_str
            save_sessions()
            clients[sess_name] = cl
            adding_state.pop(uid)
            await msg.reply(f"✅ تم إضافة الجلسة `{sess_name}`.", buttons=main_menu())
        except Exception as ex:
            await msg.reply(f"❌ كلمة المرور خاطئة: {ex}")

async def main():
    load_sessions()
    await bot.start(bot_token=bot_token)
    await start_all_sessions()
    print(">> Bot is running ...")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
