FROM python:3.12-slim

WORKDIR /app

# Создаем директории для данных и логов
RUN mkdir -p /app/data /app/logs

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
