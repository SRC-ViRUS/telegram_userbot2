# -*- coding: utf-8 -*-
import asyncio
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, UserAlreadyParticipantError, UserNotMutualContactError, FloodWaitError
from telethon.tl.functions.channels import JoinChannelRequest, GetChannelsRequest
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
        [Button.inline("👦 عرض شتائم الولد", b"show_boy"), Button.inline("👧 عرض شتائم البنت", b"show_girl")]
    ]

def sess_btns(pref): return [[Button.inline(n, f"{pref}:{n}".encode())] for n in sessions]

async def join_channel(client, target):
    """يحاول ينضم الحساب للقناة/المجموعة"""
    try:
        # إذا الرابط دعوة خاصة يبدأ بـ 'https://t.me/joinchat/'
        if target.startswith("https://t.me/joinchat/") or target.startswith("t.me/joinchat/"):
            hash_invite = target.split("/")[-1]
            await client(ImportChatInviteRequest(hash_invite))
        else:
            await client(JoinChannelRequest(target))
        return True
    except UserAlreadyParticipantError:
        # الحساب منضم أصلاً
        return True
    except Exception as e:
        print(f"خطأ بالانضمام: {e}")
        return False

@bot.on(events.CallbackQuery(data=b"snd"))
async def _(e):
    send_state[e.sender_id] = {"step": 1}
    await e.edit("✉️ أرسل الرسالة التي تريد إرسالها لكل الجلسات:")

@bot.on(events.NewMessage)
async def _(m):
    uid, txt = m.sender_id, m.raw_text.strip()

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
            # محاولة معرفة هل الهدف يوزر أو قناة/مجموعة
            if target.startswith("@"):
                try:
                    entity = await bot.get_entity(target)
                    is_user = entity.__class__.__name__ == "User"
                except:
                    pass
            elif target.isdigit():
                is_user = True
            elif target.startswith("https://t.me/") or target.startswith("t.me/"):
                # لو الرابط يحتوي joinchat فمجموعة خاصة، غيرها قناة أو يوزر
                if "joinchat" in target:
                    is_user = False
                else:
                    try:
                        entity = await bot.get_entity(target)
                        is_user = entity.__class__.__name__ == "User"
                    except:
                        pass

            # الإرسال للحسابات
            for n, cl in clients.items():
                try:
                    # تجربة الانضمام فقط لو الهدف ليس يوزر (مجموعة أو قناة)
                    if not is_user:
                        joined = await join_channel(cl, target)
                        if not joined:
                            print(f"[{n}] فشل الانضمام، تم تخطي.")
                            bad += 1
                            continue
                        # ننتظر 5 ثواني بين كل حساب لإرسال الرسالة
                        await asyncio.sleep(5)
                    else:
                        # لو يوزر نرسل فوراً
                        pass

                    await cl.send_message(await cl.get_entity(target), st["msg"])
                    ok += 1
                except FloodWaitError as fe:
                    print(f"[{n}] توقف مؤقت لفترة {fe.seconds} ثانية بسبب فلوود.")
                    await asyncio.sleep(fe.seconds)
                except Exception as e:
                    bad += 1
                    print(f"[{n}] خطأ: {e}")

            await m.reply(f"✅ أُرسلت الرسائل.\nنجاح: {ok} | فشل: {bad}", buttons=menu())

# بقية الكود كما هو (إضافة جلسات، حذف جلسات، شتائم، الخ...)

@bot.on(events.NewMessage(pattern=r"^/start$"))
async def start(e): await e.respond("🟢 مرحباً، اختر من الأزرار:", buttons=menu())

# ضع هنا باقي الكود القديم (الجلسات، الحذف، إضافة الشتائم...)

async def main():
    await bot.start(bot_token=bot_token)
    print("✅ Bot is online")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
