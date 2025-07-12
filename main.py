import asyncio, json, os, re, time
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError, PhoneCodeInvalidError,
    UserAlreadyParticipantError
)
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest

# ─── بيانات البوت ──────────────────────────────────────────────────────────
api_id    = 20507759
api_hash  = "225d3a24d84c637b3b816d13cc7bd766"
bot_token = "7644214767:AAGOlYEiyF6yFWxiIX_jlwo9Ssj_Cb95oLU"

SESS_FILE = "sessions.json"

# ─── متغيّرات global ───────────────────────────────────────────────────────
sessions: dict[str, str]  = {}   # {اسم: string_session}
clients:  dict[str, TelegramClient] = {}
current_chat = None              # آخر كروب/قناة تم الصعود عليها
waiting_for_link: set[int] = set()
adding_state: dict[int, dict] = {}  # حالة إضافة جلسة لكل مستخدم

# ─── إنشاء بوت ─────────────────────────────────────────────────────────────
bot = TelegramClient("bot", api_id, api_hash)

# ─── تحميل/حفظ الجلسات ────────────────────────────────────────────────────
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
            c = TelegramClient(StringSession(s), api_id, api_hash)
            await c.start()
            clients[name] = c
            print(f"[+] Session started: {name}")
        except Exception as e:
            print(f"[!] Fail {name}: {e}")

# ─── واجهة الأزرار ─────────────────────────────────────────────────────────
def main_menu():
    return [
        [Button.inline("🚀 صعود الاتصال", b"connect"), Button.inline("🛑 نزول الاتصال", b"disconnect")],
        [Button.inline("📋 عرض الجلسات", b"list"),   Button.inline("📥 إضافة جلسة", b"add")],
        [Button.inline("🗑️ حذف جلسة", b"del")]
    ]

def sessions_buttons(prefix: str):
    return [[Button.inline(name, f"{prefix}:{name}".encode())] for name in sessions]

# ─── /start ────────────────────────────────────────────────────────────────
@bot.on(events.NewMessage(pattern="/start"))
async def start_cmd(e):
    await e.respond("👋 أهلاً بك، اختر من الأزرار:", buttons=main_menu())

# ─── عرض الجلسات ───────────────────────────────────────────────────────────
@bot.on(events.CallbackQuery(data=b"list"))
async def list_sessions(e):
    txt = "📋 **الجلسات الحالية:**\n"
    if not sessions:
        txt += "لا توجد جلسات محفوظة."
    else:
        txt += "\n".join(f"- `{s}`" for s in sessions)
    await e.edit(txt, buttons=main_menu())

# ─── إضافة جلسة ────────────────────────────────────────────────────────────
@bot.on(events.CallbackQuery(data=b"add"))
async def add_session_start(e):
    adding_state[e.sender_id] = {"step": 1}
    await e.edit("📥 *إضافة جلسة جديدة*\nأرسل `api_id`:", parse_mode="md")

@bot.on(events.NewMessage)
async def add_session_flow(msg):
    uid, text = msg.sender_id, msg.raw_text.strip()
    if uid not in adding_state:
        return

    st = adding_state[uid]
    step = st["step"]

    if step == 1:
        if not text.isdigit():
            await msg.reply("❌ يجب أن يكون رقمًا.")
            return
        st["api_id"] = int(text); st["step"] = 2
        await msg.reply("🔑 أرسل `api_hash`:")

    elif step == 2:
        st["api_hash"] = text; st["step"] = 3
        await msg.reply("📞 أرسل رقم الهاتف (+):")

    elif step == 3:
        st["phone"] = text
        st["client"] = TelegramClient(StringSession(), st["api_id"], st["api_hash"])
        await st["client"].connect()
        try:
            await st["client"].send_code_request(st["phone"])
            st["step"] = 4
            await msg.reply("✉️ تم إرسال الكود، أرسله:")
        except Exception as e:
            await msg.reply(f"❌ خطأ: {e}")
            adding_state.pop(uid)

    elif step == 4:
        try:
            await st["client"].sign_in(st["phone"], text.replace(" ", ""))
            sess = st["client"].session.save()
            name = st["phone"]
            sessions[name] = sess; save_sessions(); clients[name] = st["client"]
            adding_state.pop(uid)
            await msg.reply(f"✅ أُضيفت الجلسة `{name}`", buttons=main_menu(), parse_mode="md")
        except SessionPasswordNeededError:
            st["step"] = 5
            await msg.reply("🔐 أرسل كلمة مرور 2FA:")
        except PhoneCodeInvalidError:
            await msg.reply("❌ الكود خاطئ، أعد إرساله.")
        except Exception as e:
            adding_state.pop(uid)
            await msg.reply(f"❌ فشل: {e}")

    elif step == 5:
        try:
            await st["client"].sign_in(password=text)
            sess = st["client"].session.save()
            name = st["phone"]
            sessions[name] = sess; save_sessions(); clients[name] = st["client"]
            adding_state.pop(uid)
            await msg.reply(f"✅ أُضيفت الجلسة `{name}`", buttons=main_menu(), parse_mode="md")
        except Exception as e:
            adding_state.pop(uid)
            await msg.reply(f"❌ كلمة المرور خاطئة: {e}")

# ─── حذف جلسة ───────────────────────────────────────────────────────────────
@bot.on(events.CallbackQuery(data=b"del"))
async def del_choose(e):
    if not sessions:
        await e.answer("🚫 لا توجد جلسات.")
        return
    await e.edit("🗑️ اختر جلسة للحذف:", buttons=sessions_buttons("del"))

@bot.on(events.CallbackQuery(pattern=b"del:(.+)"))
async def del_confirm(e):
    name = e.data.decode().split(":",1)[1]
    sessions.pop(name, None); save_sessions()
    cl = clients.pop(name, None)
    if cl: await cl.disconnect()
    await e.edit(f"🗑️ حُذفت الجلسة `{name}`.", buttons=main_menu(), parse_mode="md")

# ─── صعود/نزول الاتصال ─────────────────────────────────────────────────────
@bot.on(events.CallbackQuery(data=b"connect"))
async def connect_btn(e):
    waiting_for_link.add(e.sender_id)
    await e.edit("📨 أرسل رابط القناة/الكروب/المكالمة:")

@bot.on(events.CallbackQuery(data=b"disconnect"))
async def disconnect_btn(e):
    if not current_chat:
        await e.edit("⚠️ لم يتم تحديد كروب.", buttons=main_menu())
        return
    await e.edit("🔁 نزول الحسابات...")
    for name, cl in clients.items():
        try:
            await cl(LeaveChannelRequest(current_chat))
            await asyncio.sleep(1)
            await bot.send_message(e.chat_id, f"⬇️ [{name}] خرج")
        except Exception as er:
            await bot.send_message(e.chat_id, f"❌ [{name}] خطأ: {er}")
    await bot.send_message(e.chat_id, "✅ تم النزول.", buttons=main_menu())

# ─── استقبال الرسائل العامة (لينك الصعود) ─────────────────────────────────
@bot.on(events.NewMessage)
async def link_or_state(event):
    uid, txt = event.sender_id, event.raw_text.strip()
    if uid in waiting_for_link:
        waiting_for_link.discard(uid)
        await handle_link(event, txt)

# ─── استخلاص الكيان من أي رابط ────────────────────────────────────────────
async def extract_ent(link: str):
    if "joinchat" in link or re.search(r"t\.me/\+\w+", link):
        code = link.split("+")[-1]
        return (await bot(ImportChatInviteRequest(code))), "invite", code

    if "?" in link:      # رابط مكالمة
        link = link.split("?")[0]

    ent = await bot.get_entity(link)
    return ent, "public", None

# ─── تنفيذ الصعود لكل الجلسات ──────────────────────────────────────────────
async def handle_link(event, link):
    try:
        ent, ltype, code = await extract_ent(link)
    except Exception as err:
        await event.reply(f"❌ {err}", buttons=main_menu())
        return

    global current_chat
    current_chat = ent
    await event.reply("🔁 صعود الحسابات...")

    for name, cl in clients.items():
        try:
            if ltype == "invite":
                await cl(ImportChatInviteRequest(code))
            else:
                await cl(JoinChannelRequest(ent))
            await asyncio.sleep(1)
            await bot.send_message(event.chat_id, f"✅ [{name}] صعد")
        except UserAlreadyParticipantError:
            await bot.send_message(event.chat_id, f"✅ [{name}] موجود")
        except Exception as ex:
            await bot.send_message(event.chat_id, f"❌ [{name}] خطأ: {ex}")

    await bot.send_message(event.chat_id, "✅ صعدت كل الحسابات.", buttons=main_menu())

# ─── التشغيل الرئيسي ─────────────────────────────────────────────────────
async def main():
    load_sessions()
    await bot.start(bot_token=bot_token)
    await start_all_sessions()
    print(">> Bot running ...")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
