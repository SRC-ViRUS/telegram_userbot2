# -*- coding: utf-8 -*-
import asyncio, json, os
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import (SessionPasswordNeededError,
                             PhoneCodeInvalidError,
                             UserAlreadyParticipantError)
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest

# ── بيانات البوت ───────────────────────────────────────────────
api_id    = 20507759
api_hash  = "225d3a24d84c637b3b816d13cc7bd766"
bot_token = "7644214767:AAGOlYEiyF6yFWxiIX_jlwo9Ssj_Cb95oLU"
SESS_FILE = "sessions.json"

# ── متغيّرات عامّة ───────────────────────────────────────────
sessions, clients               = {}, {}
current_chat_link               = None     # آخر رابط صعدنا عليه
waiting_for_link                = set()    # user_ids بانتظار الرابط
adding_state, send_message_state = {}, {}  # حالات حوار التفاعل

bot = TelegramClient("bot", api_id, api_hash)

# ── إدارة الجلسات ملفًا وتشغيلًا ──────────────────────────────
def load_sessions():
    global sessions
    sessions = json.load(open(SESS_FILE)) if os.path.exists(SESS_FILE) else {}

def save_sessions():
    json.dump(sessions, open(SESS_FILE, "w"), ensure_ascii=False, indent=2)

async def start_all_sessions():
    for name, s in sessions.items():
        try:
            c = TelegramClient(StringSession(s), api_id, api_hash)
            await c.start(); clients[name] = c
            print(f"[+] جلسة {name}")
        except Exception as e:
            print(f"[!] فشل {name}: {e}")

# ── أزرار الواجهة ─────────────────────────────────────────────
def menu():
    return [
        [Button.inline("🚀 صعود الاتصال", b"connect"),
         Button.inline("🛑 نزول الاتصال", b"disconnect")],
        [Button.inline("📋 الجلسات", b"list"),
         Button.inline("📥 إضافة جلسة", b"add")],
        [Button.inline("🗑️ حذف جلسة", b"del"),
         Button.inline("✉️ إرسال رسالة", b"sendmsg")]
    ]

def sessions_btns(prefix):
    return [[Button.inline(n, f"{prefix}:{n}".encode())] for n in sessions]

# ── /start ───────────────────────────────────────────────────
@bot.on(events.NewMessage(pattern="/start"))
async def start_cmd(e): await e.respond("🟢 اختر:", buttons=menu())

# ── عرض الجلسات ───────────────────────────────────────────────
@bot.on(events.CallbackQuery(data=b"list"))
async def list_sess(e):
    txt = "📋 الجلسات:\n" + ("\n".join(f"- `{n}`" for n in sessions) if sessions else "لا توجد.")
    await e.edit(txt, parse_mode="md", buttons=menu())

# ── حذف جلسة ─────────────────────────────────────────────────
@bot.on(events.CallbackQuery(data=b"del"))
async def del_pick(e):
    if not sessions: return await e.answer("🚫 لا جلسات.")
    await e.edit("🗑️ اختر جلسة:", buttons=sessions_btns("del"))

@bot.on(events.CallbackQuery(pattern=b"del:(.+)"))
async def del_done(e):
    name = e.data.decode().split(":",1)[1]
    sessions.pop(name, None); save_sessions()
    cl = clients.pop(name, None); await cl.disconnect() if cl else None
    await e.edit(f"🗑️ حذف `{name}`", parse_mode="md", buttons=menu())

# ── إضافة جلسة (حوار تفاعلي) ─────────────────────────────────
@bot.on(events.CallbackQuery(data=b"add"))
async def add_step1(e):
    adding_state[e.sender_id] = {"step":1}; await e.edit("api_id ؟")

@bot.on(events.NewMessage)
async def handle_all(msg):
    uid, txt = msg.sender_id, msg.raw_text.strip()

    # إضافة جلسة
    if uid in adding_state:
        st, step = adding_state[uid], adding_state[uid]["step"]
        if step == 1:
            if not txt.isdigit(): return await msg.reply("رقم فقط.")
            st["api_id"] = int(txt); st["step"]=2; return await msg.reply("api_hash ؟")
        if step == 2:
            st["api_hash"] = txt; st["step"]=3; return await msg.reply("رقم الهاتف (+) ؟")
        if step == 3:
            st["phone"] = txt
            st["client"]= TelegramClient(StringSession(), st["api_id"], st["api_hash"])
            await st["client"].connect()
            try:
                await st["client"].send_code_request(txt)
                st["step"]=4; return await msg.reply("الكود؟")
            except Exception as e:
                adding_state.pop(uid); return await msg.reply(f"خطأ: {e}")
        if step == 4:
            cl=st["client"]
            try:
                await cl.sign_in(st["phone"], txt.replace(" ",""))
            except SessionPasswordNeededError:
                st["step"]=5; return await msg.reply("كلمة مرور 2FA؟")
            except PhoneCodeInvalidError:
                return await msg.reply("كود غلط.")
            sessions[st["phone"]] = cl.session.save(); save_sessions(); clients[st["phone"]] = cl
            adding_state.pop(uid); return await msg.reply("✅ تمت الإضافة", buttons=menu())
        if step == 5:
            try:
                stc=st["client"]; await stc.sign_in(password=txt)
                sessions[st["phone"]] = stc.session.save(); save_sessions(); clients[st["phone"]] = stc
                adding_state.pop(uid); return await msg.reply("✅ تمت الإضافة", buttons=menu())
            except Exception as e:
                adding_state.pop(uid); return await msg.reply(f"خطأ: {e}")

    # إرسال رسالة
    if uid in send_message_state:
        state=send_message_state[uid]
        if state["step"]==1:
            state["text"]=txt; state["step"]=2
            return await msg.reply("🎯 الهدف (يوزر @ أو آيدي أو رابط)؟")
        target=txt; text=state["text"]; send_message_state.pop(uid)
        await msg.reply("🚀 إرسال...")
        for n,cl in clients.items():
            try:
                ent=await cl.get_entity(target); await cl.send_message(ent,text)
                await bot.send_message(msg.chat_id,f"✅ {n}")
            except Exception as ex:
                await bot.send_message(msg.chat_id,f"❌ {n}: {ex}")
        return await bot.send_message(msg.chat_id,"انتهى ✅",buttons=menu())

    # رابط الصعود
    if uid in waiting_for_link:
        waiting_for_link.discard(uid); await ascend_accounts(msg, txt)

# ── زر إرسال رسالة ───────────────────────────────────────────
@bot.on(events.CallbackQuery(data=b"sendmsg"))
async def sendmsg_btn(e):
    send_message_state[e.sender_id]={"step":1}
    await e.edit("📝 اكتب الرسالة لإرسالها:")

# ── صعود/نزول ────────────────────────────────────────────────
@bot.on(events.CallbackQuery(data=b"connect"))
async def connect_btn(e):
    waiting_for_link.add(e.sender_id)
    await e.edit("📨 أرسل الرابط (قناة/كروب/دعوة/مكالمة):")

@bot.on(events.CallbackQuery(data=b"disconnect"))
async def disconnect_btn(e):
    if not current_chat_link: return await e.edit("لا كروب محدد.",buttons=menu())
    await e.edit("نزول...")
    for n, cl in clients.items():
        try:
            ent=await cl.get_entity(current_chat_link.split("?")[0])
            await cl(LeaveChannelRequest(ent)); await asyncio.sleep(1)
            await bot.send_message(e.chat_id,f"⬇️ {n}")
        except Exception as er:
            await bot.send_message(e.chat_id,f"❌ {n}: {er}")
    await bot.send_message(e.chat_id,"تم ✅",buttons=menu())

# ── تنفيذ الصعود لكل الجلسات ─────────────────────────────────
async def ascend_accounts(event, link):
    await event.reply("صعود...")
    base = link.split("?")[0]
    for n, cl in clients.items():
        try:
            if "joinchat" in link or "t.me/+" in link:
                code=link.split("+")[-1]; await cl(ImportChatInviteRequest(code))
            else:
                ent=await cl.get_entity(base); await cl(JoinChannelRequest(ent))
            await bot.send_message(event.chat_id,f"✅ {n}")
            await asyncio.sleep(1)
        except UserAlreadyParticipantError:
            await bot.send_message(event.chat_id,f"🟢 {n} موجود")
        except Exception as ex:
            await bot.send_message(event.chat_id,f"❌ {n}: {ex}")
    global current_chat_link
    current_chat_link = link
    await bot.send_message(event.chat_id,"⬆️ اكتمل الصعود.",buttons=menu())

# ── تشغيل البوت ──────────────────────────────────────────────
async def main():
    load_sessions()
    await bot.start(bot_token=bot_token)
    await start_all_sessions()
    print("Bot online ✓")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
