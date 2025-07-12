from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
import asyncio, json, os

# بيانات البوت
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
monitoring = False
user_states = {}

bot = TelegramClient("bot", api_id, api_hash)

# تشغيل الجلسات وتجاهل الجلسات التالفة
async def start_all_sessions():
    bad_sessions = []
    for name, string in sessions.items():
        try:
            client = TelegramClient(StringSession(string), api_id, api_hash)
            await client.start()
            clients[name] = client
            print(f"✅ Session {name} started")
        except Exception as e:
            print(f"❌ Failed to start {name}: {e}")
            bad_sessions.append(name)

    for name in bad_sessions:
        del sessions[name]
    if bad_sessions:
        with open("sessions.json", "w") as f:
            json.dump(sessions, f)
        print(f"🗑️ تم حذف الجلسات المعطوبة: {bad_sessions}")

@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    buttons = [
        [Button.text("📋 حساباتي")],
        [Button.text("➕ جلسة تلقائية"), Button.text("🗑 حذف جلسة")],
        [Button.text("📶 صعود الاتصال"), Button.text("⛔️ إيقاف الاتصال")]
    ]
    await event.respond("🔘 تحكم كامل بالبوت عبر الأزرار:", buttons=buttons)

@bot.on(events.NewMessage)
async def handler(event):
    chat_id = str(event.sender_id)
    text = event.raw_text.strip()

    if text == "📋 حساباتي":
        if not sessions:
            await event.reply("❌ لا توجد حسابات.")
        else:
            msg = "📋 حسابات الجلسات:\n\n"
            for name in sessions:
                status = "✅" if name in clients else "❌"
                msg += f"• {name} {status}\n"
            await event.reply(msg)
        return

    elif text == "➕ جلسة تلقائية":
        user_states[chat_id] = {"step": "api_id"}
        await event.reply("📝 أرسل الآن الـ api_id:")
        return

    elif text == "🗑 حذف جلسة":
        await event.reply("🗑️ أرسل الأمر هكذا:\n/حذف_جلسة <رقم الهاتف>")
        return

    elif text == "📶 صعود الاتصال":
        global monitoring
        if monitoring:
            await event.reply("🚀 المراقبة شغالة مسبقاً.")
            return
        monitoring = True
        await event.reply("📶 بدأت مراقبة الصعود والنزول...")

        async def monitor():
            statuses = {}
            while monitoring:
                for name, client in clients.items():
                    try:
                        me = await client.get_me()
                        entity = await client.get_entity(me.id)
                        status = entity.status.class_name
                        if statuses.get(name) != status:
                            statuses[name] = status
                            msg = f"🟢 [{name}] متصل" if "Online" in status else f"🔴 [{name}] غير متصل"
                            await bot.send_message(event.chat_id, msg)
                    except:
                        continue
                await asyncio.sleep(10)

        asyncio.create_task(monitor())
        return

    elif text == "⛔️ إيقاف الاتصال":
        monitoring = False
        await event.reply("🛑 تم إيقاف المراقبة.")
        return

    if chat_id in user_states:
        state = user_states[chat_id]

        if state["step"] == "api_id":
            try:
                state["api_id"] = int(text)
                state["step"] = "api_hash"
                await event.reply("🔐 أرسل الآن الـ api_hash:")
            except:
                await event.reply("❌ api_id غير صالح. حاول مرة أخرى.")
            return

        elif state["step"] == "api_hash":
            state["api_hash"] = text
            state["step"] = "phone"
            await event.reply("📱 أرسل رقم الهاتف مع المفتاح الدولي (مثال: +9647700000000):")
            return

        elif state["step"] == "phone":
            state["phone"] = text
            state["client"] = TelegramClient(StringSession(), state["api_id"], state["api_hash"])
            await state["client"].connect()
            try:
                await state["client"].send_code_request(state["phone"])
                state["step"] = "code"
                await event.reply("📨 تم إرسال رمز التحقق. أرسله بهالشكل:\n`رمز 12345`", parse_mode="md")
            except Exception as e:
                await event.reply(f"❌ خطأ أثناء إرسال الرمز: {e}")
                del user_states[chat_id]
            return

        elif state["step"] == "code" and text.startswith("رمز "):
            code = text.split(" ", 1)[1]
            try:
                await state["client"].sign_in(state["phone"], code)
                session_string = state["client"].session.save()
                sessions[state["phone"]] = session_string
                clients[state["phone"]] = state["client"]
                with open("sessions.json", "w") as f:
                    json.dump(sessions, f)
                await state["client"].send_message("me", "✅ تم تسجيل الدخول من خلال البوت.")
                await event.reply(f"✅ تم إنشاء الجلسة وتسجيل الدخول الحقيقي: {state['phone']}")
            except Exception as e:
                if "2FA" in str(e) or "password" in str(e):
                    state["step"] = "2fa"
                    await event.reply("🔐 الحساب يحتوي رمز تحقق ثانوي.\nأرسله بهالشكل:\n`رمز_الثانوي your_password`", parse_mode="md")
                else:
                    await event.reply(f"❌ خطأ أثناء تسجيل الدخول: {e}")
                    print(f"[خطأ تسجيل الدخول - رمز التحقق] {e}")
                    del user_states[chat_id]
            return

        elif state["step"] == "2fa" and text.startswith("رمز_الثانوي "):
            password = text.split(" ", 1)[1]
            try:
                await state["client"].sign_in(password=password)
                session_string = state["client"].session.save()
                sessions[state["phone"]] = session_string
                clients[state["phone"]] = state["client"]
                with open("sessions.json", "w") as f:
                    json.dump(sessions, f)
                await state["client"].send_message("me", "✅ تم تسجيل الدخول من خلال البوت.")
                await event.reply(f"✅ تم إنشاء الجلسة وتسجيل الدخول الحقيقي: {state['phone']}")
            except Exception as e:
                await event.reply(f"❌ فشل رمز التحقق الثانوي: {e}")
                print(f"[خطأ 2FA] {e}")
            finally:
                del user_states[chat_id]
            return

@bot.on(events.NewMessage(pattern=r"^/حذف_جلسة (\S+)$"))
async def delete_session(event):
    name = event.pattern_match.group(1)
    if name in sessions:
        if name in clients:
            await clients[name].disconnect()
            del clients[name]
        del sessions[name]
        with open("sessions.json", "w") as f:
            json.dump(sessions, f)
        await event.reply(f"🗑️ تم حذف الجلسة: {name}")
    else:
        await event.reply("❌ الجلسة غير موجودة.")

async def main():
    await bot.start(bot_token=bot_token)
    await start_all_sessions()
    print("✅ البوت يعمل الآن...")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
