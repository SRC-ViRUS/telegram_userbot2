# -*- coding: utf-8 -*-
import asyncio, os, json
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, UserAlreadyParticipantError, FloodWaitError
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest

api_id = 20507759
api_hash = "225d3a24d84c637b3b816d13cc7bd766"
bot_token = "7644214767:AAGOlYEiyF6yFWxiIX_jlwo9Ssj_Cb95oLU"

SESS_FILE = "sessions.json"
sessions, clients = {}, {}
if os.path.exists(SESS_FILE):
    sessions.update(json.load(open(SESS_FILE)))

def save_sessions():
    json.dump(sessions, open(SESS_FILE, "w"), ensure_ascii=False, indent=2)

bot = TelegramClient("bot", api_id, api_hash)
add_state, send_state, evil_state = {}, {}, {}

def menu():
    return [
        [Button.inline("📋 الجلسات", b"list"), Button.inline("📥 إضافة جلسة", b"add")],
        [Button.inline("🗑️ حذف جلسة", b"del"), Button.inline("✉️ إرسال رسالة", b"snd")],
        [Button.inline("🔥 خبث", b"evil")],
    ]

def sess_btns(tag):
    return [[Button.inline(u, f"{tag}:{u}".encode())] for u in sessions]

async def join_chat(client, link):
    try:
        if "joinchat" in link:
            code = link.split("/")[-1]
            await client(ImportChatInviteRequest(code))
        else:
            await client(JoinChannelRequest(link))
        return True
    except UserAlreadyParticipantError:
        return True
    except Exception:
        return False

@bot.on(events.NewMessage(pattern=r"^/start$"))
async def start(e):
    await e.respond("🟢 أهلاً، اختر من الأزرار:", buttons=menu())

@bot.on(events.CallbackQuery(data=b"list"))
async def list_cb(e):
    txt = "📂 الجلسات:\n" + ("\n".join(f"- `{u}`" for u in sessions) if sessions else "🚫 لا جلسات.")
    await e.edit(txt, parse_mode="md", buttons=menu())

@bot.on(events.CallbackQuery(data=b"del"))
async def del_menu(e):
    if not sessions:
        return await e.answer("🚫 لا جلسات.", alert=True)
    await e.edit("🗑️ اختر جلسة للحذف:", buttons=sess_btns("rm"))

@bot.on(events.CallbackQuery(pattern=b"rm:(.+)"))
async def del_exec(e):
    phone = e.data.decode().split(":",1)[1]
    if phone in sessions:
        sessions.pop(phone); save_sessions()
        if (c := clients.pop(phone, None)): await c.disconnect()
        await e.edit(f"❌ حُذفت `{phone}`", parse_mode="md", buttons=menu())
    else:
        await e.answer("غير موجودة.", alert=True)

@bot.on(events.CallbackQuery(data=b"add"))
async def add_start(e):
    add_state[e.sender_id] = {"step": 1}
    await e.edit("أرسل api_id:")

@bot.on(events.NewMessage)
async def flow_handler(m):
    uid = m.sender_id
    t = m.raw_text.strip()

    # ---------- إضافة جلسة ----------
    if uid in add_state:
        st = add_state[uid]
        if st["step"] == 1:
            if not t.isdigit(): return await m.reply("❌ رقم فقط.")
            st["api_id"] = int(t); st["step"] = 2
            return await m.reply("أرسل api_hash:")
        if st["step"] == 2:
            st["api_hash"] = t; st["step"] = 3
            return await m.reply("أرسل رقم الهاتف:")
        if st["step"] == 3:
            st["phone"] = t
            st["client"] = TelegramClient(StringSession(), st["api_id"], st["api_hash"])
            await st["client"].connect()
            try:
                await st["client"].send_code_request(t)
                st["step"] = 4
                return await m.reply("أرسل الكود:")
            except Exception as e:
                add_state.pop(uid); return await m.reply(f"خطأ: {e}")
        if st["step"] == 4:
            try:
                await st["client"].sign_in(st["phone"], t)
            except SessionPasswordNeededError:
                st["step"] = 5; return await m.reply("كلمة مرور 2FA:")
            except PhoneCodeInvalidError:
                return await m.reply("❌ الكود خطأ.")
            sessions[st["phone"]] = st["client"].session.save()
            clients[st["phone"]] = st["client"]
            save_sessions(); add_state.pop(uid)
            return await m.reply("✅ تمت الإضافة.", buttons=menu())
        if st["step"] == 5:
            try:
                await st["client"].sign_in(password=t)
                sessions[st["phone"]] = st["client"].session.save()
                clients[st["phone"]] = st["client"]
                save_sessions(); add_state.pop(uid)
                return await m.reply("✅ تمت الإضافة.", buttons=menu())
            except Exception as e:
                add_state.pop(uid); return await m.reply(f"❌ خطأ: {e}")

    # ---------- إرسال رسالة ----------
    if uid in send_state:
        st = send_state[uid]
        if st["step"] == 1:
            st["msg"] = t; st["step"] = 2
            return await m.reply("🎯 أرسل @يوزر أو رابط:")
        if st["step"] == 2:
            target = t
            send_state.pop(uid)
            await m.reply("🚀 جاري الإرسال...")
            ok, bad = 0, 0
            try: entity = await bot.get_entity(target)
            except: entity = target
            is_user = isinstance(entity, int) or str(entity).startswith("@")
            for ph, cl in clients.items():
                try:
                    if not is_user:
                        if not await join_chat(cl, target): bad += 1; continue
                        await asyncio.sleep(5)
                    await cl.send_message(entity, st["msg"])
                    ok += 1
                except FloodWaitError as fe:
                    await asyncio.sleep(fe.seconds)
                except Exception as e:
                    print(f"خطأ من {ph}: {e}")
                    bad += 1
            await m.reply(f"✅ تم.\nنجاح: {ok} | فشل: {bad}", buttons=menu())

    # ---------- زر خبث ----------
    if uid in evil_state:
        st = evil_state[uid]
        if st["step"] == 1:
            st["msg"] = t; st["step"] = 2
            return await m.reply("👤 أرسل قائمة اليوزرات (كل سطر @user):")
        if st["step"] == 2:
            evil_state.pop(uid)
            targets = [ln.strip() for ln in t.splitlines() if ln.strip()]
            await m.reply("🚀 جاري الإرسال...")
            for t in targets:
                for ph, cl in clients.items():
                    try:
                        ent = await cl.get_entity(t)
                        msg = await cl.send_message(ent, st["msg"])
                        await asyncio.sleep(3)
                        await cl.delete_messages(ent, msg.id, revoke=True)
                    except Exception as e:
                        print(f"[{ph}] خطأ مع {t}: {e}")
            await m.reply("✅ تمت الإزالة بعد 3 ثوانٍ.", buttons=menu())

@bot.on(events.CallbackQuery(data=b"snd"))
async def snd_btn(e):
    send_state[e.sender_id] = {"step": 1}
    await e.edit("✉️ أرسل الرسالة للإرسال:", buttons=[[Button.inline("🔙", b"back")]])

@bot.on(events.CallbackQuery(data=b"evil"))
async def evil_btn(e):
    evil_state[e.sender_id] = {"step": 1}
    await e.edit("🔥 أرسل نص الرسالة (خبث):", buttons=[[Button.inline("🔙", b"back")]])

@bot.on(events.CallbackQuery(data=b"back"))
async def back(e):
    await e.edit("🟢 عدنا للقائمة:", buttons=menu())

# ---------- تشغيل البوت والجلسات ----------
async def main():
    for ph, sess in sessions.items():
        c = TelegramClient(StringSession(sess), api_id, api_hash)
        await c.start(); clients[ph] = c
    await bot.start(bot_token=bot_token)
    print("✅ Bot is online")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
