# -*- coding: utf-8 -*-
import asyncio, os, json, datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest

# ——— بيانات الاتصال ———
api_id = 11765349
api_hash = '67d3351652cc42239a42df8c17186d49'
session_string = " "1ApWapzMBu3LbcZl_ZaB1NarDuo3EmApdJbr4sseU-pxJwoSnVt6M9BkgJ07IPt_6h4fDH6xGKqkxWJOPg3QnRFsucx8TAfxX5HVJgDdvlVbnkpCrl1ixinR7nVSoF_ydbgsu884_g9HY0wN3iHJ8ARmF0olQIIgC2YomNJbmXmigp_uJximTE1tZAQJDLJc_Qsp3TuT4trb7txpPSP0d6DUEt6pdmxlWrCNLH7VRntWchwIUg-IjAlF1Mz8dhkDP5MLDuIbd2qV5xizf2I0sdTiUSwwohES769qMKg_K4SEnwNQybqlZmCpPTGm5xuN8AIkJ8NveU4UezgFGSwW0l5qNaJiGUPw="
client = TelegramClient(StringSession(session_string), api_id, api_hash)

# ——— مجلدات التخزين ———
os.makedirs("downloads", exist_ok=True)
os.makedirs("stamps",     exist_ok=True)
STAMPS_FILE = "stamps/stamps.json"

# ——— تحميل البصمات المحفوظة ———
if os.path.isfile(STAMPS_FILE):
    with open(STAMPS_FILE) as f:
        stamps = json.load(f)
else:
    stamps = {}

# ——— المتغيرات العالمية ———
muted_private, muted_groups      = set(), {}
previous_name, change_name_task  = None, None
imitate_users_data               = {}   # {user_id: last_message_id}

# ——— دوال مساعدة ———
async def is_owner(evt):
    return evt.sender_id == (await client.get_me()).id

def save_stamps():
    with open(STAMPS_FILE, "w") as f:
        json.dump(stamps, f)

async def extract_user_id(evt, arg):
    """يُرجِّع آيدي حسب: ردّ أو بارامتر (يوزر/رقم)."""
    if evt.is_reply:
        rep = await evt.get_reply_message()
        if rep: return rep.sender_id
    if arg:
        if arg.isdigit(): return int(arg)
        try:
            return (await client.get_entity(arg)).id
        except: return None
    return None

# ——— تغيير الاسم المؤقت ———
async def change_name_loop():
    global previous_name
    previous_name = (await client.get_me()).first_name
    while True:
        now = datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(hours=3)
        try:
            await client(UpdateProfileRequest(first_name=now.strftime('%I:%M')))
        except Exception as e:
            print("خطأ تغيير الاسم:", e)
        await asyncio.sleep(60-now.second-now.microsecond/1_000_000)

@client.on(events.NewMessage(pattern=r"\.اسم مؤقت"))
async def cmd_tempname(evt):
    global change_name_task
    if not await is_owner(evt): return
    if change_name_task and not change_name_task.done():
        return await evt.reply("🔄 مفعل سابقًا.")
    change_name_task = asyncio.create_task(change_name_loop())
    await evt.reply("✅ تم التفعيل.")

@client.on(events.NewMessage(pattern=r"\.ايقاف الاسم"))
async def cmd_stopname(evt):
    global change_name_task, previous_name
    if not await is_owner(evt): return
    if change_name_task: change_name_task.cancel(); change_name_task=None
    if previous_name:
        try: await client(UpdateProfileRequest(first_name=previous_name))
        except: pass
    await evt.reply("🛑 تم الإيقاف.")

# ——— فحص ———
@client.on(events.NewMessage(pattern=r"\.فحص"))
async def cmd_ping(evt):
    if not await is_owner(evt): return
    m = await evt.edit("✅ البوت شغال.")
    await client.send_message("me", "✨ البوت بخير.")
    await asyncio.sleep(10); await m.delete()

# ——— كشف معلومات القروب ———
@client.on(events.NewMessage(pattern=r"\.كشف"))
async def cmd_info(evt):
    if not await is_owner(evt): return
    chat = await evt.get_chat()
    try:
        if getattr(chat,'megagroup',False) or getattr(chat,'broadcast',False):
            full = await client(GetFullChannelRequest(chat))
            name,cid,about = full.chats[0].title, full.chats[0].id, full.full_chat.about or "—"
            members = full.full_chat.participants_count
        else:
            full = await client(GetFullChatRequest(chat))
            name,cid,about = full.chats[0].title, full.chats[0].id, full.full_chat.about or "—"
            members = len(full.full_chat.participants)
    except:
        name,cid,members,about = getattr(chat,'title','❓'), getattr(chat,'id','❓'),"❓","❓"
    await evt.reply(f"📊 **معلومات**\n🔹 الاسم: {name}\n🔹 الايدي: `{cid}`\n🔹 الأعضاء: {members}\n🔹 الوصف:\n{about}")

# ——— الكتم / فك الكتم ———
@client.on(events.NewMessage(pattern=r"\.كتم$", func=lambda e:e.is_reply))
async def cmd_mute(evt):
    if not await is_owner(evt): return
    rep = await evt.get_reply_message()
    (muted_private if evt.is_private else muted_groups.setdefault(evt.chat_id,set())).add(rep.sender_id)
    m = await evt.edit("🔇"); await asyncio.sleep(1); await m.delete()

@client.on(events.NewMessage(pattern=r"\.الغاء الكتم$", func=lambda e:e.is_reply))
async def cmd_unmute(evt):
    if not await is_owner(evt): return
    rep = await evt.get_reply_message()
    (muted_private if evt.is_private else muted_groups.get(evt.chat_id,set())).discard(rep.sender_id)
    m = await evt.edit("🔊"); await asyncio.sleep(1); await m.delete()

@client.on(events.NewMessage(pattern=r"\.قائمة الكتم$"))
async def cmd_listmutes(evt):
    if not await is_owner(evt): return
    txt="📋 **المكتومون**\n"
    for u in muted_private:
        try: txt+=f"🔸 خاص: {(await client.get_entity(u)).first_name}\n"
        except: pass
    for cid,users in muted_groups.items():
        if users:
            try:
                chat = await client.get_entity(cid)
                txt+=f"\n🔹 {chat.title}:\n"
                for u in users:
                    try: txt+=f"  — {(await client.get_entity(u)).first_name}\n"
                    except: pass
            except: pass
    await evt.respond(txt if txt.strip()!="📋 **المكتومون**" else "لا أحد.")

@client.on(events.NewMessage(pattern=r"\.مسح الكتم$"))
async def cmd_clearmutes(evt):
    if not await is_owner(evt): return
    muted_private.clear(); muted_groups.clear()
    m = await evt.edit("🗑️"); await asyncio.sleep(1); await m.delete()

# ——— حذف رسائل المكتومين + حفظ الوسائط المؤقتة ———
@client.on(events.NewMessage(incoming=True))
async def guard_and_auto_save(evt):
    if (evt.is_private and evt.sender_id in muted_private) or \
       (evt.chat_id in muted_groups and evt.sender_id in muted_groups[evt.chat_id]):
        return await evt.delete()
    if evt.is_private and evt.media and getattr(evt.media,'ttl_seconds',None):
        try:
            path = await evt.download_media("downloads/")
            await client.send_file("me", path, caption="📸 بصمة محفوظة تلقائيًا")
            os.remove(path)
        except: pass

# ——— أمر التقليد ———
@client.on(events.NewMessage(pattern=r"\.تقليد(?:\s+(\S+))?$"))
async def cmd_enable_imitate(evt):
    if not await is_owner(evt): return
    uid = await extract_user_id(evt, evt.pattern_match.group(1))
    if not uid: return await evt.reply("❗ حدِّد المستخدم برد أو يوزر/آيدي.")
    imitate_users_data[uid] = None
    await evt.delete()

@client.on(events.NewMessage(pattern=r"\.لاتقلد(?:\s+(\S+))?$"))
async def cmd_disable_imitate(evt):
    if not await is_owner(evt): return
    uid = await extract_user_id(evt, evt.pattern_match.group(1))
    if not uid: return await evt.reply("❗ حدِّد المستخدم.")
    imitate_users_data.pop(uid, None)
    await evt.delete()

@client.on(events.NewMessage(incoming=True))
async def imitator(evt):
    me = await client.get_me()
    uid = evt.sender_id
    if uid == me.id or (evt.sender and evt.sender.bot): return
    if uid not in imitate_users_data: return

    # لا يكرر نفس الرسالة
    if imitate_users_data[uid] == evt.id: return
    imitate_users_data[uid] = evt.id

    try:
        if evt.text:
            await evt.reply(evt.text)
        elif evt.media:
            tmp = await evt.download_media()
            await client.send_file(evt.chat_id, tmp, caption=getattr(evt,'text',None))
            os.remove(tmp)
    except Exception as e:
        print("خطأ تقليد:", e)

# ——— أوامر البصمات ———
@client.on(events.NewMessage(pattern=r"\.حفظبصمة (\S+)$", func=lambda e:e.is_reply))
async def cmd_save_stamp(evt):
    if not await is_owner(evt): return
    alias = evt.pattern_match.group(1).strip(". ")
    rep   = await evt.get_reply_message()
    if not rep or not rep.media: return await evt.reply("❗ رد على ملف صوتي/فيديو.")
    path = await rep.download_media(f"stamps/{alias}")
    stamps[alias] = path; save_stamps()
    await evt.reply(f"✅ حُفظت باسم .{alias}")

@client.on(events.NewMessage(pattern=r"\.حذفبصمة (\S+)$"))
async def cmd_del_stamp(evt):
    if not await is_owner(evt): return
    alias = evt.pattern_match.group(1).strip(". ")
    if alias in stamps:
        try: os.remove(stamps[alias])
        except: pass
        stamps.pop(alias); save_stamps()
        await evt.reply("🗑️ حُذفت.")
    else:
        await evt.reply("❌ غير موجودة.")

@client.on(events.NewMessage(pattern=r"\.قائمةبصمات$"))
async def cmd_list_stamps(evt):
    if not await is_owner(evt): return
    if not stamps: return await evt.reply("لا توجد بصمات.")
    await evt.respond("🎙️ **البصمات:**\n"+"\n".join(f"• .{a}" for a in stamps))

@client.on(events.NewMessage(pattern=r"^\.(\S+)$"))
async def send_stamp(evt):
    alias = evt.pattern_match.group(1)
    if alias in stamps:
        try: await evt.respond(file=stamps[alias])
        except Exception as e: await evt.reply(f"⚠️ {e}")

# ——— قائمة الأوامر ———
@client.on(events.NewMessage(pattern=r"\.اوامر$"))
async def cmd_help(evt):
    if not await is_owner(evt): return
    await evt.respond(
        "🧠 **قائمة الأوامر**\n"
        "• .فحص\n• .كشف\n• .كتم (رد)\n• .الغاء الكتم (رد)\n"
        "• .قائمة الكتم\n• .مسح الكتم\n"
        "• .اسم مؤقت / .ايقاف الاسم\n"
        "• .تقليد (رد أو يوزر/ID)\n• .لاتقلد (رد أو يوزر/ID)\n"
        "• .حفظبصمة <اسم> (رد)\n• .حذفبصمة <اسم>\n• .قائمةبصمات\n"
        "• .<اسم>  لإرسال البصمة\n"
    )

# ——— تشغيل البوت ———
async def main():
    await client.start()
    print("✅ البوت يعمل.")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
