import asyncio, os, datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest

# بيانات الاتصال
api_id = 11765349
api_hash = '67d3351652cc42239a42df8c17186d49'
session_string = "1ApWapzMBu3LbcZl_ZaB1NarDuo3EmApdJbr4sseU-pxJwoSnVt6M9BkgJ07IPt_6h4fDH6xGKqkxWJOPg3QnRFsucx8TAfxX5HVJgDdvlVbnkpCrl1ixinR7nVSoF_ydbgsu884_g9HY0wN3iHJ8ARmF0olQIIgC2YomNJbmXmigp_uJximTE1tZAQJDLJc_Qsp3TuT4trb7txpPSP0d6DUEt6pdmxlWrCNLH7VRntWchwIUg-IjAlF1Mz8dhkDP5MLDuIbd2qV5xizf2I0sdTiUSwwohES769qMKg_K4SEnwNQybqlZmCpPTGm5xuN8AIkJ8NveU4UezgFGSwW0l5qNaJiGUPw="

client = TelegramClient(StringSession(session_string), api_id, api_hash)
os.makedirs("downloads", exist_ok=True)

# متغيرات
muted_private = set()
muted_groups = {}
previous_name = None
change_name_task = None  # مهمة تغيير الاسم التلقائي
imitate_enabled = False
imitate_users = set()

# دالة للتحقق من صاحب البوت (مالك)
async def is_owner(event):
    me = await client.get_me()
    return event.sender_id == me.id

# --------- تغيير الاسم تلقائيًا كل دقيقة بدقة ---------
async def change_name_periodically():
    global previous_name
    me = await client.get_me()
    previous_name = me.first_name
    while True:
        now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=3)
        name = now.strftime('%I:%M')
        try:
            await client(UpdateProfileRequest(first_name=name))
        except Exception as e:
            print(f"خطأ بتغيير الاسم: {e}")

        seconds_to_next_minute = 60 - now.second - now.microsecond / 1_000_000
        await asyncio.sleep(seconds_to_next_minute)

@client.on(events.NewMessage(pattern=r"\.اسم مؤقت"))
async def start_changing_name(event):
    global change_name_task
    if not await is_owner(event):
        return await event.reply("🚫 هذا الأمر خاص بالمالك فقط.")
    if change_name_task and not change_name_task.done():
        return await event.reply("🔄 تغيير الاسم التلقائي مفعل مسبقًا.")
    change_name_task = asyncio.create_task(change_name_periodically())
    await event.reply("✅ بدأ تغيير الاسم التلقائي كل دقيقة بدقة عالية.")

@client.on(events.NewMessage(pattern=r"\.ايقاف الاسم"))
async def stop_changing_name(event):
    global change_name_task, previous_name
    if not await is_owner(event):
        return await event.reply("🚫 هذا الأمر خاص بالمالك فقط.")
    if change_name_task:
        change_name_task.cancel()
        change_name_task = None
    if previous_name:
        try:
            await client(UpdateProfileRequest(first_name=previous_name))
            await event.reply("🛑 تم إيقاف تغيير الاسم وإرجاع الاسم السابق.")
        except Exception as e:
            await event.reply(f"خطأ: {e}")
    else:
        await event.reply("❌ لا يوجد اسم سابق محفوظ.")

# --------- فحص ---------
@client.on(events.NewMessage(pattern=r"\.فحص"))
async def ping(event):
    if not await is_owner(event):
        return await event.reply("🚫 هذا الأمر خاص بالمالك فقط.")
    msg = await event.edit("✅ البوت شغال وبأفضل حال!")
    await client.send_message("me", "✨ حياتي الصعب، البوت شغال.")
    await asyncio.sleep(10)
    await msg.delete()

# --------- كشف معلومات القروب أو القناة ---------
@client.on(events.NewMessage(pattern=r"\.كشف"))
async def cmd_kashf(event):
    if not await is_owner(event):
        return await event.reply("🚫 هذا الأمر خاص بالمالك فقط.")
    chat = await event.get_chat()
    try:
        if getattr(chat, 'megagroup', False) or getattr(chat, 'broadcast', False):
            full = await client(GetFullChannelRequest(chat))
            title = full.chats[0].title
            id_ = full.chats[0].id
            members_count = full.full_chat.participants_count
            about = full.full_chat.about or "لا يوجد وصف"
        else:
            full = await client(GetFullChatRequest(chat))
            title = full.chats[0].title
            id_ = full.chats[0].id
            members_count = len(full.full_chat.participants)
            about = full.full_chat.about or "لا يوجد وصف"
    except:
        title = getattr(chat, 'title', '❌')
        id_ = getattr(chat, 'id', '❌')
        members_count = "❌"
        about = "❌"
    text = f"📊 معلومات:\n🔹 الاسم: {title}\n🔹 الايدي: `{id_}`\n🔹 عدد الأعضاء: {members_count}\n🔹 الوصف:\n{about}"
    await event.reply(text)

# --------- كتم / فك كتم ---------
@client.on(events.NewMessage(pattern=r"\.كتم$", func=lambda e: e.is_reply))
async def mute_user(event):
    if not await is_owner(event):
        return await event.reply("🚫 هذا الأمر خاص بالمالك فقط.")
    reply = await event.get_reply_message()
    if reply:
        uid, cid = reply.sender_id, event.chat_id
        (muted_private if event.is_private else muted_groups.setdefault(cid, set())).add(uid)
        msg = await event.edit("🔇 تم الكتم.")
        await asyncio.sleep(1)
        await msg.delete()

@client.on(events.NewMessage(pattern=r"\.الغاء الكتم$", func=lambda e: e.is_reply))
async def unmute_user(event):
    if not await is_owner(event):
        return await event.reply("🚫 هذا الأمر خاص بالمالك فقط.")
    reply = await event.get_reply_message()
    if reply:
        uid, cid = reply.sender_id, event.chat_id
        (muted_private if event.is_private else muted_groups.get(cid, set())).discard(uid)
        msg = await event.edit("🔊 تم فك الكتم.")
        await asyncio.sleep(1)
        await msg.delete()

@client.on(events.NewMessage(pattern=r"\.قائمة الكتم$"))
async def list_muted(event):
    if not await is_owner(event):
        return await event.reply("🚫 هذا الأمر خاص بالمالك فقط.")
    text = "📋 المكتومين:\n"
    for uid in muted_private:
        try:
            user = await client.get_entity(uid)
            text += f"🔸 خاص: {user.first_name}\n"
        except:
            continue
    for cid, users in muted_groups.items():
        if users:
            try:
                chat = await client.get_entity(cid)
                text += f"\n🔹 {chat.title}:\n"
                for uid in users:
                    try:
                        user = await client.get_entity(uid)
                        text += f" - {user.first_name}\n"
                    except:
                        continue
            except:
                continue
    await event.respond(text or "لا يوجد مكتومين.")

@client.on(events.NewMessage(pattern=r"\.مسح الكتم$"))
async def clear_mutes(event):
    if not await is_owner(event):
        return await event.reply("🚫 هذا الأمر خاص بالمالك فقط.")
    muted_private.clear()
    muted_groups.clear()
    msg = await event.edit("🗑️ تم مسح المكتومين.")
    await asyncio.sleep(1)
    await msg.delete()

# --------- حذف رسائل المكتومين وحفظ الوسائط ---------
@client.on(events.NewMessage(incoming=True))
async def handle_incoming(event):
    if (event.is_private and event.sender_id in muted_private) or \
       (event.chat_id in muted_groups and event.sender_id in muted_groups[event.chat_id]):
        return await event.delete()
    if event.is_private and event.media and getattr(event.media, 'ttl_seconds', None):
        try:
            path = await event.download_media("downloads/")
            await client.send_file("me", path, caption="📸 تم حفظ البصمة.")
            os.remove(path)
        except:
            pass

# --------- أوامر التقليد ---------
async def get_user_id_from_arg_or_reply(event):
    if event.is_reply:
        reply = await event.get_reply_message()
        if reply:
            return reply.sender_id
    arg = event.pattern_match.group(1)
    if arg:
        if arg.isdigit():
            return int(arg)
        try:
            user = await event.client.get_entity(arg)
            return user.id
        except:
            return None
    return None

@client.on(events.NewMessage(pattern=r"\.تقليد(?:\s+(\S+))?$"))
async def enable_imitate(event):
    global imitate_enabled, imitate_users
    if not await is_owner(event):
        return await event.reply("🚫 هذا الأمر خاص بالمالك فقط.")
    user_id = await get_user_id_from_arg_or_reply(event)
    if user_id:
        imitate_users.add(user_id)
        await event.reply(f"✅ تم تفعيل التقليد للمستخدم `{user_id}`.")
    else:
        imitate_enabled = True
        await event.reply("✅ تم تفعيل التقليد في هذه المحادثة.")

@client.on(events.NewMessage(pattern=r"\.لاتقلد(?:\s+(\S+))?$"))
async def disable_imitate(event):
    global imitate_enabled, imitate_users
    if not await is_owner(event):
        return await event.reply("🚫 هذا الأمر خاص بالمالك فقط.")
    user_id = await get_user_id_from_arg_or_reply(event)
    if user_id:
        imitate_users.discard(user_id)
        await event.reply(f"⛔ تم إيقاف التقليد للمستخدم `{user_id}`.")
    else:
        imitate_enabled = False
        await event.reply("⛔ تم إيقاف التقليد في هذه المحادثة.")

@client.on(events.NewMessage(incoming=True))
async def auto_imitate(event):
    global imitate_enabled, imitate_users
    me = await client.get_me()
    if event.sender_id == me.id or (event.sender and event.sender.bot):
        return
    if imitate_enabled or event.sender_id in imitate_users:
        try:
            if event.text:
                await event.respond(event.text)
            elif event.media:
                await event.respond(file=await event.download_media())
        except Exception as e:
            print(f"خطأ في التقليد: {e}")

# --------- عرض الأوامر ---------
@client.on(events.NewMessage(pattern=r"\.اوامر"))
async def list_commands(event):
    if not await is_owner(event):
        return await event.reply("🚫 هذا الأمر خاص بالمالك فقط.")
    commands_text = (
        "🧠 قائمة أوامر البوت:\n\n"
        ".فحص - التحقق من أن البوت يعمل\n"
        ".كشف - عرض معلومات القروب أو القناة\n"
        ".كتم - كتم المستخدم (بالرد على رسالته)\n"
        ".الغاء الكتم - فك كتم المستخدم (بالرد على رسالته)\n"
        ".قائمة الكتم - عرض جميع المستخدمين المكتومين\n"
        ".مسح الكتم - إزالة جميع الكتم\n"
        ".اسم مؤقت - تشغيل تغيير الاسم التلقائي حسب الوقت (كل دقيقة)\n"
        ".ايقاف الاسم - إيقاف تغيير الاسم وإرجاع الاسم السابق\n"
        ".تقليد [رد أو يوزر/آيدي] - تفعيل التقليد للمستخدم أو المحادثة\n"
        ".لاتقلد [رد أو يوزر/آيدي] - إيقاف التقليد للمستخدم أو المحادثة\n"
    )
    await event.respond(commands_text)

# --------- تشغيل البوت ---------
async def main():
    await client.start()
    print("✅ البوت يعمل الآن.")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
