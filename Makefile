PYTHON ?= python3

.PHONY: help
help:
	@echo "Targets:"
	@echo "  run-core       Run assistant-core locally"
	@echo "  run-gateway    Run api-gateway locally"
	@echo "  run-connector  Run connector-service locally"
	@echo "  run-worker     Run job-worker locally"
	@echo "  web-install    Install frontend dependencies"

.PHONY: run-core
run-core:
	cd assistant-core && uvicorn app.main:app --reload --port 18001

.PHONY: run-gateway
run-gateway:
	cd api-gateway && uvicorn app.main:app --reload --port 18000

.PHONY: run-connector
run-connector:
	cd connector-service && uvicorn app.main:app --reload --port 18002

.PHONY: run-worker
run-worker:
	cd job-worker && $(PYTHON) -m app.worker

.PHONY: web-install
web-install:
	cd console-web && npm install && cd ../chat-widget && npm install

.PHONY: infra-up
infra-up:
	docker compose up -d mysql redis

.PHONY: infra-down
infra-down:
	docker compose down

.PHONY: export-openapi
export-openapi:
	python3 scripts/export_openapi.py
