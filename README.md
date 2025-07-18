# 🤖 Telegram Multi-Session Bot

بوت تيليجرام يتحكم بعدة حسابات (StringSession) باستخدام Telethon.

## 🚀 المميزات
- إنشاء جلسات تلقائيًا عبر البوت
- حذف الجلسات
- مراقبة اتصال الحسابات (صعود/نزول)
- يعمل عبر الأزرار بدون أوامر معقدة

## 🛠️ المتطلبات
- Python 3.10+
- مكتبة Telethon (`pip install -r requirements.txt`)

## ⚙️ الإعداد على Railway
1. اربط حسابك GitHub مع Railway
2. أنشئ مشروع جديد واربطه بهذا المستودع
3. في Settings > Variables أضف:
   - `BOT_TOKEN`: Your bot token from @BotFather.
   - `OWNER_ID`: Your Telegram user ID.
4. في Settings > Deploy حدد:
