# -*- coding: utf-8 -*-
import asyncio, random
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError

# ─── بيانات البوت ─────────────────────────────────────────────
api_id    = 20507759
api_hash  = "225d3a24d84c637b3b816d13cc7bd766"
bot_token = "7644214767:AAGOlYEiyF6yFWxiIX_jlwo9Ssj_Cb95oLU"

# ─── حاويات عامّة ────────────────────────────────────────────
sessions, clients = {}, {}
add_state, send_state, save_state, attack_state, insult_send_state = {}, {}, {}, {}, {}
stored_insults = {"ولد": set(), "بنت": set()}

# ─── بوت ─────────────────────────────────────────────────────
bot = TelegramClient("bot", api_id, api_hash)

# ─── وظائف مساندة ────────────────────────────────────────────
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
        [Button.inline("🖋️ إضافة شتيمة", b"add_insult"), Button.inline("📚 عرض شتائم ولد", b"show_insults_boy")],
        [Button.inline("📚 عرض شتائم بنت", b"show_insults_girl"), Button.inline("🔥 هجوم", b"attack")]
    ]

def sess_btns(pref): 
    return [[Button.inline(n, f"{pref}:{n}".encode())] for n in sessions]

# ─── /start ──────────────────────────────────────────────────
@bot.on(events.NewMessage(pattern=r"^/start$"))
async def start_handler(e):
    await e.respond("🟢 أهلاً، اختر:", buttons=menu())

# ─── عرض الجلسات ─────────────────────────────────────────────
@bot.on(events.CallbackQuery(data=b"list"))
async def list_sessions(e):
    if sessions:
        txt = "📂 الجلسات:\n" + "\n".join(f"- `{u}`" for u in sessions)
    else:
        txt = "🚫 لا توجد جلسات."
    await e.edit(txt, parse_mode="md", buttons=menu())

# ─── حذف جلسة ────────────────────────────────────────────────
@bot.on(events.CallbackQuery(data=b"del"))
async def delete_session_menu(e):
    if not sessions:
        return await e.answer("🚫 لا جلسات.", alert=True)
    await e.edit("🗑️ اختر:", buttons=sess_btns("rm"))

@bot.on(events.CallbackQuery(pattern=b"rm:(.+)"))
async def delete_session(e):
    n = e.data.decode().split(":",1)[1]
    if n in sessions:
        sessions.pop(n)
        if (c:=clients.pop(n,None)):
            await c.disconnect()
        await e.edit(f"حُذفت `{n}`", parse_mode="md", buttons=menu())
    else:
        await e.answer("❌ غير موجودة.", alert=True)

# ─── إضافة جلسة (حوار) ───────────────────────────────────────
@bot.on(events.CallbackQuery(data=b"add"))
async def add_session_start(e):
    add_state[e.sender_id] = {"step":1}
    await e.edit("أرسل api_id:")

@bot.on(events.NewMessage)
async def all_handler(m):
    uid, txt = m.sender_id, m.raw_text.strip()

    # إضافة جلسة
    if uid in add_state:
        st = add_state[uid]
        if st["step"] == 1:
            if not txt.isdigit():
                return await m.reply("رقم فقط.")
            st["api_id"] = int(txt)
            st["step"] = 2
            return await m.reply("أرسل api_hash:")
        if st["step"] == 2:
            st["api_hash"] = txt
            st["step"] = 3
            return await m.reply("أرسل رقم الهاتف مع +:")
        if st["step"] == 3:
            st["phone"] = txt
            st["client"] = TelegramClient(StringSession(), st["api_id"], st["api_hash"])
            await st["client"].connect()
            try:
                await st["client"].send_code_request(txt)
                st["step"] = 4
                return await m.reply("الكود:")
            except Exception as e:
                add_state.pop(uid)
                return await m.reply(f"خطأ: {e}")
        if st["step"] == 4:
            try:
                await st["client"].sign_in(st["phone"], txt)
            except SessionPasswordNeededError:
                st["step"] = 5
                return await m.reply("كلمة مرور 2FA:")
            except PhoneCodeInvalidError:
                return await m.reply("كود خطأ.")
            sessions[st["phone"]] = st["client"].session.save()
            clients[st["phone"]] = st["client"]
            add_state.pop(uid)
            return await m.reply("تمت الإضافة ✅", buttons=menu())
        if st["step"] == 5:
            try:
                await st["client"].sign_in(password=txt)
                sessions[st["phone"]] = st["client"].session.save()
                clients[st["phone"]] = st["client"]
                add_state.pop(uid)
                return await m.reply("تمت الإضافة ✅", buttons=menu())
            except Exception as e:
                add_state.pop(uid)
                return await m.reply(f"خطأ: {e}")

    # إرسال رسالة
    if uid in send_state:
        st = send_state[uid]
        if st["step"] == 1:
            st["msg"] = txt
            st["step"] = 2
            return await m.reply("الهدف (@user أو id أو رابط):")
        if st["step"] == 2:
            target = txt
            send_state.pop(uid)
            await m.reply("جارٍ الإرسال...")
            ok, bad = 0, 0
            for n, cl in clients.items():
                try:
                    await cl.send_message(await cl.get_entity(target), st["msg"])
                    ok += 1
                except Exception as e:
                    bad += 1
                    print(e)
            return await m.reply(f"انتهى. ناجحة:{ok} | فاشلة:{bad}", buttons=menu())

    # إضافة شتيمة (اختيار ولد أو بنت)
    if uid in save_state:
        st = save_state[uid]
        if st.get("step") == 1 and txt.lower() != "الغاء":
            st["text"] = txt
            btns = [[Button.inline("👦 ولد", b"save_boy"), Button.inline("👧 بنت", b"save_girl")]]
            st["step"] = 2
            await m.reply("اختر الفئة:", buttons=btns)
        elif st.get("step") == 2 and txt.lower() == "الغاء":
            save_state.pop(uid, None)
            await m.reply("أُلغي الطلب.", buttons=menu())

    # هجوم (إرسال شتائم)
    if uid in attack_state and attack_state[uid]["step"] == 2:
        target = txt
        kind = attack_state[uid]["type"]
        attack_state.pop(uid)
        ok, bad = 0, 0

        for cl_name, cl in clients.items():
            try:
                insults = random.sample(stored_insults[kind], min(5, len(stored_insults[kind])))
                for insult in insults:
                    await cl.send_message(target, insult)
                await asyncio.sleep(30)
                insults = random.sample(stored_insults[kind], min(5, len(stored_insults[kind])))
                for insult in insults:
                    await cl.send_message(target, insult)
                try:
                    await cl.delete_dialog(target)
                except:
                    pass
                ok += 1
            except Exception as e:
                bad += 1
                print(f"هجوم فشل لجلسة {cl_name}: {e}")

        await m.reply(f"🔥 تم الهجوم على {target}\n✅ ناجح: {ok} | ❌ فشل: {bad}", buttons=menu())

    # إرسال الشتائم عشوائيًا لشخص
    if uid in insult_send_state:
        st = insult_send_state[uid]
        if st["step"] == 1:
            st["target"] = txt
            insult_send_state[uid]["step"] = 2
            await m.reply("جاري إرسال الشتائم...")
            kind = st["kind"]
            target = st["target"]
            for cl in clients.values():
                insults = random.sample(stored_insults[kind], min(5, len(stored_insults[kind])))
                for insult in insults:
                    await cl.send_message(target, insult)
                    await asyncio.sleep(5)
                await asyncio.sleep(30)
            insult_send_state.pop(uid)
            await m.reply("تم إرسال الشتائم بنجاح.", buttons=menu())

# ─── زر إرسال رسالة (بدء) ───────────────────────────────────
@bot.on(events.CallbackQuery(data=b"snd"))
async def start_send_message(e):
    send_state[e.sender_id] = {"step": 1}
    await e.edit("اكتب النص الذي تريد إرساله لكل الجلسات:")

# ─── زر إضافة شتيمة ──────────────────────────────────────────
@bot.on(events.CallbackQuery(data=b"add_insult"))
async def start_add_insult(e):
    save_state[e.sender_id] = {"step": 1}
    await e.edit("أرسل الشتيمة (أي نص)، أو كلمة 'الغاء' لإلغاء:")

# ─── حفظ الشتيمة ولد أو بنت ───────────────────────────────────
@bot.on(events.CallbackQuery(pattern=b"save_boy|save_girl"))
async def save_insult_handler(e):
    uid = e.sender_id
    if uid not in save_state:
        return await e.answer("لا يوجد شيء للحفظ.", alert=True)
    kind = "ولد" if e.data == b"save_boy" else "بنت"
    insult = save_state[uid]["text"]
    if insult in stored_insults[kind]:
        txt = "⚠️ هذه الشتيمة موجودة سابقًا."
    else:
        stored_insults[kind].add(insult)
        txt = "✅ تم حفظ الشتيمة."
    save_state.pop(uid, None)
    await e.edit(f"{txt}\nالفئة: {kind}", buttons=menu())

# ─── عرض الشتائم ولد ─────────────────────────────────────────
@bot.on(events.CallbackQuery(data=b"show_insults_boy"))
async def show_boy_insults(e):
    if stored_insults["ولد"]:
        txt = "🧑 شتائم الولد:\n" + "\n".join(f"- {i}" for i in stored_insults["ولد"])
    else:
        txt = "🚫 لا توجد شتائم ولد."
    await e.edit(txt, buttons=menu())

# ─── عرض الشتائم بنت ─────────────────────────────────────────
@bot.on(events.CallbackQuery(data=b"show_insults_girl"))
async def show_girl_insults(e):
    if
