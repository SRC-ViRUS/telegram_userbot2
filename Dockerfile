FROM python:3.12-slim

# تثبيت ffmpeg و libopus
RUN apt-get update && apt-get install -y ffmpeg libopus-dev

# إعداد مجلد العمل
WORKDIR /app

# نسخ كل الملفات إلى الحاوية
COPY . /app

# تثبيت مكتبات بايثون
RUN pip install --no-cache-dir -r requirements.txt

# تشغيل البوت
CMD ["python", "main.py"]
