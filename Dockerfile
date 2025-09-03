# Базовый образ — стабильный Python 3.11
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Установим зависимости
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Кладём исходники внутрь образа (для прод). В dev мы ещё смонтируем томом.
COPY . /app

EXPOSE 5000

# Запуск через встроенный раннер (нам ок для демо)
CMD ["python", "app.py"]
