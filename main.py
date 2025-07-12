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
add_state, send_state, save_state = {}, {}, {}
stored_insults = {"👦": set(), "👧": set()}

bot = TelegramClient("bot", api_id, api_hash)

def menu():
    return [
        [Button.inline("📋 الجلسات", b"list"), Button.inline("📥 إضافة جلسة", b"add")],
        [Button.inline("🗑️ حذف جلسة", b"del"), Button.inline("✉️ إرسال رسالة", b"snd")],
        [Button.inline("➕ إضافة شتيمة", b"add_insult"), Button.inline("📤 استخراج الجلسات", b"export_sessions")],
        [Button.inline("👦 عرض شتائم الولد", b"show_boy"), Button.inline("👧 عرض شتائم البنت", b"show_girl")],
        [Button.inline("💀 خبث", b"khabath")]  # زر خبث الجديد
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

@bot.on(events.CallbackQuery(data=b"snd"))
async def _(e):
    send_state[e.sender_id] = {"step": 1}
    await e.edit("✉️ أرسل الرسالة التي تريد إرسالها لكل الجلسات:")

@bot.on(events.CallbackQuery(data=b"khabath"))
async def _(e):
    if e.sender_id not in clients:
        await e.answer("🚫 هذا الأمر خاص بالمالك فقط.", alert=True)
        return
    send_state[e.sender_id] = {"step": "khabath_msg"}
    await e.edit("✍️ أرسل نص الرسالة التي تريد إرسالها بخبث:")

@bot.on(events.NewMessage)
async def _(m):
    uid, txt = m.sender_id, m.raw_text.strip()

    # معالجة إضافة جلسة، إرسال رسالة عامة، وحفظ الشتائم كما في كودك...

    # معالج خبث
    if uid in send_state and send_state[uid].get("step") == "khabath_msg":
        send_state[uid]["msg"] = txt
        send_state[uid]["step"] = "khabath_target"
        return await m.reply("🔍 أرسل معرف المستخدم (@username أو id) الذي تريد إرسال الرسالة له:")

    if uid in send_state and send_state[uid].get("step") == "khabath_target":
        target = txt
        msg_text = send_state[uid]["msg"]
        send_state.pop(uid)

        if uid not in clients:
            return await m.reply("🚫 لا تملك صلاحية القيام بهذه العملية.")

        client_ = clients[uid]

        try:
            entity = await client_.get_entity(target)
        except Exception as e:
            return await m.reply(f"❌ لم أتمكن من العثور على المستخدم: {e}")

        try:
            # إرسال الرسالة للهدف
            sent_msg = await client_.send_message(entity, msg_text)

            # بعد 3 ثواني حذف المحادثة من الطرفين
            await asyncio.sleep(3)
            await client_.delete_dialog(entity)
            await m.reply("✅ تم إرسال الرسالة وحذف المحادثة.")
        except Exception as e:
            await m.reply(f"❌ حدث خطأ أثناء الإرسال أو الحذف: {e}")

        return

    # معالج باقي الخطوات (إضافة جلسات، حذف، شتائم، إرسال رسائل عادية، الخ) هنا كما في كودك السابق...

@bot.on(events.NewMessage(pattern=r"^/start$"))
async def start(e): await e.respond("🟢 مرحباً، اختر من الأزرار:", buttons=menu())

# ضع هنا باقي كود الجلسات، الحذف، إضافة الشتائم، الخ بدون تغييرات

async def main():
    await bot.start(bot_token=bot_token)
    print("✅ Bot is online")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
