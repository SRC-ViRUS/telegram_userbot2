import asyncio
import json
import os
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.tl.functions.channels import JoinChannelRequest
from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream import AudioPiped, VideoPiped
from yt_dlp import YoutubeDL

api_id = 20507759
api_hash = "225d3a24d84c637b3b816d13cc7bd766"
bot_token = "7644214767:AAGOlYEiyF6yFWxiIX_jlwo9Ssj_Cb95oLU"

# تحميل الجلسات
if os.path.exists("sessions.json"):
    with open("sessions.json", "r") as f:
        sessions = json.load(f)
else:
    sessions = {}

clients = {}
calls = {}
pending_media = {}  # مؤقت لتخزين ما سيتم تشغيله

bot = TelegramClient("bot", api_id, api_hash)

def get_stream_url(youtube_link):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_link, download=False)
        return info['url']

async def start_all_sessions():
    for name, string in sessions.items():
        try:
            client = TelegramClient(StringSession(string), api_id, api_hash)
            await client.start()
            clients[name] = client
            call = PyTgCalls(client)
            await call.start()
            calls[name] = call
            print(f"✅ Session started: {name}")
        except Exception as e:
            print(f"❌ Failed: {name} - {e}")

@bot.on(events.NewMessage(pattern="/start"))
async def start_cmd(event):
    buttons = [
        [Button.text("📋 حساباتي")],
        [Button.text("📥 أرسل رابط أو ملف لتشغيله في المكالمة")]
    ]
    await event.respond("👋 مرحباً بك، أرسل رابط يوتيوب أو ملف ميديا وسيتم تشغيله.", buttons=buttons)

@bot.on(events.NewMessage)
async def media_handler(event):
    sender = event.sender_id

    if event.file:
        # استلام ملف صوت/فيديو
        path = await event.download_media()
        pending_media[sender] = {"type": "file", "path": path}
        await event.respond("🎵 تم استلام الملف. كيف تريد تشغيله؟", buttons=[
            [Button.inline("✅ صوت فقط", b"audio"), Button.inline("🎥 بالفيديو", b"video")]
        ])
        return

    text = event.raw_text.strip()
    if text.startswith("http") and "youtube" in text:
        try:
            pending_media[sender] = {"type": "youtube", "link": text}
            await event.respond("📺 تم استلام رابط يوتيوب. كيف تريد تشغيله؟", buttons=[
                [Button.inline("✅ صوت فقط", b"audio"), Button.inline("🎥 بالفيديو", b"video")]
            ])
        except Exception as e:
            await event.reply(f"❌ فشل استخراج الرابط: {e}")
        return

@bot.on(events.CallbackQuery)
async def callback(event):
    sender = event.sender_id
    data = event.data.decode("utf-8")

    if sender not in pending_media:
        await event.answer("⛔ لا يوجد شيء لتشغيله")
        return

    media = pending_media.pop(sender)
    await event.edit("⏳ جارٍ التشغيل...")

    # شغّل على كل الحسابات
    for name, client in clients.items():
        try:
            call = calls.get(name)
            if not call:
                continue

            await client(JoinChannelRequest(event.chat.username or event.chat_id))

            if media["type"] == "file":
                if data == "audio":
                    await call.join_group_call(event.chat_id, AudioPiped(media["path"]))
                elif data == "video":
                    await call.join_group_call(event.chat_id, VideoPiped(media["path"]))

            elif media["type"] == "youtube":
                url = get_stream_url(media["link"])
                if data == "audio":
                    await call.join_group_call(event.chat_id, AudioPiped(url))
                elif data == "video":
                    await call.join_group_call(event.chat_id, VideoPiped(url))

            await bot.send_message(event.chat_id, f"✅ [{name}] شغّل المقطع.")
        except Exception as e:
            await bot.send_message(event.chat_id, f"❌ [{name}] فشل التشغيل: {e}")

async def main():
    await bot.start(bot_token=bot_token)
    await start_all_sessions()
    print("✅ البوت يعمل الآن...")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
