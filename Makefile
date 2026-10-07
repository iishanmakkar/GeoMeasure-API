# GeoMeasure API — Makefile

.PHONY: dev build up down test lint typecheck fixtures clean help

PYTHON := C:/Python314/python.exe
PIP := $(PYTHON) -m pip

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ── Local dev ──────────────────────────────────────────────────────────────────
venv: ## Create local venv
	$(PYTHON) -m venv .venv

install: ## Install package in editable mode
	$(PYTHON) -m pip install -e ".[dev]"

dev: ## Run dev server with hot-reload
	$(PYTHON) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

fixtures: ## Generate binary test fixtures
	$(PYTHON) tests/fixtures/generate_fixtures.py

# ── Docker ─────────────────────────────────────────────────────────────────────
build: ## Build Docker image
	docker compose build

up: ## Start API container
	docker compose up

up-d: ## Start API container (detached)
	docker compose up -d

down: ## Stop containers
	docker compose down

# ── Quality ────────────────────────────────────────────────────────────────────
lint: ## Run ruff linter
	$(PYTHON) -m ruff check app/ tests/
	$(PYTHON) -m ruff format --check app/ tests/

format: ## Auto-format with ruff
	$(PYTHON) -m ruff format app/ tests/

typecheck: ## Run mypy
	$(PYTHON) -m mypy app/ --ignore-missing-imports

test: ## Run all tests with coverage
	$(PYTHON) -m pytest tests/ -v --cov=app --cov-report=term-missing --cov-fail-under=70

test-unit: ## Run unit tests only
	$(PYTHON) -m pytest tests/unit/ -v

test-integration: ## Run integration tests only
	$(PYTHON) -m pytest tests/integration/ -v

test-security: ## Run security tests only
	$(PYTHON) -m pytest tests/security/ -v

ci: lint typecheck test ## Run full CI pipeline locally

clean: ## Clean temp files
	-del /f geomeasure.db test_geomeasure.db test_ci.db 2>nul
	-for /d /r . %%d in (__pycache__) do @rd /s /q "%%d" 2>nul
	-rd /s /q .pytest_cache 2>nul
	-rd /s /q .coverage 2>nul
	-rd /s /q htmlcov 2>nul
