import asyncio
import json
import os
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, UserAlreadyParticipantError
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest

# بيانات البوت
api_id = 20507759
api_hash = "225d3a24d84c637b3b816d13cc7bd766"
bot_token = "7644214767:AAGOlYEiyF6yFWxiIX_jlwo9Ssj_Cb95oLU"

SESS_FILE = "sessions.json"
sessions = {}
clients = {}
current_chat = None
waiting_for_link = {}
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
        [Button.inline("📋 عرض الجلسات", b"list"), Button.inline("📥 إضافة جلسة", b"add")]
    ]

@bot.on(events.NewMessage(pattern="/start"))
async def start_cmd(e):
    await e.respond("👋 أهلاً بك – اختر من الأزرار:", buttons=main_menu())

@bot.on(events.CallbackQuery(data=b"connect"))
async def connect_cmd(event):
    user_id = event.sender_id
    waiting_for_link[user_id] = True
    await event.edit("📨 أرسل رابط القناة / الكروب / المكالمة:")

@bot.on(events.CallbackQuery(data=b"disconnect"))
async def disconnect_cmd(event):
    if not current_chat:
        await event.edit("⚠️ لم يتم تحديد كروب.", buttons=main_menu())
        return
    await event.edit("🔁 جارٍ نزول الحسابات...")
    for name, cl in clients.items():
        try:
            await cl(LeaveChannelRequest(current_chat))
            await asyncio.sleep(1)
            await bot.send_message(event.chat_id, f"⬇️ [{name}] خرج")
        except Exception as ex:
            await bot.send_message(event.chat_id, f"❌ [{name}] خطأ: {ex}")
    await bot.send_message(event.chat_id, "✅ تم النزول.", buttons=main_menu())

@bot.on(events.CallbackQuery(data=b"list"))
async def list_sessions(event):
    load_sessions()
    if not sessions:
        txt = "🚫 لا توجد جلسات حالياً."
    else:
        txt = "📋 الجلسات:\n" + "\n".join([f"- `{s}`" for s in sessions])
    await event.edit(txt, buttons=main_menu())

@bot.on(events.CallbackQuery(data=b"add"))
async def add_session(event):
    adding_state[event.sender_id] = {"step": 1}
    await event.edit("📥 أرسل `api_id` الآن:")

@bot.on(events.NewMessage)
async def all_handler(event):
    user_id = event.sender_id
    text = event.raw_text.strip()

    # ============ إضافة جلسة ============
    if user_id in adding_state:
        state = adding_state[user_id]
        step = state["step"]

        if step == 1:
            if not text.isdigit():
                await event.reply("❌ يجب أن يكون api_id رقم.")
                return
            state["api_id"] = int(text)
            state["step"] = 2
            await event.reply("🔐 أرسل `api_hash`:")

        elif step == 2:
            state["api_hash"] = text
            state["step"] = 3
            await event.reply("📞 أرسل رقم الهاتف مع +:")

        elif step == 3:
            phone = text
            state["phone"] = phone
            state["client"] = TelegramClient(StringSession(), state["api_id"], state["api_hash"])
            await state["client"].connect()
            try:
                await state["client"].send_code_request(phone)
                state["step"] = 4
                await event.reply("📨 تم إرسال الكود، أرسله الآن:")
            except Exception as e:
                await event.reply(f"❌ فشل إرسال الكود: {e}")
                adding_state.pop(user_id)

        elif step == 4:
            code = text.replace(" ", "")
            try:
                await state["client"].sign_in(state["phone"], code)
                session = state["client"].session.save()
                name = state["phone"]
                sessions[name] = session
                save_sessions()
                clients[name] = state["client"]
                adding_state.pop(user_id)
                await event.reply(f"✅ تم إضافة الجلسة `{name}`", buttons=main_menu())
            except SessionPasswordNeededError:
                state["step"] = 5
                await event.reply("🔐 أرسل كلمة مرور التحقق الثنائي:")
            except PhoneCodeInvalidError:
                await event.reply("❌ الكود غير صحيح. أعد المحاولة.")
            except Exception as e:
                await event.reply(f"❌ فشل تسجيل الدخول: {e}")
                adding_state.pop(user_id)

        elif step == 5:
            try:
                await state["client"].sign_in(password=text)
                session = state["client"].session.save()
                name = state["phone"]
                sessions[name] = session
                save_sessions()
                clients[name] = state["client"]
                adding_state.pop(user_id)
                await event.reply(f"✅ تم إضافة الجلسة `{name}`", buttons=main_menu())
            except Exception as e:
                await event.reply(f"❌ كلمة المرور خاطئة: {e}")
                adding_state.pop(user_id)

    # ============ رابط الصعود ============
    elif user_id in waiting_for_link:
        waiting_for_link.pop(user_id)
        await handle_link(event, text)

# ================== فك الروابط ==================
async def extract_entity_from_link(bot, link):
    try:
        if "joinchat" in link or "/+" in link or "t.me/+" in link:
            code = link.split("+")[-1]
            result = await bot(ImportChatInviteRequest(code))
            return result.chats[0]

        if "?" in link:
            link = link.split("?")[0]

        return await bot.get_entity(link)

    except Exception as e:
        raise Exception(f"❌ فشل استخراج الرابط:\n{e}")

# ================== صعود الحسابات ==================
async def handle_link(event, link):
    try:
        ent = await extract_entity_from_link(bot, link)
    except Exception as err:
        await event.respond(str(err), buttons=main_menu())
        return

    global current_chat
    current_chat = ent
    await event.respond("🔁 جارٍ صعود الحسابات...")

    for name, cl in clients.items():
        try:
            await cl(JoinChannelRequest(ent))
            await asyncio.sleep(1)
            await bot.send_message(event.chat_id, f"✅ [{name}] صعد الاتصال")
        except UserAlreadyParticipantError:
            await bot.send_message(event.chat_id, f"✅ [{name}] موجود مسبقاً")
        except Exception as ex:
            await bot.send_message(event.chat_id, f"❌ [{name}] خطأ: {ex}")

    await bot.send_message(event.chat_id, "✅ تم صعود الحسابات.", buttons=main_menu())

# ================== تشغيل ==================
async def main():
    load_sessions()
    await bot.start(bot_token=bot_token)
    await start_all_sessions()
    print("✅ البوت يعمل الآن...")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
