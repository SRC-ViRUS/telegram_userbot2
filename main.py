# -*- coding: utf-8 -*-
import asyncio, json, os, traceback
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import (
    FloodWaitError, PhoneCodeInvalidError, SessionPasswordNeededError,
    UserAlreadyParticipantError
)
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest, DeleteMessagesRequest

# ─────── بيانات البوت ─────────────────────────────────────────
api_id    = 20507759
api_hash  = "225d3a24d84c637b3b816d13cc7bd766"
bot_token = "7644214767:AAGOlYEiyF6yFWxiIX_jlwo9Ssj_Cb95oLU"

# ─────── ملف الجلسات الدائم ──────────────────────────────────
SESS_FILE = "sessions.json"
sessions, clients = {}, {}

# ─────── حاويات الحوارات التفاعليّة ──────────────────────────
add_state, send_state, khabath_state, save_state = {}, {}, {}, {}

# ─────── تخزين الشتائم حسب الفئة ────────────────────────────
stored_insults = {"👦": set(), "👧": set()}

# ─────── تحميل الجلسات من الملف (إن وُجد) ───────────────────
if os.path.exists(SESS_FILE):
    sessions.update(json.load(open(SESS_FILE)))
    print(f"Loaded {len(sessions)} sessions")

# ─────── عميل البوت ─────────────────────────────────────────
bot = TelegramClient("bot", api_id, api_hash)

# ─────── مالك البوت (يُعيَّن أول مرة يستعمل /start) ────────
OWNER_ID = None

# ─────── واجهة الأزرار ──────────────────────────────────────
def menu():
    return [
        [Button.inline("📋 الجلسات", b"list"),   Button.inline("📥 إضافة جلسة", b"add")],
        [Button.inline("🗑️ حذف جلسة", b"del"),  Button.inline("✉️ إرسال رسالة", b"snd")],
        [Button.inline("➕ إضافة شتيمة", b"add_ins"), Button.inline("📤 استخراج الجلسات", b"export")],
        [Button.inline("👦 شتائم الولد", b"show_b"), Button.inline("👧 شتائم البنت", b"show_g")],
        [Button.inline("💀 خبث", b"khabath")]
    ]

def sess_btns(pref):
    return [[Button.inline(user, f"{pref}:{user}".encode())] for user in sessions]

# ─────── أدوات مساعدة ───────────────────────────────────────
def save_sessions():  # حفظ جلسات الحسابات
    json.dump(sessions, open(SESS_FILE, "w"), ensure_ascii=False, indent=2)

async def join_chat(client, link):
    """يحاول انضمام الحساب لرابط عام أو دعوة خاصة."""
    try:
        if "joinchat" in link:
            code = link.split("/")[-1]
            await client(ImportChatInviteRequest(code))
        else:
            await client(JoinChannelRequest(link))
        return True
    except UserAlreadyParticipantError:
        return True
    except Exception as e:
        print("join_chat error:", e)
        return False

async def is_owner(event):
    return event.sender_id == OWNER_ID

# ─────── /start ─────────────────────────────────────────────
@bot.on(events.NewMessage(pattern=r"^/start$"))
async def _(e):
    global OWNER_ID
    if OWNER_ID is None:
        OWNER_ID = e.sender_id
        await e.respond("✅ تم تسجيلك مالكًا للبوت.")
    await e.respond("🟢 مرحبًا، اختر من الأزرار:", buttons=menu())

# ─────── قائمة الجلسات ─────────────────────────────────────
@bot.on(events.CallbackQuery(data=b"list"))
async def _(e):
    if not await is_owner(e): return await e.answer("للمالك فقط", alert=True)
    if sessions:
        txt = "📂 الجلسات الحالية:\n" + "\n".join(f"- `{u}`" for u in sessions)
    else:
        txt = "🚫 لا توجد جلسات."
    await e.edit(txt, parse_mode="md", buttons=menu())

# ─────── حذف جلسة ──────────────────────────────────────────
@bot.on(events.CallbackQuery(data=b"del"))
async def _(e):
    if not await is_owner(e): return await e.answer("للمالك فقط", alert=True)
    if not sessions: return await e.answer("لا جلسات.", alert=True)
    await e.edit("🗑️ اختر الجلسة لحذفها:", buttons=sess_btns("rm"))

@bot.on(events.CallbackQuery(pattern=b"rm:(.+)"))
async def _(e):
    if not await is_owner(e): return
    user = e.data.decode().split(":",1)[1]
    if user in sessions:
        sessions.pop(user); save_sessions()
        if (c:=clients.pop(user,None)): await c.disconnect()
        await e.edit(f"❌ حُذفت `{user}`", parse_mode="md", buttons=menu())
    else:
        await e.answer("غير موجودة.", alert=True)

# ─────── إضافة جلسة (خطوات) ───────────────────────────────
@bot.on(events.CallbackQuery(data=b"add"))
async def _(e):
    if not await is_owner(e): return await e.answer("للمالك فقط", alert=True)
    add_state[e.sender_id] = {"step":1}
    await e.edit("أرسل api_id:")

@bot.on(events.NewMessage)
async def add_session_flow(m):
    uid, txt = m.sender_id, m.raw_text.strip()
    if uid not in add_state: return
    st = add_state[uid]

    if st["step"]==1:
        if not txt.isdigit(): return await m.reply("رقم فقط.")
        st["api_id"]=int(txt); st["step"]=2
        return await m.reply("أرسل api_hash:")

    if st["step"]==2:
        st["api_hash"]=txt; st["step"]=3
        return await m.reply("أرسل رقم الهاتف مع +:")

    if st["step"]==3:
        st["phone"]=txt
        st["client"]=TelegramClient(StringSession(), st["api_id"], st["api_hash"])
        await st["client"].connect()
        try:
            await st["client"].send_code_request(txt)
            st["step"]=4
            return await m.reply("الكود:")
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
        clients[st["phone"]]  = st["client"]
        save_sessions(); add_state.pop(uid)
        return await m.reply("✅ تمت الإضافة.", buttons=menu())

    if st["step"]==5:
        try:
            await st["client"].sign_in(password=txt)
            sessions[st["phone"]] = st["client"].session.save()
            clients[st["phone"]]  = st["client"]
            save_sessions(); add_state.pop(uid)
            return await m.reply("✅ تمت الإضافة.", buttons=menu())
        except Exception as e:
            add_state.pop(uid); return await m.reply(f"خطأ: {e}")

# ─────── زر إرسال رسالة (جماعي) ───────────────────────────
@bot.on(events.CallbackQuery(data=b"snd"))
async def _(e):
    if not await is_owner(e): return await e.answer("للمالك فقط", alert=True)
    send_state[e.sender_id]={"step":1}
    await e.edit("✉️ اكتب الرسالة المراد إرسالها:")

@bot.on(events.NewMessage)
async def send_message_flow(m):
    uid, txt = m.sender_id, m.raw_text.strip()
    if uid not in send_state: return
    st = send_state[uid]

    if st["step"]==1:
        st["msg"]=txt; st["step"]=2
        return await m.reply("هدف الإرسال (@user أو رابط):")

    if st["step"]==2:
        target=txt; send_state.pop(uid)
        await m.reply("🚀 جارٍ الإرسال...")
        ok=bad=0

        entity=None
        try: entity=await bot.get_entity(target)
        except: pass
        is_user = getattr(entity, "__class__", None).__name__=="User" if entity else target.isdigit()

        for u,cl in clients.items():
            try:
                if not is_user:
                    joined=await join_chat(cl,target)
                    if not joined: bad+=1; continue
                    await asyncio.sleep(5)
                await cl.send_message(entity or target, st["msg"])
                ok+=1
            except FloodWaitError as fe:
                await asyncio.sleep(fe.seconds)
            except Exception as e:
                bad+=1; print(e)

        await m.reply(f"انتهى ✅\nنجاح:{ok} | فشل:{bad}", buttons=menu())

# ─────── أمر 💀 خبث ─────────────────────────────────────────
@bot.on(events.CallbackQuery(data=b"khabath"))
async def _(e):
    if not await is_owner(e): return await e.answer("للمالك فقط", alert=True)
    khabath_state[e.sender_id]={"step":1}
    await e.edit("💀 أرسل نص الرسالة الخبيثة:")

@bot.on(events.NewMessage)
async def khabath_flow(m):
    uid, txt = m.sender_id, m.raw_text.strip()
    if uid not in khabath_state: return
    st=khabath_state[uid]

    if st["step"]==1:
        st["msg"]=txt; st["step"]=2
        return await m.reply("👤 أرسل معرف أو ID الهدف:")

    if st["step"]==2:
        target=txt; khabath_state.pop(uid)
        msg_ids=[]
        for u, cl in clients.items():
            try:
                ent=await cl.get_entity(target)
                sent=await cl.send_message(ent, st["msg"])
                msg_ids.append((cl, ent, sent.id))
            except Exception as e:
                print(e); continue

        await asyncio.sleep(3)
        for cl, ent, mid in msg_ids:
            try:
                await cl(DeleteMessagesRequest(peer=ent, id=[mid], revoke=True))
            except Exception as e:
                print("delete error:", e)

        await m.reply("✅ خبث تم وتنظف خلال 3 ثواني.", buttons=menu())

# ─────── الشتائم (إضافة/عرض) ───────────────────────────────
@bot.on(events.CallbackQuery(data=b"add_ins"))
async def _(e):
    if not await is_owner(e): return await e.answer("للمالك فقط", alert=True)
    save_state[e.sender_id]={"step":1}
    await e.edit("أرسل الشتيمة أو 'الغاء':")

@bot.on(events.NewMessage)
async def save_insult_flow(m):
    uid, txt=m.sender_id, m.raw_text.strip()
    if uid not in save_state: return
    if txt.lower()=="الغاء":
        save_state.pop(uid); return await m.reply("أُلغي.", buttons=menu())
    st=save_state[uid]; st["txt"]=txt
    btn=[[Button.inline("👦",b"sv_b"), Button.inline("👧",b"sv_g")]]
    save_state[uid]={"text":txt}
    await m.reply("اختر الفئة:", buttons=btn)

@bot.on(events.CallbackQuery(data=b"sv_b"))
async def _(e):
    insult=save_state.get(e.sender_id,{}).get("text")
    if not insult: return await e.answer("لا نص", alert=True)
    res="⚠️ موجودة."
    if insult not in stored_insults["👦"]:
        stored_insults["👦"].add(insult); res="✅ حُفظت."
    save_state.pop(e.sender_id,None)
    await e.edit(f"{res}\nالفئة 👦", buttons=menu())

@bot.on(events.CallbackQuery(data=b"sv_g"))
async def _(e):
    insult=save_state.get(e.sender_id,{}).get("text")
    if not insult: return await e.answer("لا نص", alert=True)
    res="⚠️ موجودة."
    if insult not in stored_insults["👧"]:
        stored_insults["👧"].add(insult); res="✅ حُفظت."
    save_state.pop(e.sender_id,None)
    await e.edit(f"{res}\nالفئة 👧", buttons=menu())

@bot.on(events.CallbackQuery(data=b"show_b"))
async def _(e):
    lst=stored_insults["👦"]; txt="\n".join(lst) or "🚫 لا شيء."; await e.edit(f"👦:\n{txt}", buttons=menu())

@bot.on(events.CallbackQuery(data=b"show_g"))
async def _(e):
    lst=stored_insults["👧"]; txt="\n".join(lst) or "🚫 لا شيء."; await e.edit(f"👧:\n{txt}", buttons=menu())

@bot.on(events.CallbackQuery(data=b"export"))
async def _(e):
    if not await is_owner(e): return await e.answer("للمالك فقط", alert=True)
    if not sessions: return await e.answer("لا جلسات", alert=True)
    out="\n\n".join(f"{u}:\n`{s}`" for u,s in sessions.items())
    await bot.send_message(e.sender_id, f"📤 الجلسات:\n\n{out}", parse_mode="md")
    await e.answer("أُرسلت لك بالخاص.", alert=True)

# ─────── تشغيل البوت ───────────────────────────────────────
async def main():
    # تشغيل الجلسات المخزنة
    for phone,sess in sessions.items():
        c=TelegramClient(StringSession(sess), api_id, api_hash)
        await c.start()
        clients[phone]=c
    await bot.start(bot_token=bot_token)
    print("✅ Bot online")
    await bot.run_until_disconnected()

if __name__=="__main__":
    asyncio.run(main())
