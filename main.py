# -*- coding: utf-8 -*-
import asyncio, os, json
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError, PhoneCodeInvalidError,
    UserAlreadyParticipantError, FloodWaitError
)
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest

#──────── بيانات البوت ────────
api_id    = 20507759
api_hash  = "225d3a24d84c637b3b816d13cc7bd766"
bot_token = "7644214767:AAGOlYEiyF6yFWxiIX_jlwo9Ssj_Cb95oLU"

#──────── تخزين جلسات الحسابات ────────
SESS_FILE = "sessions.json"
sessions, clients = {}, {}
if os.path.exists(SESS_FILE):
    sessions.update(json.load(open(SESS_FILE)))

def save_sessions():
    json.dump(sessions, open(SESS_FILE, "w"), ensure_ascii=False, indent=2)

#──────── حاويات الحالات التفاعليّة ────────
add_state, send_state, save_state, evil_state = {}, {}, {}, {}
stored_insults = {"👦": set(), "👧": set()}

bot = TelegramClient("bot", api_id, api_hash)

#──────── أزرار القائمة ────────
def menu():
    return [
        [Button.inline("📋 الجلسات", b"list"),  Button.inline("📥 إضافة جلسة", b"add")],
        [Button.inline("🗑️ حذف جلسة", b"del"), Button.inline("✉️ إرسال رسالة", b"snd")],
        [Button.inline("🔥 خبث", b"evil")],
        [Button.inline("➕ إضافة شتيمة", b"add_ins"), Button.inline("📤 استخراج الجلسات", b"export")],
        [Button.inline("👦 شتائم الولد", b"show_b"),  Button.inline("👧 شتائم البنت", b"show_g")]
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

#──────── /start ────────
@bot.on(events.NewMessage(pattern=r"^/start$"))
async def start(e):
    await e.respond("🟢 أهلاً، اختر من الأزرار:", buttons=menu())

#──────── عرض الجلسات ────────
@bot.on(events.CallbackQuery(data=b"list"))
async def list_cb(e):
    txt = "📂 الجلسات:\n" + ("\n".join(f"- `{u}`" for u in sessions) if sessions else "🚫 لا جلسات.")
    await e.edit(txt, parse_mode="md", buttons=menu())

#──────── حذف جلسة ────────
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

#──────── إضافة جلسة ────────
@bot.on(events.CallbackQuery(data=b"add"))
async def add_start(e):
    add_state[e.sender_id] = {"step": 1}
    await e.edit("أرسل api_id:")

@bot.on(events.NewMessage)
async def add_flow(m):
    if m.sender_id not in add_state: return
    st = add_state[m.sender_id]; t = m.text.strip()
    if st["step"] == 1:
        if not t.isdigit(): return await m.reply("رقم فقط.")
        st["api_id"] = int(t); st["step"] = 2
        return await m.reply("api_hash:")
    if st["step"] == 2:
        st["api_hash"] = t; st["step"] = 3
        return await m.reply("رقم الهاتف (+):")
    if st["step"] == 3:
        st["phone"] = t
        st["client"] = TelegramClient(StringSession(), st["api_id"], st["api_hash"])
        await st["client"].connect()
        try:
            await st["client"].send_code_request(t)
            st["step"] = 4; return await m.reply("الكود:")
        except Exception as e:
            add_state.pop(m.sender_id); return await m.reply(f"خطأ: {e}")
    if st["step"] == 4:
        try:
            await st["client"].sign_in(st["phone"], t)
        except SessionPasswordNeededError:
            st["step"] = 5; return await m.reply("كلمة مرور 2FA:")
        except PhoneCodeInvalidError:
            return await m.reply("كود خطأ.")
        sessions[st["phone"]] = st["client"].session.save()
        clients[st["phone"]]  = st["client"]
        save_sessions(); add_state.pop(m.sender_id)
        return await m.reply("✅ أُضيفت.", buttons=menu())
    if st["step"] == 5:
        try:
            await st["client"].sign_in(password=t)
            sessions[st["phone"]] = st["client"].session.save()
            clients[st["phone"]]  = st["client"]
            save_sessions(); add_state.pop(m.sender_id)
            return await m.reply("✅ أُضيفت.", buttons=menu())
        except Exception as e:
            add_state.pop(m.sender_id); return await m.reply(f"خطأ: {e}")

#──────── إرسال جماعي ────────
@bot.on(events.CallbackQuery(data=b"snd"))
async def snd_start(e):
    send_state[e.sender_id] = {"step": 1}
    await e.edit("✉️ اكتب الرسالة:", buttons=[[Button.inline("🔙", b"back")]])

@bot.on(events.CallbackQuery(data=b"back"))
async def back_btn(e): await e.edit("↩️ تم الرجوع.", buttons=menu())

@bot.on(events.NewMessage)
async def send_flow(m):
    if m.sender_id not in send_state: return
    st = send_state[m.sender_id]; t = m.text.strip()
    if st["step"] == 1:
        st["msg"] = t; st["step"] = 2
        return await m.reply("🎯 الهدف (@user أو رابط):")
    if st["step"] == 2:
        target = t; send_state.pop(m.sender_id)
        await m.reply("🚀 جارٍ الإرسال…")
        ok = bad = 0
        entity = None
        try: entity = await bot.get_entity(target)
        except: pass
        is_user = getattr(entity, "__class__", None).__name__ == "User" if entity else target.isdigit()
        for ph, cl in clients.items():
            try:
                if not is_user and not await join_chat(cl, target): bad += 1; continue
                if not is_user: await asyncio.sleep(5)
                await cl.send_message(entity or target, st["msg"])
                ok += 1
            except FloodWaitError as fe:
                await asyncio.sleep(fe.seconds)
            except Exception as e:
                bad += 1; print(e)
        await m.reply(f"✅ تم.\nنجاح:{ok} | فشل:{bad}", buttons=menu())

#──────── زر خبث وحواره ────────
@bot.on(events.CallbackQuery(data=b"evil"))
async def evil_start(e):
    evil_state[e.sender_id] = {"step": 1}
    await e.edit("💬 أرسل نص الرسالة (خبث):")

@bot.on(events.NewMessage)
async def evil_flow(m):
    if m.sender_id not in evil_state: return
    st = evil_state[m.sender_id]
    if st["step"] == 1:
        st["msg"] = m.text.strip(); st["step"] = 2
        return await m.reply("👤 أرسل قائمة اليوزرات (كل سطر @user):")
    if st["step"] == 2:
        evil_state.pop(m.sender_id)
        targets = [ln.strip() for ln in m.text.splitlines() if ln.strip()]
        await m.reply("🚀 جارٍ إرسال رسائل خبث...")
        for t in targets:
            for ph, cl in clients.items():
                try:
                    ent = await cl.get_entity(t)
                    sent = await cl.send_message(ent, st["msg"])
                    await asyncio.sleep(3)
                    await cl.delete_messages(ent, sent.id, revoke=True)
                except Exception as e:
                    print(f"[{ph}] خطأ خبث مع {t}: {e}")
        await m.reply("✅ أُرسلت وحُذفت بعد 3 ثوانٍ.", buttons=menu())

#──────── نظام الشتائم ────────
@bot.on(events.CallbackQuery(data=b"add_ins"))
async def add_ins(e):
    save_state[e.sender_id] = {"step": 1}
    await e.edit("📝 أرسل الشتيمة أو (الغاء):")

@bot.on(events.NewMessage)
async def insult_flow(m):
    if m.sender_id not in save_state: return
    if m.text.lower() == "الغاء":
        save_state.pop(m.sender_id); return await m.reply("أُلغي.", buttons=menu())
    txt = m.text.strip(); save_state[m.sender_id] = {"text": txt}
    await m.reply("اختر الفئة:", buttons=[[Button.inline("👦", b"sv_b"), Button.inline("👧", b"sv_g")]])

@bot.on(events.CallbackQuery(data=b"sv_b"))
async def sv_b(e):
    insult = save_state.pop(e.sender_id, {}).get("text")
    if insult: stored_insults["👦"].add(insult)
    await e.edit("✅ حُفظت 👦", buttons=menu())

@bot.on(events.CallbackQuery(data=b"sv_g"))
async def sv_g(e):
    insult = save_state.pop(e.sender_id, {}).get("text")
    if insult: stored_insults["👧"].add(insult)
    await e.edit("✅ حُفظت 👧", buttons=menu())

@bot.on(events.CallbackQuery(data=b"show_b"))
async def show_b(e):
    txt = "\n".join(stored_insults["👦"]) or "🚫 فارغة."
    await e.edit(f"👦:\n{txt}", buttons=menu())

@bot.on(events.CallbackQuery(data=b"show_g"))
async def show_g(e):
    txt = "\n".join(stored_insults["👧"]) or "🚫 فارغة."
    await e.edit(f"👧:\n{txt}", buttons=menu())

#──────── تصدير الجلسات ────────
@bot.on(events.CallbackQuery(data=b"export"))
async def export(e):
    if not sessions: return await e.answer("🚫 لا جلسات.", alert=True)
    dump = "\n\n".join(f"{u}:\n`{s}`" for u, s in sessions.items())
    await bot.send_message(e.sender_id, f"📤 جلسات:\n\n{dump}", parse_mode="md")
    await e.answer("✓ بالخاص.", alert=True)

#──────── تشغيل الجلسات المخزّنة ثم البوت ────────
async def main():
    for ph, ses in sessions.items():
        c = TelegramClient(StringSession(ses), api_id, api_hash)
        await c.start(); clients[ph] = c
    await bot.start(bot_token=bot_token)
    print("✅ Bot online")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
