import json
import re
import aiohttp
import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from loguru import logger

# ✅ توكن البوت (من متغيرات البيئة)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OWNER_ID_STR = os.environ.get("OWNER_ID")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set.")

if not OWNER_ID_STR:
    raise ValueError("OWNER_ID environment variable not set.")

try:
    OWNER_ID = int(OWNER_ID_STR)
except ValueError:
    raise ValueError("OWNER_ID environment variable must be an integer.")

storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)
CHANNELS_FILE = "channels.json"
USERS_FILE = "users.json"
CACHE = {}  # لتخزين مؤقت للفيديوهات والصور

class Form(StatesGroup):
    add_channel = State()
    broadcast = State()

# ======= إدارة القنوات (القائمة) =======
def load_channels():
    try:
        with open(CHANNELS_FILE, "r") as f:
            data = json.load(f)
            return data.get("channels", [])
    except FileNotFoundError:
        return []

def save_channels(channels):
    with open(CHANNELS_FILE, "w") as f:
        json.dump({"channels": channels}, f, indent=4)

# ======= إدارة المستخدمين =======
def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

# ======= إضافة مستخدم =======
def add_user(user_id):
    users = load_users()
    if str(user_id) not in users:
        users[str(user_id)] = {"downloads": 0}
        save_users(users)

# ======= تحديث عدد التنزيلات =======
def increment_download(user_id):
    users = load_users()
    if str(user_id) in users:
        users[str(user_id)]["downloads"] += 1
        save_users(users)

# ======= التحقق من الاشتراك =======
async def is_subscribed(user_id):
    channels = load_channels()
    for channel in channels:
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception as e:
            logger.error(f"Error checking subscription for user {user_id} in channel {channel}: {e}")
            return False
    return True if channels else True  # إذا ماكو قنوات تعتبر مشترك

# ======= إنشاء لوحة أزرار الاشتراك =======
def subscription_keyboard():
    channels = load_channels()
    buttons = []
    for ch in channels:
        buttons.append([InlineKeyboardButton(text=ch, url=f"https://t.me/{ch.lstrip('@')}")])
    buttons.append([InlineKeyboardButton(text="✅ تحقق", callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ======= دوال تنزيل الفيديو =======

async def download_tiktok(url, quality="hd"):
    if url in CACHE:
        return CACHE[url]

    async with aiohttp.ClientSession() as session:
        api_url = f"https://api.tikmate.app/api/convert?url={url}"
        async with session.get(api_url) as resp:
            if resp.status != 200:
                raise Exception(f"TikMate API returned status code {resp.status}")
            data = await resp.json()
            token = data.get('token')
            vid_id = data.get('id')
            if not token or not vid_id:
                raise Exception("فشل الحصول على رابط الفيديو من TikMate")
            video_url = f"https://tikmate.app/download/{token}/{vid_id}.mp4"
            CACHE[url] = video_url
            return video_url

async def download_facebook(url):
    if url in CACHE:
        return CACHE[url]

    async with aiohttp.ClientSession() as session:
        api_url = "https://fbdownloader.online/api/analyze"
        payload = {"q": url}
        headers = {"content-type": "application/x-www-form-urlencoded"}
        async with session.post(api_url, data=payload, headers=headers) as resp:
            if resp.status != 200:
                raise Exception(f"FBDownloader API returned status code {resp.status}")
            data = await resp.json()
            if 'links' not in data or not data['links']:
                raise Exception("فشل الحصول على رابط الفيديو من FBDownloader")
            video_url = data['links'][0]['url']
            CACHE[url] = video_url
            return video_url

async def download_instagram(url):
    if url in CACHE:
        return CACHE[url]

    async with aiohttp.ClientSession() as session:
        api_url = f"https://api.threadsphotodownloader.com/v2/media?url={url}"
        async with session.get(api_url) as resp:
            if resp.status != 200:
                raise Exception("فشل الحصول على الفيديو")
            data = await resp.json()
            if not data.get('data') or not data['data'].get('videos'):
                raise Exception("فشل الحصول على رابط الفيديو من Instagram")
            video_url = data['data']['videos'][0]['url']
            CACHE[url] = video_url
            return video_url

async def download_youtube(url):
    if url in CACHE:
        return CACHE[url]

    async with aiohttp.ClientSession() as session:
        api_url = f"https://loader.to/ajax/download.php?format=720&url={url}"
        async with session.get(api_url) as resp:
            if resp.status != 200:
                raise Exception("فشل الحصول على معلومات الفيديو من YouTube")
            data = await resp.json()
            download_url = data.get('download_url')
            if not download_url:
                raise Exception("فشل الحصول على رابط الفيديو")
            CACHE[url] = download_url
            return download_url

async def download_twitter(url):
    if url in CACHE:
        return CACHE[url]

    async with aiohttp.ClientSession() as session:
        api_url = f"https://api.vxtwitter.com/Twitter/Status/{url.split('/')[-1]}"
        async with session.get(api_url) as resp:
            if resp.status != 200:
                raise Exception("فشل الحصول على الفيديو من Twitter")
            data = await resp.json()
            video_url = data.get('media_extended', [{}])[0].get('url')
            if not video_url:
                raise Exception("فشل الحصول على رابط الفيديو من Twitter")
            CACHE[url] = video_url
            return video_url


# ======= كشف نوع الرابط =======
def detect_platform(url: str):
    url = url.lower()
    if any(x in url for x in ["tiktok.com", "vm.tiktok.com"]):
        return "tiktok"
    elif any(x in url for x in ["facebook.com", "fb.watch"]):
        return "facebook"
    elif "instagram.com" in url:
        return "instagram"
    elif any(x in url for x in ["youtube.com", "youtu.be"]):
        return "youtube"
    elif any(x in url for x in ["twitter.com", "x.com"]):
        return "twitter"
    else:
        return None

# ======= التعامل مع الرسائل =======

@dp.message(F.text.startswith("/start"))
async def cmd_start(message: types.Message):
    add_user(message.from_user.id)
    if await is_subscribed(message.from_user.id):
        await message.reply("أهلًا! أرسل لي رابط فيديو لتنزيله.")
    else:
        await message.reply("🚫 يجب الاشتراك في القنوات التالية أولاً:", reply_markup=subscription_keyboard())

@dp.callback_query(F.data == "check_sub")
async def callback_check_sub(call: types.CallbackQuery):
    if await is_subscribed(call.from_user.id):
        await call.message.edit_text("✅ أنت مشترك في كل القنوات، الآن يمكنك استخدام البوت.")
    else:
        await call.answer("❌ ما زلت غير مشترك في جميع القنوات.", show_alert=True)

@dp.message(F.text.regexp(r'https?://'))
async def handle_link(message: types.Message):
    add_user(message.from_user.id)
    if not await is_subscribed(message.from_user.id):
        await message.reply("🚫 يجب الاشتراك في القنوات التالية أولاً:", reply_markup=subscription_keyboard())
        return

    url = message.text.strip()
    platform = detect_platform(url)

    if not platform:
        await message.reply("❌ المنصة غير مدعومة حالياً.")
        return

    await message.reply("🚀 جاري التنزيل ...")

    try:
        if platform == "tiktok":
            video_url = await download_tiktok(url)
            await message.reply_video(video_url)
        elif platform == "facebook":
            video_url = await download_facebook(url)
            await message.reply_video(video_url)
        elif platform == "instagram":
            video_url = await download_instagram(url)
            await message.reply_video(video_url)
        elif platform == "youtube":
            video_url = await download_youtube(url)
            await message.reply_video(video_url)
        elif platform == "twitter":
            video_url = await download_twitter(url)
            await message.reply_video(video_url)
        increment_download(message.from_user.id)
    except Exception as e:
        logger.error(f"Error downloading video from {platform} for user {message.from_user.id}: {e}")
        await message.reply(f"❌ فشل التنزيل: {str(e)}")

# ======= لوحة تحكم المالك =======

def owner_keyboard():
    buttons = [
        [InlineKeyboardButton("📌 القنوات", callback_data="show_channels")],
        [InlineKeyboardButton("➕ إضافة قناة", callback_data="add_channel")],
        [InlineKeyboardButton("❌ حذف قناة", callback_data="remove_channel")],
        [InlineKeyboardButton("📊 عدد المستخدمين", callback_data="user_count")],
        [InlineKeyboardButton("📢 نشر رسالة", callback_data="broadcast")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(F.text.startswith("/admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id != OWNER_ID:
        await message.reply("🚫 أنت لست مالك البوت.")
        return
    await message.reply("مرحبًا بك في لوحة التحكم:", reply_markup=owner_keyboard())

@dp.callback_query(F.data == "show_channels")
async def show_channels(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        await call.answer("🚫 ممنوع", show_alert=True)
        return
    channels = load_channels()
    text = "📌 القنوات المطلوبة للاشتراك:\n\n"
    if not channels:
        text += "لا توجد قنوات بعد."
    else:
        for ch in channels:
            text += f"{ch}\n"
    await call.message.edit_text(text, reply_markup=owner_keyboard())

@dp.callback_query(F.data == "add_channel")
async def add_channel_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != OWNER_ID:
        await call.answer("🚫 ممنوع", show_alert=True)
        return
    await call.message.edit_text("📥 أرسل معرف القناة التي تريد إضافتها (مثلاً: @channelusername)")
    await state.set_state(Form.add_channel)

@dp.message(Form.add_channel)
async def process_add_channel(message: types.Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    ch = message.text.strip()
    channels = load_channels()
    if ch not in channels:
        channels.append(ch)
        save_channels(channels)
        await message.reply(f"✅ تم إضافة القناة: {ch}")
    else:
        await message.reply("⚠️ القناة موجودة بالفعل.")
    await state.clear()

@dp.callback_query(F.data == "remove_channel")
async def remove_channel_start(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        await call.answer("🚫 ممنوع", show_alert=True)
        return
    channels = load_channels()
    if not channels:
        await call.message.edit_text("لا توجد قنوات للحذف.", reply_markup=owner_keyboard())
        return

    buttons = []
    for ch in channels:
        buttons.append([InlineKeyboardButton(ch, callback_data=f"del_{ch}")])
    buttons.append([InlineKeyboardButton("رجوع", callback_data="admin_back")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await call.message.edit_text("❌ اختر قناة للحذف:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("del_"))
async def delete_channel(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        await call.answer("🚫 ممنوع", show_alert=True)
        return
    ch = call.data[4:]
    channels = load_channels()
    if ch in channels:
        channels.remove(ch)
        save_channels(channels)
        await call.message.edit_text(f"✅ تم حذف القناة: {ch}", reply_markup=owner_keyboard())
    else:
        await call.answer("⚠️ القناة غير موجودة.", show_alert=True)

@dp.callback_query(F.data == "admin_back")
async def admin_back(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        await call.answer("🚫 ممنوع", show_alert=True)
        return
    await call.message.edit_text("مرحبًا بك في لوحة التحكم:", reply_markup=owner_keyboard())

@dp.callback_query(F.data == "user_count")
async def user_count(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        await call.answer("🚫 ممنوع", show_alert=True)
        return
    users = load_users()
    await call.message.edit_text(f"👥 عدد المستخدمين المسجلين: {len(users)}", reply_markup=owner_keyboard())

@dp.callback_query(F.data == "broadcast")
async def broadcast_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != OWNER_ID:
        await call.answer("🚫 ممنوع", show_alert=True)
        return
    await call.message.edit_text("📢 أرسل الرسالة التي تريد نشرها:")
    await state.set_state(Form.broadcast)

@dp.message(Form.broadcast)
async def process_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    users = load_users()
    count = 0
    for user_id in users:
        try:
            await bot.send_message(int(user_id), message.text)
            count += 1
        except Exception as e:
            logger.error(f"Error sending broadcast message to user {user_id}: {e}")
    await message.reply(f"✅ تم إرسال الرسالة لـ {count} مستخدمًا.")
    await state.clear()

# ========== تشغيل البوت ==========
async def main():
    logger.add("bot.log", rotation="10 MB")
    logger.info("Bot is starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
