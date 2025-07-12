# -*- coding: utf-8 -*-
import asyncio, json, os
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import (
    PhoneCodeInvalidError, SessionPasswordNeededError,
    UserAlreadyParticipantError, FloodWaitError
)
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest, DeleteMessagesRequest

# ── بيانات البوت ────────────────────────────────────────────
api_id    = 20507759
api_hash  = "225d3a24d84c637b3b816d13cc7bd766"
bot_token = "7644214767:AAGOlYEiyF6yFWxiIX_jlwo9Ssj_Cb95oLU"

SESS_FILE = "sessions.json"
sessions, clients = {}, {}
add_state, send_state, khabath_state, save_state = {}, {}, {}, {}
stored_insults = {"👦": set(), "👧": set()}
OWNER_ID = None  # يضبط أوّل /start

bot = TelegramClient("bot", api_id, api_hash)

# ── تحميل الجلسات المحفوظة ─────────────────────────────────
if os.path.exists(SESS_FILE):
    sessions.update(json.load(open(SESS_FILE)))
    print(f"Loaded {len(sessions)} sessions")

def save_sessions():
    json.dump(sessions, open(SESS_FILE, "w"), ensure_ascii=False, indent=2)

# ── واجهة الأزرار ───────────────────────────────────────────
def menu():
    return [
        [Button.inline("📋 الجلسات", b"list"),  Button.inline("📥 إضافة جلسة", b"add")],
        [Button.inline("🗑️ حذف جلسة", b"del"), Button.inline("✉️ إرسال رسالة", b"snd")],
        [Button.inline("➕ إضافة شتيمة", b"add_ins"), Button.inline("📤 استخراج الجلسات", b"export")],
        [Button.inline("👦 شتائم الولد", b"show_b"),  Button.inline("👧 شتائم البنت", b"show_g")],
        [Button.inline("😈 خبث", b"khabath")]
    ]

def sess_btns(tag): return [[Button.inline(u, f"{tag}:{u}".encode())] for u in sessions]

async def is_owner(e): return e.sender_id == OWNER_ID

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

# ── /start ─────────────────────────────────────────────────
@bot.on(events.NewMessage(pattern=r"^/start$"))
async def _(e):
    global OWNER_ID
    if OWNER_ID is None:
        OWNER_ID = e.sender_id
        await e.respond("✅ تم تعيينك مالكًا للبوت.")
    await e.respond("🟢 أهلاً، اختر:", buttons=menu())

# ── قائمة الجلسات ──────────────────────────────────────────
@bot.on(events.CallbackQuery(data=b"list"))
async def _(e):
    if not await is_owner(e): return await e.answer("للمالك فقط!", alert=True)
    txt = "📂 الجلسات:\n" + ("\n".join(f"- `{u}`" for u in sessions) if sessions else "🚫 لا جلسات.")
    await e.edit(txt, parse_mode="md", buttons=menu())

# ── حذف جلسة ───────────────────────────────────────────────
@bot.on(events.CallbackQuery(data=b"del"))
async def _(e):
    if not await is_owner(e): return await e.answer("للمالك فقط!", alert=True)
    if not sessions: return await e.answer("لا جلسات.", alert=True)
    await e.edit("🗑️ اختر جلسة:", buttons=sess_btns("rm"))

@bot.on(events.CallbackQuery(pattern=b"rm:(.+)"))
async def _(e):
    if not await is_owner(e): return
    phone = e.data.decode().split(":",1)[1]
    if phone in sessions:
        sessions.pop(phone); save_sessions()
        if (c:=clients.pop(phone,None)): await c.disconnect()
        await e.edit(f"❌ حُذفت `{phone}`", parse_mode="md", buttons=menu())
    else:
        await e.answer("غير موجودة.", alert=True)

# ── إضافة جلسة ─────────────────────────────────────────────
@bot.on(events.CallbackQuery(data=b"add"))
async def _(e):
    if not await is_owner(e): return await e.answer("للمالك فقط!", alert=True)
    add_state[e.sender_id]={"step":1}
    await e.edit("أرسل api_id:")

@bot.on(events.NewMessage)
async def add_flow(m):
    uid, txt = m.sender_id, m.raw_text.strip()
    if uid not in add_state: return
    st=add_state[uid]
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
            st["step"]=4; return await m.reply("أرسل الكود:")
        except Exception as e:
            add_state.pop(uid); return await m.reply(f"خطأ: {e}")
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
        return await m.reply("✅ أضيفت.", buttons=menu())
    if st["step"]==5:
        try:
            await st["client"].sign_in(password=txt)
            sessions[st["phone"]] = st["client"].session.save()
            clients[st["phone"]]  = st["client"]
            save_sessions(); add_state.pop(uid)
            return await m.reply("✅ أضيفت.", buttons=menu())
        except Exception as e:
            add_state.pop(uid); return await m.reply(f"خطأ: {e}")

# ── إرسال جماعي ────────────────────────────────────────────
@bot.on(events.CallbackQuery(data=b"snd"))
async def _(e):
    if not await is_owner(e): return await e.answer("للمالك فقط!", alert=True)
    send_state[e.sender_id]={"step":1}
    await e.edit("✉️ اكتب الرسالة:")

@bot.on(events.NewMessage)
async def send_flow(m):
    uid, txt=m.sender_id, m.raw_text.strip()
    if uid not in send_state: return
    st=send_state[uid]
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
        is_user= getattr(entity,"__class__",None).__name__=="User" if entity else target.isdigit()
        for ph,cl in clients.items():
            try:
                if not is_user and not await join_chat(cl,target):
                    bad+=1; continue
                if not is_user: await asyncio.sleep(5)
                await cl.send_message(entity or target, st["msg"])
                ok+=1
            except FloodWaitError as fe:
                await asyncio.sleep(fe.seconds)
            except Exception as e:
                bad+=1; print(e)
        await m.reply(f"✅ انتهى.\nنجاح:{ok} | فشل:{bad}", buttons=menu())

# ── زِر 😈 خبث ──────────────────────────────────────────────
@bot.on(events.CallbackQuery(data=b"khabath"))
async def _(e):
    if not await is_owner(e): return await e.answer("للمالك فقط!", alert=True)
    khabath_state[e.sender_id]={"step":1}
    await e.edit("😈 أرسل نص الرسالة:")

@bot.on(events.NewMessage)
async def khabath_flow(m):
    uid, txt=m.sender_id, m.raw_text.strip()
    if uid not in khabath_state: return
    st=khabath_state[uid]
    if st["step"]==1:
        st["msg"]=txt; st["step"]=2
        return await m.reply("👤 أرسل معرف الهدف (@username أو ID):")
    if st["step"]==2:
        target=txt; khabath_state.pop(uid)
        info=[]
        for ph,cl in clients.items():
            try:
                ent=await cl.get_entity(target)
                sent=await cl.send_message(ent, st["msg"])
                info.append((cl, ent, sent.id))
            except Exception as e:
                print(f"[{ph}] send err:", e)
        await asyncio.sleep(3)
        for cl, ent, mid in info:
            try:
                await cl(DeleteMessagesRequest(ent, [mid], revoke=True))
                await cl.delete_dialog(ent)
            except Exception as e:
                print("del err:", e)
        await m.reply("✅ أُرسل وحُذفت المحادثة بعد 3 ثوانٍ.", buttons=menu())

# ── الشتائم (إضافة/عرض) ───────────────────────────────────
@bot.on(events.CallbackQuery(data=b"add_ins"))
async def _(e):
    if not await is_owner(e): return await e.answer("للمالك فقط!", alert=True)
    save_state[e.sender_id]={"step":1}
    await e.edit("🔸 أرسل الشتيمة (أو 'الغاء'):")

@bot.on(events.NewMessage)
async def insult_flow(m):
    uid, txt=m.sender_id, m.raw_text.strip()
    if uid not in save_state: return
    if txt.lower()=="الغاء":
        save_state.pop(uid); return await m.reply("تم الإلغاء.", buttons=menu())
    save_state[uid]={"text":txt}
    btn=[[Button.inline("👦", b"sv_b"), Button.inline("👧", b"sv_g")]]
    await m.reply("اختر الفئة:", buttons=btn)

@bot.on(events.CallbackQuery(data=b"sv_b"))
async def _(e):
    insult=save_state.pop(e.sender_id,{}).get("text")
    if not insult: return
    stored_insults["👦"].add(insult)
    await e.edit("✅ حُفظت للولد.", buttons=menu())

@bot.on(events.CallbackQuery(data=b"sv_g"))
async def _(e):
    insult=save_state.pop(e.sender_id,{}).get("text")
    if not insult: return
    stored_insults["👧"].add(insult)
    await e.edit("✅ حُفظت للبنت.", buttons=menu())

@bot.on(events.CallbackQuery(data=b"show_b"))
async def _(e):
    txt="\n".join(stored_insults["👦"]) or "🚫 لا شيء."
    await e.edit(f"👦:\n{txt}", buttons=menu())

@bot.on(events.CallbackQuery(data=b"show_g"))
async def _(e):
    txt="\n".join(stored_insults["👧"]) or "🚫 لا شيء."
    await e.edit(f"👧:\n{txt}", buttons=menu())

@bot.on(events.CallbackQuery(data=b"export"))
async def _(e):
    if not await is_owner(e): return await e.answer("للمالك فقط!", alert=True)
    if not sessions: return await e.answer("لا جلسات.", alert=True)
    out="\n\n".join(f"{u}:\n`{s}`" for u,s in sessions.items())
    await bot.send_message(e.sender_id, f"📤 جلسات:\n\n{out}", parse_mode="md")
    await e.answer("أُرسلت بالخاص.", alert=True)

# ── تشغيل كل الجلسات المسجلة ثم البوت ─────────────────────
async def main():
    for ph,ses in sessions.items():
        c=TelegramClient(StringSession(ses), api_id, api_hash)
        await c.start(); clients[ph]=c
    await bot.start(bot_token=bot_token)
    print("✅ Bot online")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
