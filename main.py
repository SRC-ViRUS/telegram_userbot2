# -*- coding: utf-8 -*-
import asyncio, json, os, traceback
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import (
    FloodWaitError, PhoneCodeInvalidError, SessionPasswordNeededError,
    UserAlreadyParticipantError
)
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import (
    ImportChatInviteRequest, DeleteMessagesRequest
)

#──────── إعدادات البوت ────────
api_id    = 20507759
api_hash  = "225d3a24d84c637b3b816d13cc7bd766"
bot_token = "7644214767:AAGOlYEiyF6yFWxiIX_jlwo9Ssj_Cb95oLU"

SESS_FILE = "sessions.json"   # يُخزّن StringSessions

sessions, clients = {}, {}
add_state, send_state, khabath_state, save_state = {}, {}, {}, {}
stored_insults = {"👦": set(), "👧": set()}

OWNER_ID = None        # يُحدَّد أول /start
bot = TelegramClient("bot", api_id, api_hash)

#──────── واجهة الأزرار ────────
def menu():
    return [
        [Button.inline("📋 الجلسات", b"list"), Button.inline("📥 إضافة جلسة", b"add")],
        [Button.inline("🗑️ حذف جلسة", b"del"),  Button.inline("✉️ إرسال رسالة", b"snd")],
        [Button.inline("➕ إضافة شتيمة", b"add_ins"), Button.inline("📤 استخراج الجلسات", b"export")],
        [Button.inline("👦 شتائم الولد", b"show_b"),  Button.inline("👧 شتائم البنت", b"show_g")],
        [Button.inline("💀 خبث", b"khabath")]
    ]

def sess_btns(tag):       # أزرار الجلسات للحذف
    return [[Button.inline(u, f"{tag}:{u}".encode())] for u in sessions]

#──────── أدوات مساعدة ────────
def save_sessions():
    json.dump(sessions, open(SESS_FILE, "w"), ensure_ascii=False, indent=2)

if os.path.exists(SESS_FILE):
    sessions.update(json.load(open(SESS_FILE)))
    print(f"Loaded {len(sessions)} sessions from file")

async def is_owner(e):
    return e.sender_id == OWNER_ID

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
    except Exception as exc:
        print("join_chat error:", exc)
        return False

#──────── /start ────────
@bot.on(events.NewMessage(pattern=r"^/start$"))
async def _(e):
    global OWNER_ID
    if OWNER_ID is None:
        OWNER_ID = e.sender_id
        await e.respond("✅ تم تعيينك مالكًا للبوت.")
    await e.respond("🟢 أهلاً، اختر:", buttons=menu())

#──────── قائمة الجلسات ────────
@bot.on(events.CallbackQuery(data=b"list"))
async def _(e):
    if not await is_owner(e): return await e.answer("للمالك فقط!", alert=True)
    txt = "📂 الجلسات:\n" + ("\n".join(f"- `{u}`" for u in sessions) if sessions else "🚫 لا توجد جلسات.")
    await e.edit(txt, parse_mode="md", buttons=menu())

#──────── حذف جلسة ────────
@bot.on(events.CallbackQuery(data=b"del"))
async def _(e):
    if not await is_owner(e): return await e.answer("للمالك فقط!", alert=True)
    if not sessions: return await e.answer("لا جلسات.", alert=True)
    await e.edit("🗑️ اختر جلسة للحذف:", buttons=sess_btns("rm"))

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

#──────── إضافة جلسة (حوار تفاعلي) ────────
@bot.on(events.CallbackQuery(data=b"add"))
async def _(e):
    if not await is_owner(e): return await e.answer("للمالك فقط!", alert=True)
    add_state[e.sender_id] = {"step":1}
    await e.edit("أرسل api_id:")

@bot.on(events.NewMessage)
async def add_flow(m):
    uid, txt = m.sender_id, m.raw_text.strip()
    if uid not in add_state: return
    st = add_state[uid]

    if st["step"]==1:
        if not txt.isdigit(): return await m.reply("رقم فقط.")
        st["api_id"]=int(txt); st["step"]=2
        return await m.reply("أرسل api_hash:")

    if st["step"]==2:
        st["api_hash"]=txt; st["step"]=3
        return await m.reply("أرسل رقم الهاتف (+):")

    if st["step"]==3:
        st["phone"]=txt
        st["client"]=TelegramClient(StringSession(), st["api_id"], st["api_hash"])
        await st["client"].connect()
        try:
            await st["client"].send_code_request(txt)
            st["step"]=4; return await m.reply("الكود:")
        except Exception as e:
            add_state.pop(uid)
            return await m.reply(f"خطأ: {e}")

    if st["step"]==4:
        try:
            await st["client"].sign_in(st["phone"], txt)
        except SessionPasswordNeededError:
            st["step"]=5; return await m.reply("كلمة مرور 2FA:")
        except PhoneCodeInvalidError:
            return await m.reply("❌ كود خطأ.")
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
            add_state.pop(uid)
            return await m.reply(f"خطأ: {e}")

#──────── إرسال رسالة جماعيّة ────────
@bot.on(events.CallbackQuery(data=b"snd"))
async def _(e):
    if not await is_owner(e): return await e.answer("للمالك فقط!", alert=True)
    send_state[e.sender_id]={"step":1}
    await e.edit("✉️ اكتب الرسالة للإرسال:")

@bot.on(events.NewMessage)
async def send_flow(m):
    uid, txt = m.sender_id, m.raw_text.strip()
    if uid not in send_state: return
    st = send_state[uid]

    if st["step"]==1:
        st["msg"]=txt; st["step"]=2
        return await m.reply("🎯 الهدف (@user أو رابط):")

    if st["step"]==2:
        target=txt; send_state.pop(uid)
        await m.reply("🚀 جاري الإرسال…")
        ok=bad=0
        entity=None
        try: entity=await bot.get_entity(target)
        except: pass
        is_user = getattr(entity,"__class__",None).__name__=="User" if entity else target.isdigit()

        for user,cl in clients.items():
            try:
                if not is_user:
                    if not await join_chat(cl,target): bad+=1; continue
                    await asyncio.sleep(5)
                await cl.send_message(entity or target, st["msg"])
                ok+=1
            except FloodWaitError as fe:
                await asyncio.sleep(fe.seconds)
            except Exception as e:
                bad+=1; print(e)

        await m.reply(f"✅ تم.\nنجاح: {ok} | فشل: {bad}", buttons=menu())

#──────── أمر 💀 خبث ────────
@bot.on(events.CallbackQuery(data=b"khabath"))
async def _(e):
    if not await is_owner(e): return await e.answer("للمالك فقط!", alert=True)
    khabath_state[e.sender_id]={"step":1}
    await e.edit("💀 أرسل نص الرسالة الخبيثة:")

@bot.on(events.NewMessage)
async def khabath_flow(m):
    uid, txt=m.sender_id, m.raw_text.strip()
    if uid not in khabath_state: return
    st=khabath_state[uid]

    # 1- الرسالة
    if st["step"]==1:
        st["msg"]=txt; st["step"]=2
        return await m.reply("👤 أرسل معرف الهدف (@username أو ID):")

    # 2- الهدف وإتمام
    if st["step"]==2:
        target=txt; khabath_state.pop(uid)
        sent_info=[]
        for ph,cl in clients.items():
            try:
                ent=await cl.get_entity(target)
                msg=await cl.send_message(ent, st["msg"])
                sent_info.append((cl, ent, msg.id))
            except Exception as e:
                print(f"[{ph}] send error:", e)

        await asyncio.sleep(3)
        for cl, ent, mid in sent_info:
            try:
                # حذف الرسالة المرسَلة من الطرفين
                await cl(DeleteMessagesRequest(peer=ent, id=[mid], revoke=True))
                # حذف الحوار من واجهة الحساب
                await cl.delete_dialog(ent)
            except Exception as e:
                print("delete error:", e)

        await m.reply("✅ تم خبث الرسالة وحُذفت المحادثة بعد 3 ثواني.", buttons=menu())

#──────── نظام الشتائم ────────
@bot.on(events.CallbackQuery(data=b"add_ins"))
async def _(e):
    if not await is_owner(e): return await e.answer("للمالك فقط!", alert=True)
    save_state[e.sender_id]={"step":1}
    await e.edit("🔸 أرسل الشتيمة، أو 'الغاء' للإلغاء:")

@bot.on(events.NewMessage)
async def insult_flow(m):
    uid, txt=m.sender_id, m.raw_text.strip()
    if uid not in save_state: return

    if txt.lower()=="الغاء":
        save_state.pop(uid); return await m.reply("تم الإلغاء.", buttons=menu())

    st=save_state[uid]; st["text"]=txt
    btn=[[Button.inline("👦",b"sv_b"), Button.inline("👧",b"sv_g")]]
    await m.reply("اختر الفئة:", buttons=btn)

@bot.on(events.CallbackQuery(data=b"sv_b"))
async def _(e):
    insult=save_state.get(e.sender_id,{}).get("text")
    if not insult: return await e.answer("لا نص.", alert=True)
    res="⚠️ موجودة."
    if insult not in stored_insults["👦"]: stored_insults["👦"].add(insult); res="✅ تم الحفظ."
    save_state.pop(e.sender_id,None)
    await e.edit(f"{res}\nالفئة: 👦", buttons=menu())

@bot.on(events.CallbackQuery(data=b"sv_g"))
async def _(e):
    insult=save_state.get(e.sender_id,{}).get("text")
    if not insult: return await e.answer("لا نص.", alert=True)
    res="⚠️ موجودة."
    if insult not in stored_insults["👧"]: stored_insults["👧"].add(insult); res="✅ تم الحفظ."
    save_state.pop(e.sender_id,None)
    await e.edit(f"{res}\nالفئة: 👧", buttons=menu())

@bot.on(events.CallbackQuery(data=b"show_b"))
async def _(e):
    txt="\n".join(stored_insults["👦"]) or "🚫 فارغة."
    await e.edit(f"👦 شتائم:\n{txt}", buttons=menu())

@bot.on(events.CallbackQuery(data=b"show_g"))
async def _(e):
    txt="\n".join(stored_insults["👧"]) or "🚫 فارغة."
    await e.edit(f"👧 شتائم:\n{txt}", buttons=menu())

@bot.on(events.CallbackQuery(data=b"export"))
async def _(e):
    if not await is_owner(e): return await e.answer("للمالك فقط!", alert=True)
    if not sessions: return await e.answer("لا جلسات.", alert=True)
    out="\n\n".join(f"{u}:\n`{s}`" for u,s in sessions.items())
    await bot.send_message(e.sender_id, f"📤 الجلسات:\n\n{out}", parse_mode="md")
    await e.answer("أُرسلت بالخاص.", alert=True)

#──────── تشغيل جميع الجلسات المُخزّنة والبوت ────────
async def main():
    for ph, sess in sessions.items():
        c=TelegramClient(StringSession(sess), api_id, api_hash)
        await c.start()
        clients[ph]=c
    await bot.start(bot_token=bot_token)
    print("✅ Bot online")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
