# -*- coding: utf-8 -*-
import asyncio, json, os, random, re
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from telethon.tl.types import PeerChannel

# ─── بيانات البوت ─────────────────────────────────────────────
api_id    = 20507759
api_hash  = "225d3a24d84c637b3b816d13cc7bd766"
bot_token = "7644214767:AAGOlYEiyF6yFWxiIX_jlwo9Ssj_Cb95oLU"
SESS_FILE = "sessions.json"

# ─── حاويات عامّة ────────────────────────────────────────────
sessions, clients = {}, {}
add_state, send_state = {}, {}
tagall_state = {}

# ─── بوت ─────────────────────────────────────────────────────
bot = TelegramClient("bot", api_id, api_hash)

# ─── قائمة جمل التاكات العشوائية ─────────────────────────────
tag_messages = [
    "هاي يا شباب، لازم تشوفون هالشي!",
    "سلام عليكم، هاي رسالة مهمة!",
    "يلا يا حلوين، لا تنسون الموضوع!",
    "هذي الرسالة للكل، انتبهوا!",
    "تذكير سريع لكم جميعاً!"
]

# ─── وظائف مساندة ────────────────────────────────────────────
def load_sessions():
    if os.path.exists(SESS_FILE):
        sessions.update(json.load(open(SESS_FILE)))

def save_sessions():
    json.dump(sessions, open(SESS_FILE, "w"), ensure_ascii=False, indent=2)

async def spin_all_sessions():
    for usr, s in sessions.items():
        try:
            c = TelegramClient(StringSession(s), api_id, api_hash)
            await c.start(); clients[usr] = c
            print(f"[+] {usr} ON")
        except Exception as e:
            print(f"[!] {usr} FAIL: {e}")

def menu():
    return [
        [Button.inline("📋 الجلسات", b"list"), Button.inline("📥 إضافة جلسة", b"add")],
        [Button.inline("🗑️ حذف جلسة", b"del"), Button.inline("✉️ إرسال رسالة", b"snd")],
        [Button.inline("📢 تاك جماعي", b"tagall"), Button.inline("⏸️ وقف التاك", b"stop_tag")]
    ]

def sess_btns(pref): return [[Button.inline(n, f"{pref}:{n}".encode())] for n in sessions]

# ─── /start ──────────────────────────────────────────────────
@bot.on(events.NewMessage(pattern=r"^/start$"))
async def _(e): await e.respond("🟢 أهلاً، اختر:", buttons=menu())

# ─── عرض الجلسات ─────────────────────────────────────────────
@bot.on(events.CallbackQuery(data=b"list"))
async def _(e):
    if sessions:
        txt = "📂 الجلسات:\n" + "\n".join(f"- `{u}`" for u in sessions)
    else: txt = "🚫 لا توجد جلسات."
    await e.edit(txt, parse_mode="md", buttons=menu())

# ─── حذف جلسة ────────────────────────────────────────────────
@bot.on(events.CallbackQuery(data=b"del"))
async def _(e):
    if not sessions: return await e.answer("🚫 لا جلسات.", alert=True)
    await e.edit("🗑️ اختر:", buttons=sess_btns("rm"))

@bot.on(events.CallbackQuery(pattern=b"rm:(.+)"))
async def _(e):
    n = e.data.decode().split(":",1)[1]
    if n in sessions:
        sessions.pop(n); save_sessions()
        if (c:=clients.pop(n,None)): await c.disconnect()
        await e.edit(f"حُذفت `{n}`", parse_mode="md", buttons=menu())
    else: await e.answer("❌ غير موجودة.", alert=True)

# ─── إضافة جلسة (حوار) ───────────────────────────────────────
@bot.on(events.CallbackQuery(data=b"add"))
async def _(e):
    add_state[e.sender_id] = {"step":1}
    await e.edit("أرسل api_id:")

@bot.on(events.NewMessage)
async def all_handler(m):
    uid, txt = m.sender_id, m.raw_text.strip()

    # -------- إضافة جلسة --------
    if uid in add_state:
        st = add_state[uid]
        if st["step"]==1:
            if not txt.isdigit(): return await m.reply("رقم فقط.")
            st["api_id"]=int(txt); st["step"]=2; return await m.reply("أرسل api_hash:")
        if st["step"]==2:
            st["api_hash"]=txt; st["step"]=3; return await m.reply("أرسل رقم الهاتف مع +:")
        if st["step"]==3:
            st["phone"]=txt; st["client"]=TelegramClient(StringSession(),st["api_id"],st["api_hash"])
            await st["client"].connect()
            try:
                await st["client"].send_code_request(txt)
                st["step"]=4; return await m.reply("الكود:")
            except Exception as e:
                add_state.pop(uid); return await m.reply(f"خطأ: {e}")
        if st["step"]==4:
            try:
                await st["client"].sign_in(st["phone"], txt)
            except SessionPasswordNeededError:
                st["step"]=5; return await m.reply("كلمة مرور 2FA:")
            except PhoneCodeInvalidError:
                return await m.reply("كود خطأ.")
            sessions[st["phone"]] = st["client"].session.save(); save_sessions()
            clients[st["phone"]]  = st["client"]
            add_state.pop(uid); return await m.reply("تمت الإضافة ✅", buttons=menu())
        if st["step"]==5:
            try:
                await st["client"].sign_in(password=txt)
                sessions[st["phone"]] = st["client"].session.save(); save_sessions()
                clients[st["phone"]]  = st["client"]
                add_state.pop(uid); return await m.reply("تمت الإضافة ✅", buttons=menu())
            except Exception as e:
                add_state.pop(uid); return await m.reply(f"خطأ: {e}")

    # -------- إرسال رسالة --------
    if uid in send_state:
        st = send_state[uid]
        if st["step"]==1:
            st["msg"]=txt; st["step"]=2; return await m.reply("الهدف (@user أو id أو رابط):")
        if st["step"]==2:
            target = txt; send_state.pop(uid)
            await m.reply("جارٍ الإرسال...")
            ok, bad = 0,0
            for n,cl in clients.items():
                try:
                    await cl.send_message(await cl.get_entity(target), st["msg"])
                    ok+=1
                except Exception as e:
                    bad+=1
            return await m.reply(f"انتهى. ناجحة:{ok} | فاشلة:{bad}", buttons=menu())

    # -------- حالة تاك جماعي (تحديد يوزر المنشن) --------
    if uid in tagall_state:
        st = tagall_state[uid]
        if st["step"] == 1:
            st["user_to_tag"] = txt
            st["step"] = 2
            await m.reply("أرسل رابط المجموعة (رابط الكروب):")
            return
        elif st["step"] == 2:
            st["group_link"] = txt
            st["running"] = True
            st["step"] = 3

            # تحويل رابط المجموعة إلى Entity
            try:
                entity = await bot.get_entity(await get_entity_from_link(st["group_link"]))
            except Exception as e:
                tagall_state.pop(uid)
                await m.reply(f"❌ خطأ في الحصول على المجموعة:\n{e}", buttons=menu())
                return

            ok, bad = 0, 0
            for name, client in clients.items():
                if not st["running"]:
                    break
                try:
                    msg = random.choice(tag_messages)
                    text_to_send = f"{st['user_to_tag']}\n{msg}"
                    await client.send_message(entity, text_to_send)
                    ok += 1
                    await asyncio.sleep(2)
                except Exception:
                    bad += 1

            tagall_state.pop(uid)
            await m.reply(f"تم إرسال التاكات بواسطة {ok} جلسات.\nفشلت: {bad}", buttons=menu())
            return

# ─── دالة لتحويل رابط المجموعة إلى Entity ─────────────────────
async def get_entity_from_link(link):
    clean_link = re.sub(r'https?://t\.me/', '', link)
    if clean_link.startswith('c/'):
        channel_id = int(clean_link.split('/')[1])
        return PeerChannel(channel_id - 1000000000000)
    else:
        return clean_link

# ─── زر إرسال رسالة (بدء) ───────────────────────────────────
@bot.on(events.CallbackQuery(data=b"snd"))
async def _(e):
    send_state[e.sender_id]={"step":1}
    await e.edit("اكتب النص الذي تريد إرساله لكل الجلسات:")

# ─── زر التاك الجماعي (بدء) ─────────────────────────────────
@bot.on(events.CallbackQuery(data=b"tagall"))
async def _(e):
    uid = e.sender_id
    tagall_state[uid] = {"step": 1, "running": False}
    await e.edit("أرسل @username أو ID الشخص الذي تريد أن يتم ذكره:")

# ─── زر وقف التاك الجماعي ────────────────────────────────────
@bot.on(events.CallbackQuery(data=b"stop_tag"))
async def _(e):
    uid = e.sender_id
    if uid in tagall_state and tagall_state[uid].get("running", False):
        tagall_state[uid]["running"] = False
        await e.answer("تم إيقاف التاك الجماعي.", alert=True)
        await e.edit("⏸️ تم إيقاف التاك الجماعي.", buttons=menu())
    else:
        await e.answer("لا توجد عملية تاك جماعي شغالة حالياً.", alert=True)

# ─── تشغيل البوت ────────────────────────────────────────────
async def main():
    load_sessions()
    await spin_all_sessions()
    await bot.start(bot_token=bot_token)
    print("Bot online ✓")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
