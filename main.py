import asyncio
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, UserAlreadyParticipantError, UserNotMutualContactError, FloodWaitError
from telethon.tl.functions.channels import JoinChannelRequest, GetChannelsRequest
from telethon.tl.functions.messages import ImportChatInviteRequest, DeleteMessagesRequest

api_id    = 20507759
api_hash  = "225d3a24d84c637b3b816d13cc7bd766"
bot_token = "7644214767:AAGOlYEiyF6yFWxiIX_jlwo9Ssj_Cb95oLU"

sessions, clients = {}, {}
add_state, send_state, save_state, khbth_state = {}, {}, {}, {}
stored_insults = {"👦": set(), "👧": set()}

bot = TelegramClient("bot", api_id, api_hash)

def menu():
    return [
        [Button.inline("📋 الجلسات", b"list"), Button.inline("📥 إضافة جلسة", b"add")],
        [Button.inline("🗑️ حذف جلسة", b"del"), Button.inline("✉️ إرسال رسالة", b"snd")],
        [Button.inline("🔥 خبث", b"khbth")],
        [Button.inline("➕ إضافة شتيمة", b"add_insult"), Button.inline("📤 استخراج الجلسات", b"export_sessions")],
        [Button.inline("👦 عرض شتائم الولد", b"show_boy"), Button.inline("👧 عرض شتائم البنت", b"show_girl")]
    ]

def sess_btns(pref): 
    return [[Button.inline(n, f"{pref}:{n}".encode())] for n in sessions]

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

@bot.on(events.CallbackQuery(data=b"snd"))
async def _(e):
    send_state[e.sender_id] = {"step": 1}
    await e.edit("✉️ أرسل الرسالة التي تريد إرسالها لكل الجلسات:")

@bot.on(events.CallbackQuery(data=b"khbth"))
async def _(e):
    khbth_state[e.sender_id] = {"step": 1}
    await e.edit("🔥 أمر خبث مفعل.\nأرسل المعرف (@user أو id أو رابط):")

@bot.on(events.NewMessage)
async def _(m):
    uid, txt = m.sender_id, m.raw_text.strip()

    # حالة إرسال رسالة لجميع الجلسات
    if uid in send_state:
        st = send_state[uid]
        if st["step"] == 1:
            st["msg"] = txt
            st["step"] = 2
            await m.reply("أرسل المعرف (@user أو id أو رابط):")
            return
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

            await m.reply(f"✅ أُرسلت الرسائل.\nنجاح: {ok} | فشل: {bad}", buttons=menu())

    # حالة أمر خبث
    elif uid in khbth_state:
        st = khbth_state[uid]
        if st["step"] == 1:
            st["target"] = txt
            st["step"] = 2
            await m.reply("🔥 الآن أرسل الرسالة التي تريد إرسالها:")
            return
        if st["step"] == 2:
            msg_text = txt
            target = st["target"]
            khbth_state.pop(uid)

            await m.reply("🔥 جاري الإرسال والحذف بعد 3 ثواني...")

            for n, cl in clients.items():
                try:
                    entity = await cl.get_entity(target)
                    sent_msg = await cl.send_message(entity, msg_text)
                    await asyncio.sleep(3)
                    await cl.delete_messages(entity, sent_msg.id, revoke=True)
                except Exception as e:
                    print(f"[{n}] خطأ في أمر خبث: {e}")

            await m.reply("✅ تم تنفيذ أمر خبث.", buttons=menu())

# ضع هنا باقي الكود القديم (الجلسات، الحذف، الشتائم، الخ...) 

@bot.on(events.NewMessage(pattern=r"^/start$"))
async def start(e): 
    await e.respond("🟢 مرحباً، اختر من الأزرار:", buttons=menu())

async def main():
    await bot.start(bot_token=bot_token)
    print("✅ Bot is online")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
