# -*- coding: utf-8 -*-
import asyncio, random, json, os
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, UserAlreadyParticipantError
from telethon.tl.functions.channels import JoinChannelRequest, GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest
from telethon.tl.types import Channel, Chat

api_id    = 20507759
api_hash  = "225d3a24d84c637b3b816d13cc7bd766"
bot_token = "7644214767:AAGOlYEiyF6yFWxiIX_jlwo9Ssj_Cb95oLU"

add_state, send_state, save_state = {}, {}, {}
stored_insults = {"👦": set(), "👧": set()}

bot = TelegramClient("bot", api_id, api_hash)

# --- دوال لحفظ واسترجاع الجلسات من ملف JSON ---
def save_sessions():
    with open(sessions_file, "w", encoding="utf-8") as f:
        json.dump(sessions, f, ensure_ascii=False, indent=2)

def load_sessions():
    global sessions
    if os.path.exists(sessions_file):
        with open(sessions_file, "r", encoding="utf-8") as f:
            sessions = json.load(f)

def menu():
    return [
        [Button.inline("📋 الجلسات", b"list"), Button.inline("📥 إضافة جلسة", b"add")],
        [Button.inline("🗑️ حذف جلسة", b"del"), Button.inline("✉️ إرسال رسالة", b"snd")],
        [Button.inline("➕ إضافة شتيمة", b"add_insult"), Button.inline("📤 استخراج الجلسات", b"export_sessions")],
        [Button.inline("👦 عرض شتائم الولد", b"show_boy"), Button.inline("👧 عرض شتائم البنت", b"show_girl")]
    ]

def sess_btns(pref): return [[Button.inline(n, f"{pref}:{n}".encode())] for n in sessions]

@bot.on(events.NewMessage(pattern=r"^/start$"))
async def start(e): 
    await e.respond("🟢 مرحباً، اختر من الأزرار:", buttons=menu())

@bot.on(events.CallbackQuery(data=b"list"))
async def _(e):
    if sessions:
        txt = "📂 الجلسات:\n" + "\n".join(f"- `{u}`" for u in sessions)
    else:
        txt = "🚫 لا توجد جلسات حالياً."
    await e.edit(txt, parse_mode="md", buttons=menu())

@bot.on(events.CallbackQuery(data=b"del"))
async def _(e):
    if not sessions: 
        return await e.answer("🚫 لا يوجد جلسات لحذفها.", alert=True)
    await e.edit("🗑️ اختر جلسة لحذفها:", buttons=sess_btns("rm"))

@bot.on(events.CallbackQuery(pattern=b"rm:(.+)"))
async def _(e):
    n = e.data.decode().split(":",1)[1]
    if n in sessions:
        sessions.pop(n)
        if (c := clients.pop(n, None)):
            await c.disconnect()
        save_sessions()  # حفظ التعديل
        await e.edit(f"❌ حُذفت الجلسة `{n}`", parse_mode="md", buttons=menu())
    else:
        await e.answer("❌ الجلسة غير موجودة.", alert=True)

@bot.on(events.CallbackQuery(data=b"add"))
async def _(e):
    add_state[e.sender_id] = {"step": 1}
    await e.edit("أرسل `api_id` الخاص بالحساب:", parse_mode="md")

@bot.on(events.CallbackQuery(data=b"snd"))
async def _(e):
    send_state[e.sender_id] = {"step": 1}
    await e.edit("✉️ أرسل الرسالة التي تريد إرسالها لكل الجلسات:")

@bot.on(events.CallbackQuery(data=b"add_insult"))
async def _(e):
    save_state[e.sender_id] = {"step": 1}
    await e.edit("أرسل الشتيمة (أي نص)، أو أرسل 'الغاء' لإلغاء العملية.")

@bot.on(events.CallbackQuery(data=b"show_boy"))
async def _(e):
    insults = stored_insults["👦"]
    if insults:
        txt = "👦 شتائم الولد:\n" + "\n".join(f"- {i}" for i in insults)
    else:
        txt = "🚫 لا توجد شتائم للفئة 👦"
    await e.edit(txt, buttons=menu())

@bot.on(events.CallbackQuery(data=b"show_girl"))
async def _(e):
    insults = stored_insults["👧"]
    if insults:
        txt = "👧 شتائم البنت:\n" + "\n".join(f"- {i}" for i in insults)
    else:
        txt = "🚫 لا توجد شتائم للفئة 👧"
    await e.edit(txt, buttons=menu())

@bot.on(events.CallbackQuery(data=b"export_sessions"))
async def _(e):
    if not sessions:
        return await e.answer("🚫 لا توجد جلسات.", alert=True)
    msg = "📤 **الجلسات المحفوظة:**\n\n"
    for user, sess in sessions.items():
        msg += f"`{user}`:\n`{sess}`\n\n"
    try:
        await bot.send_message(e.sender_id, msg, parse_mode="md")
        await e.answer("✅ تم الإرسال بالخاص.", alert=True)
    except Exception:
        await e.answer("❌ فشل الإرسال. تأكد من فتح الخاص مع البوت.", alert=True)

@bot.on(events.NewMessage)
async def _(m):
    uid, txt = m.sender_id, m.raw_text.strip()

    # إضافة جلسة
    if uid in add_state:
        st = add_state[uid]
        if st["step"] == 1:
            if not txt.isdigit(): return await m.reply("❌ يجب أن يكون رقمًا.")
            st["api_id"] = int(txt)
            st["step"] = 2
            return await m.reply("أرسل `api_hash` الخاص بالحساب:")
        if st["step"] == 2:
            st["api_hash"] = txt
            st["step"] = 3
            return await m.reply("أرسل رقم الهاتف بالحساب (مع +):")
        if st["step"] == 3:
            st["phone"] = txt
            st["client"] = TelegramClient(StringSession(), st["api_id"], st["api_hash"])
            await st["client"].connect()
            try:
                await st["client"].send_code_request(txt)
                st["step"] = 4
                return await m.reply("أرسل كود التحقق:")
            except Exception as e:
                add_state.pop(uid)
                return await m.reply(f"❌ خطأ: {e}")
        if st["step"] == 4:
            try:
                await st["client"].sign_in(st["phone"], txt)
            except SessionPasswordNeededError:
                st["step"] = 5
                return await m.reply("أرسل كلمة مرور 2FA:")
            except PhoneCodeInvalidError:
                return await m.reply("❌ الكود غير صحيح.")
            sessions[st["phone"]] = st["client"].session.save()
            clients[st["phone"]] = st["client"]
            save_sessions()  # حفظ التعديل
            add_state.pop(uid)
            return await m.reply("✅ تمت الإضافة بنجاح.", buttons=menu())
        if st["step"] == 5:
            try:
                await st["client"].sign_in(password=txt)
                sessions[st["phone"]] = st["client"].session.save()
                clients[st["phone"]] = st["client"]
                save_sessions()  # حفظ التعديل
                add_state.pop(uid)
                return await m.reply("✅ تمت الإضافة بنجاح.", buttons=menu())
            except Exception as e:
                add_state.pop(uid)
                return await m.reply(f"❌ خطأ: {e}")

    # إرسال رسالة
    if uid in send_state:
        st = send_state[uid]
        if st["step"] == 1:
            st["msg"] = txt
            st["step"] = 2
            return await m.reply("أرسل المعرف (@user أو id أو رابط):")
        if st["step"] == 2:
            target = txt
            send_state.pop(uid)
            await m.reply("🚀 يتم الآن الإرسال...")

            # تحقق من نوع الهدف (شخصي أو مجموعة)
            try:
                entity = await bot.get_entity(target)
            except Exception as e:
                return await m.reply(f"❌ خطأ في العثور على الهدف: {e}")

            is_group = isinstance(entity, (Channel, Chat))
            ok, bad = 0, 0

            if is_group:
                # اذا مجموعة، حاول انضمام الحسابات غير المنضمة
                for n, cl in clients.items():
                    try:
                        # تحقق إذا العضو بالفعل موجود
                        full = await cl(GetFullChannelRequest(entity)) if isinstance(entity, Channel) else await cl(GetFullChatRequest(entity))
                        participants = []
                        if isinstance(entity, Channel):
                            participants = [p.user_id for p in full.full_chat.participants or []]
                        else:
                            participants = [p.user_id for p in full.full_chat.participants or []]
                        if cl.get_me().id not in participants:
                            try:
                                await cl(JoinChannelRequest(entity))
                                await asyncio.sleep(3)  # انتظار قليل بعد الانضمام
                            except UserAlreadyParticipantError:
                                pass
                            except Exception as ex:
                                print(f"[{n}] خطأ أثناء الانضمام: {ex}")
                    except Exception as e:
                        print(f"[{n}] خطأ أثناء جلب المشاركين: {e}")

                # إرسال الرسائل مع تأخير 5 ثواني بين كل حساب
                for n, cl in clients.items():
                    try:
                        await cl.send_message(entity, st["msg"])
                        ok += 1
                    except Exception as e:
                        bad += 1
                        print(f"[{n}] خطأ أثناء الإرسال: {e}")
                    await asyncio.sleep(5)
            else:
                # اذا شخصي، ارسل للجميع دفعة واحدة بدون تأخير
                for n, cl in clients.items():
                    try:
                        await cl.send_message(entity, st["msg"])
                        ok += 1
                    except Exception as e:
                        bad += 1
                        print(f"[{n}] خطأ أثناء الإرسال: {e}")

            return await m.reply(f"✅ أُرسلت الرسائل.\nنجاح: {ok} | فشل: {bad}", buttons=menu())

    # حفظ الشتيمة
    if uid in save_state:
        st = save_state[uid]
        if st["step"] == 1 and txt.lower() != "الغاء":
            st["text"] = txt
            st["step"] = 2
            btns = [[
                Button.inline("👦", b"save_boy"),
                Button.inline("👧", b"save_girl")
            ]]
            return await m.reply("اختر الفئة:", buttons=btns)
        elif txt.lower() == "الغاء":
            save_state.pop(uid, None)
            return await m.reply("❌ تم الإلغاء.", buttons=menu())

@bot.on(events.CallbackQuery(data=b"save_boy"))
async def _(e):
    uid = e.sender_id
    if uid not in save_state: return await e.answer("❌ لا يوجد نص محفوظ.", alert=True)
    insult = save_state[uid]["text"]
    if insult in stored_insults["👦"]:
        txt = "⚠️ مضافة سابقًا."
    else:
        stored_insults["👦"].add(insult)
        txt = "✅ تم الحفظ."
    save_state.pop(uid, None)
    await e.edit(f"{txt}\nالفئة: 👦", buttons=menu())

@bot.on(events.CallbackQuery(data=b"save_girl"))
async def _(e):
    uid = e.sender_id
    if uid not in save_state: return await e.answer("❌ لا يوجد نص محفوظ.", alert=True)
    insult = save_state[uid]["text"]
    if insult in stored_insults["👧"]:
        txt = "⚠️ مضافة سابقًا."
    else:
        stored_insults["👧"].add(insult)
        txt = "✅ تم الحفظ."
    save_state.pop(uid, None)
    await e.edit(f"{txt}\nالفئة: 👧", buttons=menu())

async def main():
    load_sessions()  # تحميل الجلسات المحفوظة
    # إنشاء عملاء لكل جلسة وتحميلها
    for phone, sess in sessions.items():
        client = TelegramClient(StringSession(sess), api_id, api_hash)
        await client.start()
        clients[phone] = client

    await bot.start(bot_token=bot_token)
    print("✅ Bot is online")
    await bot.run_until_disconnected()

if __name__
