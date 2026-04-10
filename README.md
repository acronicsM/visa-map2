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
git clone https://github.com/acronicsM/visa-map2.git
cd visa-map2

py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1   # Windows
# source .venv/bin/activate  # Linux/macOS

pip install -r requirements.txt
copy .env.example .env     # или cp; заполнить переменные

docker-compose up -d

alembic upgrade head
python scripts/load_all_countries.py
python scripts/import_passport_index.py
python scripts/import_geodata.py
python scripts/seed_rss.py

python -m uvicorn app.main:app --reload --port 8000
```

Порты Postgres/Redis см. в `docker-compose.yml` (часто Postgres на хосте **5442**).

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
| GET | /countries/safety-final-scores | Карта `iso2 → safety_final_score` (Redis) |
| GET | /countries/geodata | GeoJSON для карты (кеш Redis) |
| GET | /visa-map/{iso2} | Визовая карта для паспорта |
| GET | /visa-map/{iso2}/{iso2} | Детали визового режима |
| PUT | /admin/countries/safety-final-scores | Импорт merged JSON безопасности (см. ниже) |
| PATCH | /admin/visa-policies/{id} | Обновить визовый режим |
| POST | /admin/news-triggers | Создать триггер |
| GET | /admin/news-triggers | Список триггеров |
| PATCH | /admin/news-triggers/{id}/status | Обновить статус |

## Admin API

Требует заголовок **`X-Api-Key`**. Значение — из `.env` → **`API_KEY`**.

## Импорт коэффициентов безопасности

**`PUT /admin/countries/safety-final-scores`** — тело JSON в формате merged-файла с корнем **`by_iso2`**. В каждой записи страны обязателен **`safety_final_score`** (0…100; чем выше, тем безопаснее); остальные поля игнорируются.

Что происходит при успешном запросе:

1. В **Redis** сохраняется полная карта `iso2 → safety_final_score` (ключ `countries:safety_final_scores:v1`, без TTL до следующей загрузки).
2. В **PostgreSQL** (`countries`) обновляются **`safety_level`**, **`safety_updated_at`**, **`safety_source`**, **`updated_at`** по порогам из настроек.
3. Сбрасывается кеш GeoJSON (`countries:geodata:v2`), чтобы на карте подтянулись новые **`safety_level`** в `properties` фич.

Уровни **`safety_level`**: `safe` \| `unsafe` \| `dangerous` — задаются порогами в `.env` (опционально):

| Переменная | По умолчанию | Смысл |
|------------|--------------|--------|
| `SAFETY_SCORE_SAFE_MIN` | `70` | при `score >=` → `safe` |
| `SAFETY_SCORE_UNSAFE_MIN` | `40` | иначе, если `score >=` этого порога → `unsafe`, ещё ниже → `dangerous` |

Должно выполняться `SAFETY_SCORE_SAFE_MIN` > `SAFETY_SCORE_UNSAFE_MIN`, иначе приложение не стартует.

**`GET /countries/safety-final-scores`** — публично отдаёт текущую карту баллов из Redis или `{}`, если импорт ещё не выполняли.

Перезапуск uvicorn **не** нужен при каждой подгрузке данных — только при деплое нового кода или смене переменных окружения, читаемых при старте.

Ответ **`PUT`**: `stored_count` (сколько кодов в импорте), `countries_safety_updated` (сколько строк в `countries` реально обновилось; может быть меньше, если в JSON есть коды без записи в БД).

## Продакшн деплой

```bash
docker-compose -f docker-compose.prod.yml up -d
docker-compose -f docker-compose.prod.yml exec app alembic upgrade head
```

## Структура проекта

```
visa-map2/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── cache.py
│   ├── dependencies.py
│   ├── exceptions.py
│   ├── middleware.py
│   ├── models/
│   ├── schemas/
│   ├── routers/
│   └── services/
├── alembic/
├── scripts/
├── Dockerfile
├── docker-compose.yml
├── docker-compose.prod.yml
└── requirements.txt
```
