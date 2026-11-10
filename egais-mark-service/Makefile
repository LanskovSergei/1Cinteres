.PHONY: install test run up down logs

install:
	pip install -r requirements-dev.txt

test:
	pytest -q

run:
	uvicorn app.main:app --reload --port 8000

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f api
