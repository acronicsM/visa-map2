# Visa Map 2 — Backend

API сервиса визовых режимов стран мира на FastAPI + PostgreSQL/PostGIS + Redis.

## Стек

- **FastAPI** — веб-фреймворк
- **PostgreSQL 16 + PostGIS 3** — база данных с геоданными
- **Redis 7** — кеширование
- **SQLAlchemy 2.0** (async) — ORM
- **Alembic** — миграции
- **Docker** — контейнеризация

## Быстрый старт (разработка)

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
.venv\Scripts\Activate.ps1  # Windows

# Установить зависимости
pip install -r requirements.txt

# Скопировать env
copy .env.example .env

# Поднять БД и Redis
docker-compose up -d

# Накатить миграции и заполнить данными
alembic upgrade head
python scripts/load_all_countries.py
python scripts/import_passport_index.py
python scripts/import_geodata.py
python scripts/seed_rss.py

# Запустить сервер
python -m uvicorn app.main:app --reload
```

### API документация
После запуска: http://localhost:8000/docs

## Эндпоинты

| Метод | URL | Описание |
|-------|-----|----------|
| GET | /health | Статус сервера и БД |
| GET | /countries | Список стран |
| GET | /countries?region=Europe | Фильтр по региону |
| GET | /countries?search=рос | Поиск по названию |
| GET | /countries/{iso2} | Карточка страны |
| GET | /countries/geodata | GeoJSON для карты |
| GET | /visa-map/{iso2} | Визовая карта для паспорта |
| GET | /visa-map/{iso2}/{iso2} | Детали визового режима |
| PATCH | /admin/visa-policies/{id} | Обновить визовый режим |
| POST | /admin/news-triggers | Создать триггер |
| GET | /admin/news-triggers | Список триггеров |
| PATCH | /admin/news-triggers/{id}/status | Обновить статус |

## Admin API

Требует заголовок `X-Api-Key`. Значение берётся из `.env` → `API_KEY`.

## Продакшн деплой
```bash
# Собрать и запустить
docker-compose -f docker-compose.prod.yml up -d

# Накатить миграции
docker-compose -f docker-compose.prod.yml exec app alembic upgrade head
```

## Структура проекта
```
backend/
├── app/
│   ├── main.py          # FastAPI приложение
│   ├── config.py        # Настройки из .env
│   ├── database.py      # SQLAlchemy async engine
│   ├── cache.py         # Redis утилиты
│   ├── dependencies.py  # API key авторизация
│   ├── exceptions.py    # Обработчики ошибок
│   ├── middleware.py    # Логирование запросов
│   ├── models/          # SQLAlchemy модели
│   ├── schemas/         # Pydantic схемы
│   ├── routers/         # FastAPI роутеры
│   └── services/        # Бизнес-логика
├── alembic/             # Миграции
├── scripts/             # Seed скрипты
├── Dockerfile
├── docker-compose.yml
└── docker-compose.prod.yml
```