ROOT = ..
COMPOSE_BASE = $(ROOT)/docker/docker-compose.yml
COMPOSE_INFRA = $(ROOT)/docker/docker-compose.infra.yml
COMPOSE_MONITORING = $(ROOT)/docker/docker-compose.monitoring.yml
ALL = -f $(COMPOSE_BASE) -f $(COMPOSE_INFRA) -f $(COMPOSE_MONITORING)

.PHONY: up down logs migrate build infra monitoring clean db restart

up:
	docker-compose $(ALL) up -d

build:
	docker-compose $(ALL) up -d --build

down:
	docker-compose $(ALL) down

clean:
	docker-compose $(ALL) down -v

infra:
	docker-compose -f $(COMPOSE_INFRA) up -d

monitoring:
	docker-compose -f $(COMPOSE_MONITORING) up -d

## make logs s=app
logs:
	docker-compose $(ALL) logs -f $(s)

migrate:
	docker-compose $(ALL) exec app sh -c "PYTHONPATH=app alembic upgrade head"

## make migration msg="add restaurants"
migration:
	docker-compose $(ALL) exec app sh -c "PYTHONPATH=app alembic revision --autogenerate -m '$(msg)'"

db:
	docker-compose $(ALL) exec postgres psql -U $${POSTGRES_USER} -d $${POSTGRES_DB}

## make restart s=app
restart:
	docker-compose $(ALL) restart $(s)