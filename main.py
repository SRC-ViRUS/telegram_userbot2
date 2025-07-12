import asyncio
import json
import os
import re
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.errors import UserAlreadyParticipantError

api_id = 20507759
api_hash = "225d3a24d84c637b3b816d13cc7bd766"
bot_token = "7644214767:AAGOlYEiyF6yFWxiIX_jlwo9Ssj_Cb95oLU"

SESS_FILE = "sessions.json"
sessions = {}
clients = {}
current_chat = None
waiting_for_link = {}

bot = TelegramClient("bot", api_id, api_hash)

def load_sessions():
    global sessions
    if os.path.exists(SESS_FILE):
        with open(SESS_FILE, "r", encoding="utf-8") as f:
            sessions = json.load(f)
    else:
        sessions = {}

def save_sessions():
    with open(SESS_FILE, "w", encoding="utf-8") as f:
        json.dump(sessions, f, ensure_ascii=False, indent=2)

async def start_all_sessions():
    for name, s in sessions.items():
        try:
            client = TelegramClient(StringSession(s), api_id, api_hash)
            await client.start()
            clients[name] = client
            print(f"[+] Session started: {name}")
        except Exception as e:
            print(f"[!] Failed {name}: {e}")

def main_menu():
    return [
        [Button.inline("🚀 صعود الاتصال", b"connect"), Button.inline("🛑 نزول الاتصال", b"disconnect")],
        [Button.inline("📋 عرض الجلسات", b"list")]
    ]

@bot.on(events.NewMessage(pattern="/start"))
async def start_cmd(e):
    await e.respond("👋 أهلاً بك – اختر من الأزرار:", buttons=main_menu())

@bot.on(events.CallbackQuery(data=b"connect"))
async def on_connect_button(event):
    user_id = event.sender_id
    waiting_for_link[user_id] = True
    await event.answer()
    await event.edit("📨 أرسل الآن رابط الكروب أو القناة أو المكالمة:")

@bot.on(events.NewMessage)
async def on_new_message(event):
    user_id = event.sender_id
    if user_id in waiting_for_link:
        link = event.raw_text.strip()
        waiting_for_link.pop(user_id)
        await handle_link(event, link)

async def extract_entity_from_link(bot, link):
    try:
        if "joinchat" in link or "/+" in link or "t.me/+" in link:
            # رابط دعوة خاصة
            code = link.split("+")[-1]
            result = await bot(ImportChatInviteRequest(code))
            return result.chats[0]

        if "?" in link:
            # رابط مكالمة صوتية / فيديو
            link = link.split("?")[0]

        # قناة أو كروب عام
        return await bot.get_entity(link)

    except Exception as e:
        raise Exception(f"❌ فشل استخراج الكيان:\n`{e}`")

async def handle_link(event, link):
    try:
        ent = await extract_entity_from_link(bot, link)
    except Exception as err:
        await event.respond(str(err), buttons=main_menu())
        return

    global current_chat
    current_chat = ent
    await event.respond("🔁 جارٍ صعود الحسابات...")

    for name, cl in clients.items():
        try:
            await cl(JoinChannelRequest(ent))
            await asyncio.sleep(1)
            await bot.send_message(event.chat_id, f"✅ [{name}] صعد الاتصال")
        except UserAlreadyParticipantError:
            await bot.send_message(event.chat_id, f"✅ [{name}] موجود مسبقاً")
        except Exception as ex:
            await bot.send_message(event.chat_id, f"❌ [{name}] خطأ: {ex}")

    await bot.send_message(event.chat_id, "✅ تم صعود جميع الحسابات.", buttons=main_menu())

@bot.on(events.CallbackQuery(data=b"disconnect"))
async def leave_all(e):
    await e.answer()
    if not current_chat:
        await e.edit("⚠️ لا يوجد كروب مُحدد.", buttons=main_menu())
        return
    await e.edit("🔁 جارٍ نزول الحسابات...")
    for name, cl in clients.items():
        try:
            await cl(LeaveChannelRequest(current_chat))
            await asyncio.sleep(1)
            await bot.send_message(e.chat_id, f"⬇️ [{name}] خرج")
        except Exception as ex:
            await bot.send_message(e.chat_id, f"❌ [{name}] خطأ: {ex}")
    await bot.send_message(e.chat_id, "✅ تم نزول الجميع.", buttons=main_menu())

async def main():
    load_sessions()
    await bot.start(bot_token=bot_token)
    await start_all_sessions()
    print("✅ البوت يعمل الآن...")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
