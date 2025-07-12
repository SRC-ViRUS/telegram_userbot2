# -*- coding: utf-8 -*-
import asyncio, json, os, random
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError

# ─── بيانات البوت ─────────────────────────────────────────────
api_id    = 20507759
api_hash  = "225d3a24d84c637b3b816d13cc7bd766"
bot_token = "7644214767:AAGOlYEiyF6yFWxiIX_jlwo9Ssj_Cb95oLU"
SESS_FILE = "sessions.json"

# ─── حاويات عامّة ────────────────────────────────────────────
sessions, clients = {}, {}
add_state, send_state, save_state, spam_tasks = {}, {}, {}, {}
stored_insults = {"ولد": set(), "بنت": set()}

# ─── بوت ─────────────────────────────────────────────────────
bot = TelegramClient("bot", api_id, api_hash)

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
            await c.start()
            clients[usr] = c
            print(f"[+] {usr} ON")
        except Exception as e:
            print(f"[!] {usr} FAIL: {e}")

def menu():
    return [
        [Button.inline("📋 الجلسات", b"list"), Button.inline("📥 إضافة جلسة", b"add")],
        [Button.inline("🗑️ حذف جلسة", b"del"), Button.inline("✉️ إرسال رسالة", b"snd")],
        [Button.inline("😈 انجب شتيمة", b"insult")],
        [Button.inline("🔥 قائمة الشتائم", b"insults_menu")]
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
    else:
        txt = "🚫 لا توجد جلسات."
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
        sessions.pop(n)
        save_sessions()
        if (c:=clients.pop(n,None)):
            await c.disconnect()
        await e.edit(f"حُذفت `{n}`", parse_mode="md", buttons=menu())
    else:
        await e.answer("❌ غير موجودة.", alert=True)

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
            st["phone"]=txt
            st["client"]=TelegramClient(StringSession(), st["api_id"], st["api_hash"])
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
            sessions[st["phone"]] = st["client"].session.save()
            save_sessions()
            clients[st["phone"]]  = st["client"]
            add_state.pop(uid); return await m.reply("تمت الإضافة ✅", buttons=menu())
        if st["step"]==5:
            try:
                await st["client"].sign_in(password=txt)
                sessions[st["phone"]] = st["client"].session.save()
                save_sessions()
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
                    bad+=1; print(e)
            return await m.reply(f"انتهى. ناجحة:{ok} | فاشلة:{bad}", buttons=menu())

    # -------- حفظ شتيمة مؤقت --------
    if uid in save_state and save_state[uid]["step"]==1 and txt.lower()!="الغاء":
        save_state[uid]["text"]=txt
        btns=[[Button.inline("👦 ولد","svb".encode()),Button.inline("👧 بنت","svg".encode())]]
        await m.reply("اختر الفئة:", buttons=btns)

# ─── زر إرسال رسالة (بدء) ───────────────────────────────────
@bot.on(events.CallbackQuery(data=b"snd"))
async def _(e):
    send_state[e.sender_id]={"step":1}
    await e.edit("اكتب النص الذي تريد إرساله لكل الجلسات:")

# ─── حفظ شتيمة (تبدأ برسالة زر) ────────────────────────────
@bot.on(events.CallbackQuery(data=b"insult"))
async def _(e):
    save_state[e.sender_id]={"step":1}
    await e.edit("أرسل الشتيمة (أي نص)، أو كلمة 'الغاء' لإلغاء:")

@bot.on(events.CallbackQuery(pattern=b"svb|svg"))
async def _(e):
    uid   = e.sender_id
    kind  = "ولد" if e.data==b"svb" else "بنت"
    if uid not in save_state:
        return await e.answer("لا يوجد شيء للحفظ.", alert=True)
    insult = save_state[uid]["text"]
    if insult in stored_insults[kind]:
        txt="⚠️ موجودة سابقًا."
    else:
        stored_insults[kind].add(insult); txt="✅ حُفظت."
    save_state.pop(uid, None)
    await e.edit(f"{txt}\nالفئة: {kind}", buttons=menu())

# ─── زر إلغاء (على حفظ الشتيمة) ────────────────────────────
@bot.on(events.NewMessage(pattern=r"(?i)^الغاء$"))
async def _(m):
    if save_state.pop(m.sender_id, None):
        return await m.reply("أُلغي الطلب.", buttons=menu())

# ─── قائمة الشتائم الرئيسية ──────────────────────────────────
@bot.on(events.CallbackQuery(data=b"insults_menu"))
async def insults_menu(e):
    await e.edit(
        "اختر من القائمة:",
        buttons=[
            [Button.inline("عرض شتائم الأولاد", b"show_insults_boys")],
            [Button.inline("عرض شتائم البنات", b"show_insults_girls")],
            [Button.inline("إرسال شتيمة عشوائية", b"send_random_insult")],
            [Button.inline("رجوع", b"back_menu")]
        ]
    )

@bot.on(events.CallbackQuery(pattern=b"show_insults_boys"))
async def show_boys(e):
    insults = "\n".join(stored_insults["ولد"]) or "لا توجد شتائم."
    await e.edit(f"شتائم الأولاد:\n{insults}", buttons=[Button.inline("رجوع", b"insults_menu")])

@bot.on(events.CallbackQuery(pattern=b"show_insults_girls"))
async def show_girls(e):
    insults = "\n".join(stored_insults["بنت"]) or "لا توجد شتائم."
    await e.edit(f"شتائم البنات:\n{insults}", buttons=[Button.inline("رجوع", b"insults_menu")])

@bot.on(events.CallbackQuery(pattern=b"send_random_insult"))
async def send_random(e):
    all_insults = list(stored_insults["ولد"]) + list(stored_insults["بنت"])
    if not all_insults:
        await e.answer("ماكو شتائم محفوظة.", alert=True)
        return
    insult = random.choice(all_insults)
    await e.edit(f"شتيمة عشوائية:\n{insult}", buttons=[Button.inline("رجوع", b"insults_menu")])

@bot.on(events.CallbackQuery(pattern=b"back_menu"))
async def back_to_menu(e):
    await e.edit("🟢 أهلاً، اختر:", buttons=menu())

# ─── تشغيل البوت ────────────────────────────────────────────
async def main():
    load_sessions()
    await spin_all_sessions()
    await bot.start(bot_token=bot_token)
    print("Bot online ✓")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
