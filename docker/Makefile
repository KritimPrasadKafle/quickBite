COMPOSE = docker compose
ROOT = ..
ENV_FILE = $(ROOT)/.env
COMPOSE_BASE = $(ROOT)/docker/docker-compose.yml
COMPOSE_INFRA = $(ROOT)/docker/docker-compose.infra.yml
COMPOSE_MONITORING = $(ROOT)/docker/docker-compose.monitoring.yml
ALL = --env-file $(ENV_FILE) -f $(COMPOSE_BASE) -f $(COMPOSE_INFRA) -f $(COMPOSE_MONITORING)

.PHONY: up down logs migrate build infra monitoring clean db restart

up:
	$(COMPOSE) $(ALL) up -d

build:
	$(COMPOSE) $(ALL) up -d --build

down:
	$(COMPOSE) $(ALL) down

clean:
	$(COMPOSE) $(ALL) down -v

infra:
	$(COMPOSE) --env-file $(ENV_FILE) -f $(COMPOSE_INFRA) up -d

monitoring:
	$(COMPOSE) --env-file $(ENV_FILE) -f $(COMPOSE_MONITORING) up -d

logs:
	$(COMPOSE) $(ALL) logs -f $(s)

migrate:
	$(COMPOSE) $(ALL) exec app sh -c "PYTHONPATH=app alembic upgrade head"

migration:
	$(COMPOSE) $(ALL) exec app sh -c "PYTHONPATH=app alembic revision --autogenerate -m '$(msg)'"

db:
	$(COMPOSE) $(ALL) exec postgres psql -U $${POSTGRES_USER} -d $${POSTGRES_DB}

restart:
	$(COMPOSE) $(ALL) restart $(s)