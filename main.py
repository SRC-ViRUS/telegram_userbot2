import asyncio, json, os, re
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError, PhoneCodeInvalidError,
    UserAlreadyParticipantError
)
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest

#──────────── بيانات البوت ────────────
api_id    = 20507759
api_hash  = "225d3a24d84c637b3b816d13cc7bd766"
bot_token = "7644214767:AAGOlYEiyF6yFWxiIX_jlwo9Ssj_Cb95oLU"
SESS_FILE = "sessions.json"

#──────────── متغيّرات عامّة ────────────
sessions, clients = {}, {}
current_chat      = None
waiting_for_link  = set()          # user_ids بانتظار رابط
adding_state      = {}             # حالة إضافة جلسة
send_message_state = {}            # user_id: {"step": 1/2, "text": ""}

bot = TelegramClient("bot", api_id, api_hash)

#──────────── أدوات جلسات ────────────
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
            print(f"[!] {name} failed: {e}")

#──────────── أزرار الواجهة ────────────
def menu():
    return [
        [Button.inline("🚀 صعود الاتصال", b"connect"),
         Button.inline("🛑 نزول الاتصال", b"disconnect")],
        [Button.inline("📋 عرض الجلسات", b"list"),
         Button.inline("📥 إضافة جلسة", b"add")],
        [Button.inline("🗑️ حذف جلسة", b"del"),
         Button.inline("✉️ إرسال رسالة", b"sendmsg")]
    ]

def sessions_btns(prefix):          # أزرار بأسماء الجلسات
    return [[Button.inline(n, f"{prefix}:{n}".encode())] for n in sessions]

#──────────── /start ────────────
@bot.on(events.NewMessage(pattern="/start"))
async def cmd_start(e):
    await e.respond("👋 أهلاً بك، اختر من الأزرار:", buttons=menu())

#──────────── عرض الجلسات ────────────
@bot.on(events.CallbackQuery(data=b"list"))
async def list_sess(e):
    txt = "📋 **الجلسات الحالية:**\n"
    txt += "لا توجد جلسات." if not sessions else "\n".join(f"- `{s}`" for s in sessions)
    await e.edit(txt, buttons=menu(), parse_mode="md")

#──────────── حذف جلسة ────────────
@bot.on(events.CallbackQuery(data=b"del"))
async def del_choose(e):
    if not sessions:
        await e.answer("🚫 لا توجد جلسات.")
        return
    await e.edit("🗑️ اختر جلسة للحذف:", buttons=sessions_btns("del"))

@bot.on(events.CallbackQuery(pattern=b"del:(.+)"))
async def del_done(e):
    name = e.data.decode().split(":",1)[1]
    sessions.pop(name, None); save_sessions()
    c = clients.pop(name, None)
    if c: await c.disconnect()
    await e.edit(f"🗑️ حُذفت الجلسة `{name}`.", buttons=menu(), parse_mode="md")

#──────────── إضافة جلسة ────────────
@bot.on(events.CallbackQuery(data=b"add"))
async def add_begin(e):
    adding_state[e.sender_id] = {"step":1}
    await e.edit("📥 *إضافة جلسة*\nأرسل `api_id`:", parse_mode="md")

@bot.on(events.NewMessage)
async def add_flow_or_link(msg):
    uid, txt = msg.sender_id, msg.raw_text.strip()

    #── إضافة جلسة
    if uid in adding_state:
        st, step = adding_state[uid], adding_state[uid]["step"]
        if step == 1:
            if not txt.isdigit():
                await msg.reply("❌ api_id يجب رقم.")
                return
            st["api_id"] = int(txt); st["step"] = 2
            await msg.reply("🔑 أرسل `api_hash`:")
        elif step == 2:
            st["api_hash"] = txt; st["step"] = 3
            await msg.reply("📞 أرسل رقم الهاتف (+):")
        elif step == 3:
            st["phone"] = txt
            st["client"] = TelegramClient(StringSession(), st["api_id"], st["api_hash"])
            await st["client"].connect()
            try:
                await st["client"].send_code_request(st["phone"])
                st["step"] = 4
                await msg.reply("✉️ أرسل كود التفعيل:")
            except Exception as e:
                adding_state.pop(uid)
                await msg.reply(f"❌ خطأ إرسال الكود: {e}")
        elif step == 4:
            cl = st["client"]
            try:
                await cl.sign_in(st["phone"], txt.replace(" ", ""))
                sess = cl.session.save(); name = st["phone"]
                sessions[name] = sess; save_sessions(); clients[name] = cl
                adding_state.pop(uid)
                await msg.reply(f"✅ أُضيفت الجلسة `{name}`", buttons=menu(), parse_mode="md")
            except SessionPasswordNeededError:
                st["step"] = 5
                await msg.reply("🔐 أرسل كلمة مرور 2FA:")
            except PhoneCodeInvalidError:
                await msg.reply("❌ الكود خاطئ، حاول ثانية.")
            except Exception as e:
                adding_state.pop(uid)
                await msg.reply(f"❌ فشل: {e}")
        elif step == 5:
            cl = st["client"]
            try:
                await cl.sign_in(password=txt)
                sess = cl.session.save(); name = st["phone"]
                sessions[name] = sess; save_sessions(); clients[name] = cl
                adding_state.pop(uid)
                await msg.reply(f"✅ أُضيفت الجلسة `{name}`", buttons=menu(), parse_mode="md")
            except Exception as e:
                adding_state.pop(uid)
                await msg.reply(f"❌ كلمة المرور خاطئة: {e}")
        return

    #── إرسال رسالة لكل الجلسات
    if uid in send_message_state:
        state = send_message_state[uid]
        if state["step"] == 1:
            state["text"] = txt
            state["step"] = 2
            await msg.reply("🎯 إلى من تريد إرسال الرسالة؟ (يوزر / آيدي / رابط كروب)")
        elif state["step"] == 2:
            target = txt
            text = state["text"]
            del send_message_state[uid]

            await msg.reply("🚀 جارٍ إرسال الرسالة من جميع الحسابات...")
            for name, cl in clients.items():
                try:
                    ent = await cl.get_entity(target)
                    await cl.send_message(ent, text)
                    await bot.send_message(msg.chat_id, f"✅ [{name}] أرسل الرسالة")
                    await asyncio.sleep(1)
                except Exception as ex:
                    await bot.send_message(msg.chat_id, f"❌ [{name}] فشل الإرسال: {ex}")
            await bot.send_message(msg.chat_id, "✅ تمت عملية الإرسال.", buttons=menu())
            return

    #── رابط الصعود
    if uid in waiting_for_link:
        waiting_for_link.discard(uid)
        await handle_link(msg, txt)

#──────────── صعود الاتصال ────────────
@bot.on(events.CallbackQuery(data=b"connect"))
async def connect_btn(e):
    waiting_for_link.add(e.sender_id)
    await e.edit("📨 أرسل رابط القناة / الكروب / المكالمة:")

#──────────── نزول الاتصال ────────────
@bot.on(events.CallbackQuery(data=b"disconnect"))
async def disconnect_btn(e):
    if not current_chat:
        await e.edit("⚠️ لا يوجد كروب محدّد.", buttons=menu())
        return
    await e.edit("🔁 نزول الحسابات...")
    for n, cl in clients.items():
        try:
            await cl(LeaveChannelRequest(current_chat))
            await asyncio.sleep(1)
            await bot.send_message(e.chat_id, f"⬇️ [{n}] خرج")
        except Exception as er:
            await bot.send_message(e.chat_id, f"❌ [{n}] خطأ: {er}")
    await bot.send_message(e.chat_id, "✅ تم النزول.", buttons=menu())

#──────────── صعود – معالجة الرابط لكل حساب ────────────
async def handle_link(event, link):
    await event.reply("🔁 جارٍ صعود الحسابات...")

    for name, cl in clients.items():
        try:
            if "joinchat" in link or "t.me/+" in link:
                code = link.split("+")[-1]
                await cl(ImportChatInviteRequest(code))
            else:
                base = link.split("?")[0]  # يزيل ?videochat
                ent  = await cl.get_entity(base)
                await cl(JoinChannelRequest(ent))

            await asyncio.sleep(1)
            await bot.send_message(event.chat_id, f"✅ [{name}] صعد")
        except UserAlreadyParticipantError:
            await bot.send_message(event.chat_id, f"✅ [{name}] موجود")
        except Exception as ex:
            await bot.send_message(event.chat_id, f"❌ [{name}] خطأ: {ex}")

    global current_chat
    current_chat = base if "base" in locals() else link
    await bot.send_message(event.chat_id, "✅ اكتملت العملية.", buttons=menu())

#──────────── التشغيل ────────────
async def main():
    load_sessions()
    await bot.start(bot_token=bot_token)
    await start_all_sessions()
    print(">> Bot running ...")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
