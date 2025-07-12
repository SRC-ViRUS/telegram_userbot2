FROM python:3.10-bullseye

WORKDIR /app

RUN apt-get update && apt-get install -y ffmpeg libffi-dev build-essential git

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
