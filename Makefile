.PHONY: up down restart logs migrate seed build

# Разработка
up:
	docker-compose up -d

down:
	docker-compose down

restart:
	docker-compose restart app

logs:
	docker-compose logs -f app

# База данных
migrate:
	alembic upgrade head

seed:
	python scripts/seed_countries.py
	python scripts/seed_visa_policies.py
	python scripts/import_geodata.py

# Сброс БД (осторожно!)
db-reset:
	docker-compose down -v
	docker-compose up -d
	@echo "Waiting for postgres..."
	@timeout 15 /bin/sh -c 'until docker exec visamap_postgres pg_isready; do sleep 1; done'
	alembic upgrade head
	python scripts/seed_countries.py
	python scripts/seed_visa_policies.py
	python scripts/import_geodata.py

# Продакшн
prod-build:
	docker-compose -f docker-compose.prod.yml build

prod-up:
	docker-compose -f docker-compose.prod.yml up -d

prod-down:
	docker-compose -f docker-compose.prod.yml down

prod-logs:
	docker-compose -f docker-compose.prod.yml logs -f app

prod-migrate:
	docker-compose -f docker-compose.prod.yml exec app alembic upgrade head

# Разработка
dev:
	uvicorn app.main:app --reload

# Проверка
health:
	curl -s http://localhost:8000/health | python -m json.tool