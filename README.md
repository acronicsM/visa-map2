# Visa Map 2 — Backend

Сервис визовых режимов стран мира.

## Быстрый старт

### Требования
- Docker Desktop
- Python 3.11
- Git

### Установка
```bash
# Клонировать репозиторий
git clone https://github.com/acronicsM/visa-map2.git
cd visa-map2/backend

# Создать виртуальное окружение
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1

# Установить зависимости
pip install -r requirements.txt

# Скопировать env
copy .env.example .env

# Поднять БД и Redis
docker-compose up -d

# Запустить сервер
uvicorn app.main:app --reload
```

### API документация
После запуска: http://localhost:8000/docs