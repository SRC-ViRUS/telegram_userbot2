import asyncio
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    UserAlreadyParticipantError,
    FloodWaitError
)
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest

api_id    = 20507759
api_hash  = "225d3a24d84c637b3b816d13cc7bd766"
bot_token = "7644214767:AAGOlYEiyF6yFWxiIX_jlwo9Ssj_Cb95oLU"

sessions, clients = {}, {}
add_state, send_state, save_state = {}, {}, {}
stored_insults = {"👦": set(), "👧": set()}

bot = TelegramClient("bot", api_id, api_hash)

def menu():
    return [
        [Button.inline("📋 الجلسات", b"list"), Button.inline("📥 إضافة جلسة", b"add")],
        [Button.inline("🗑️ حذف جلسة", b"del"), Button.inline("✉️ إرسال رسالة", b"snd")],
        [Button.inline("➕ إضافة شتيمة", b"add_insult"), Button.inline("📤 استخراج الجلسات", b"export_sessions")],
        [Button.inline("👦 عرض شتائم الولد", b"show_boy"), Button.inline("👧 عرض شتائم البنت", b"show_girl")],
        [Button.inline("🔥 أمر خبث", b"khbth_menu")]
    ]

def sess_btns(pref): return [[Button.inline(n, f"{pref}:{n}".encode())] for n in sessions]

async def join_channel(client, target):
    try:
        if target.startswith("https://t.me/joinchat/") or target.startswith("t.me/joinchat/"):
            hash_invite = target.split("/")[-1]
            await client(ImportChatInviteRequest(hash_invite))
        else:
            await client(JoinChannelRequest(target))
        return True
    except UserAlreadyParticipantError:
        return True
    except Exception as e:
        print(f"خطأ بالانضمام: {e}")
        return False

async def is_owner(event):
    me = await bot.get_me()
    return event.sender_id == me.id

# -- أوامر الأزرار -- #

@bot.on(events.CallbackQuery(data=b"list"))
async def list_sessions(e):
    if sessions:
        txt = "📂 الجلسات:\n" + "\n".join(f"- `{u}`" for u in sessions)
    else:
        txt = "🚫 لا توجد جلسات حالياً."
    await e.edit(txt, parse_mode="md", buttons=menu())

@bot.on(events.CallbackQuery(data=b"del"))
async def del_sessions(e):
    if not sessions: 
        return await e.answer("🚫 لا يوجد جلسات لحذفها.", alert=True)
    await e.edit("🗑️ اختر جلسة لحذفها:", buttons=sess_btns("rm"))

@bot.on(events.CallbackQuery(pattern=b"rm:(.+)"))
async def rm_session(e):
    n = e.data.decode().split(":",1)[1]
    if n in sessions:
        sessions.pop(n)
        if (c := clients.pop(n, None)):
            await c.disconnect()
        await e.edit(f"❌ حُذفت الجلسة `{n}`", parse_mode="md", buttons=menu())
    else:
        await e.answer("❌ الجلسة غير موجودة.", alert=True)

@bot.on(events.CallbackQuery(data=b"add"))
async def add_session_start(e):
    add_state[e.sender_id] = {"step": 1}
    await e.edit("أرسل `api_id` الخاص بالحساب:", parse_mode="md")

@bot.on(events.CallbackQuery(data=b"snd"))
async def send_message_start(e):
    send_state[e.sender_id] = {"step": 1}
    await e.edit("✉️ أرسل الرسالة التي تريد إرسالها لكل الجلسات:")

@bot.on(events.CallbackQuery(data=b"add_insult"))
async def add_insult_start(e):
    save_state[e.sender_id] = {"step": 1}
    await e.edit("أرسل الشتيمة (أي نص)، أو أرسل 'الغاء' لإلغاء العملية.")

@bot.on(events.CallbackQuery(data=b"show_boy"))
async def show_boy_insults(e):
    insults = stored_insults["👦"]
    if insults:
        txt = "👦 شتائم الولد:\n" + "\n".join(f"- {i}" for i in insults)
    else:
        txt = "🚫 لا توجد شتائم للفئة 👦"
    await e.edit(txt, buttons=menu())

@bot.on(events.CallbackQuery(data=b"show_girl"))
async def show_girl_insults(e):
    insults = stored_insults["👧"]
    if insults:
        txt = "👧 شتائم البنت:\n" + "\n".join(f"- {i}" for i in insults)
    else:
        txt = "🚫 لا توجد شتائم للفئة 👧"
    await e.edit(txt, buttons=menu())

@bot.on(events.CallbackQuery(data=b"export_sessions"))
async def export_sessions(e):
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

@bot.on(events.CallbackQuery(data=b"khbth_menu"))
async def khbth_menu_handler(e):
    if not await is_owner(e):
        return await e.answer("🚫 هذا الأمر خاص بالمالك فقط.", alert=True)
    await e.edit(
        "🔥 أمر خبث:\nأرسل الأمر بهذا الشكل:\n`.خبث @user1 @user2 ... نص الرسالة`",
        buttons=menu()
    )

# -- استقبال الرسائل النصية -- #

@bot.on(events.NewMessage)
async def on_new_message(m):
    uid, txt = m.sender_id, m.raw_text.strip()

    # إضافة جلسة
    if uid in add_state:
        st = add_state[uid]
        if st["step"] == 1:
            if not txt.isdigit():
                return await m.reply("❌ يجب أن يكون api_id رقماً فقط.")
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
            add_state.pop(uid)
            return await m.reply("✅ تمت الإضافة بنجاح.", buttons=menu())
        if st["step"] == 5:
            try:
                await st["client"].sign_in(password=txt)
                sessions[st["phone"]] = st["client"].session.save()
                clients[st["phone"]] = st["client"]
                add_state.pop(uid)
                return await m.reply("✅ تمت الإضافة بنجاح.", buttons=menu())
            except Exception as e:
                add_state.pop(uid)
                return await m.reply(f"❌ خطأ: {e}")

    # إرسال رسالة عادية
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

            ok, bad = 0, 0
            is_user = False
            if target.startswith("@"):
                try:
                    entity = await bot.get_entity(target)
                    is_user = entity.__class__.__name__ == "User"
                except:
                    pass
            elif target.isdigit():
                is_user = True
            elif target.startswith("https://t.me/") or target.startswith("t.me/"):
                if "joinchat" in target:
                    is_user = False
                else:
                    try:
                        entity = await bot.get_entity(target)
                        is_user = entity.__class__.__name__ == "User"
                    except:
                        pass

            for n, cl in clients.items():
                try:
                    if not is_user:
                        joined = await join_channel(cl, target)
                        if not joined:
                            print(f"[{n}] فشل الانضمام، تم تخطي.")
                            bad += 1
                            continue
                        await asyncio.sleep(5)
                    await cl.send_message(await cl.get_entity(target), st["msg"])
                    ok += 1
                except FloodWaitError as fe:
                    print(f"[{n}] توقف مؤقت لفترة {fe.seconds} ثانية بسبب فلوود.")
                    await asyncio.sleep(fe.seconds)
                except Exception as e:
                    bad += 1
                    print(f"[{n}] خطأ: {e}")

            return await m.reply(f"✅ أُرسلت الرسائل.\nنجاح: {ok} | فشل: {bad}", buttons=menu())

    # أمر خبث
    if txt.startswith(".خبث"):
        if not await is_owner(m):
            return await m.reply("🚫 هذا الأمر خاص بالمالك فقط.")

        parts = txt.split(maxsplit=2)
        if len(parts) < 3:
            return await m.reply("❌ الصيغة: .خبث @user1 @user2 ... نص الرسالة")

        targets = parts[1].split()
        msg_text = parts[2]

        await m.reply("🔥 جاري إرسال الرسائل الموقتة...")

        for n, cl in clients.items():
            for target in targets:
                try:
                    entity = await cl.get_entity(target)
                    sent_msg = await cl.send_message(entity, msg_text)
                    await asyncio.sleep(3)
                    await cl.delete_messages(entity, sent_msg.id, revoke=True)
                except Exception as e:
                    print(f"[{n}] خطأ في أمر خبث: {e}")

        return await m.reply("✅ تم إرسال الرسائل الموقتة وحُذفت بعد 3 ثواني.")

@bot.on(events.CallbackQuery(data=b"export_sessions"))
async def export_sessions(e):
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

@bot.on(events.NewMessage(pattern=r"^/start$"))
async def start(e): 
    await e.respond("🟢 مرحباً، اختر من الأزرار:", buttons=menu())

async def main():
    await bot.start(bot_token=bot_token)
    print("✅ Bot is online")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
