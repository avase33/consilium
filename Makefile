.PHONY: install dev test run serve worker docker clean

install:
	pip install -e .

dev:
	pip install -e ".[dev,server,stream]"

test:
	pytest -q

run:
	python -m consilium research "electric vehicle charging market in Europe"

serve:
	uvicorn consilium.service.api:app --reload

worker:
	faststream run consilium.messaging.streams:app

docker:
	docker compose -f deploy/docker-compose.yml up --build

clean:
	rm -f *.db *.report.md *.report.json
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
