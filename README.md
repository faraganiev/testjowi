# Order System (Flask)

Мини-система управления заказами (тестовое JOWI).

## Быстрый старт (Docker)
1. Скопируйте переменные окружения:
   ```bash
   cp .env.example .env   # (Windows PowerShell: copy .env.example .env)
   ```
2. Сборка и запуск:
   ```bash
   docker compose up --build -d
   ```
3. Откройте: http://localhost:5000  
   Логин/пароль по умолчанию: **admin / admin**

Полезно:
```bash
docker compose logs -f web   # логи
docker compose down          # остановка
```

## Локальный запуск (без Docker)
```bash
python -m venv .venv
# Windows:
# .\.venv\Scripts\activate
# Linux/Mac:
# source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # (Windows PowerShell: copy .env.example .env)
python app.py
# Откройте http://127.0.0.1:5000
```

## Переменные окружения (.env)
Минимум:
```env
SECRET_KEY=change-me-please
FLASK_ENV=production
```

Опционально:
```env
PORT=5000
DATABASE_URL=sqlite:///database.db
# Для масштабирования real-time через Redis (необязательно для локали):
# REDIS_URL=redis://redis:6379/0
```

