.DEFAULT_GOAL := help

.PHONY: docker-build docker-down docker-logs docker-up help install-backend install-dev install-frontend run-backend run-frontend setup setup-ollama-smoke smoke smoke-docker start status test test-backend test-backend-docker test-docker test-frontend test-frontend-docker test-ollama test-ollama-smoke upgrade validate-env

help: ## Show available commands
	@echo "Local AI Coding Assistant"
	@echo ""
	@echo "Available commands:"
	@echo "  make help              Show this help message"
	@echo "  make install-backend   Install backend dependencies"
	@echo "  make install-dev       Install backend and test dependencies"
	@echo "  make install-frontend  Install frontend dependencies"
	@echo "  make run-backend       Start the FastAPI development server"
	@echo "  make run-frontend      Start the Vite development server"
	@echo "  make setup             Install local development dependencies"
	@echo "  make start             Start backend and frontend together"
	@echo "  make test              Run backend and frontend tests"
	@echo "  make test-backend      Run the backend pytest suite"
	@echo "  make test-frontend     Run frontend lint, unit tests, and build"
	@echo "  make test-docker       Run backend and frontend tests in Docker"
	@echo "  make smoke             Run a quick local backend/frontend smoke check"
	@echo "  make smoke-docker      Run a quick Docker smoke check"
	@echo "  make test-ollama       Run optional live Ollama tests"
	@echo "  make setup-ollama-smoke Pull tiny CPU-friendly Ollama smoke models"
	@echo "  make test-ollama-smoke Run optional live Ollama AI-flow smoke tests"
	@echo "  make docker-build      Build the backend and frontend images"
	@echo "  make docker-up         Build and start the Compose services"
	@echo "  make docker-down       Stop and remove the Compose services"
	@echo "  make docker-logs       Follow Compose service logs"
	@echo "  make validate-env      Validate local deployment env files"
	@echo "  make upgrade           Back up data before a dry-run production upgrade"
	@echo "  make status            Show the current implementation phase"

install-backend: ## Install backend dependencies
	cd backend && python3 -m pip install -r requirements.txt

install-dev: ## Install backend and test dependencies
	python3 -m pip install -r backend/requirements-dev.txt

install-frontend: ## Install frontend dependencies
	cd frontend && npm install

run-backend: ## Start the FastAPI development server
	cd backend && python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-frontend: ## Start the Vite development server
	cd frontend && npm run dev

setup: ## Install local development dependencies
	bash scripts/setup.sh

start: ## Start backend and frontend together
	bash scripts/start.sh

docker-build: ## Build the backend and frontend images
	docker compose build

docker-up: ## Build and start the Compose services
	docker compose up --build --detach

docker-down: ## Stop and remove the Compose services
	docker compose down

docker-logs: ## Follow Compose service logs
	docker compose logs --follow

test-backend: ## Run the backend pytest suite
	python3 -m pytest

test-frontend: ## Run frontend lint, unit tests, and production build
	cd frontend && npm run lint && npm run test:run && npm run build

test: test-backend test-frontend ## Run backend and frontend tests

test-backend-docker: ## Run backend tests in Docker
	docker compose -f docker-compose.test.yml run --rm backend-test

test-frontend-docker: ## Run frontend tests in Docker
	docker compose -f docker-compose.test.yml run --rm frontend-test

test-docker: test-backend-docker test-frontend-docker ## Run backend and frontend tests in Docker
	docker compose -f docker-compose.test.yml down --remove-orphans

smoke: ## Run quick local backend/frontend smoke checks
	python3 -m pytest tests/test_health.py tests/test_component_capabilities.py
	cd frontend && npm run lint

smoke-docker: ## Run quick Docker smoke checks
	docker compose -f docker-compose.test.yml run --rm backend-test python -m pytest tests/test_health.py tests/test_component_capabilities.py
	docker compose -f docker-compose.test.yml run --rm frontend-test npm run lint
	docker compose -f docker-compose.test.yml down --remove-orphans

validate-env: ## Validate local deployment env files
	python3 scripts/validate_env.py

upgrade: ## Validate env and back up data before a dry-run production upgrade
	python3 scripts/upgrade.py

test-ollama: ## Run optional live Ollama tests
	RUN_OLLAMA_TESTS=1 python3 -m pytest -m ollama

setup-ollama-smoke: ## Pull tiny CPU-friendly Ollama smoke-test models
	python3 scripts/setup_ollama_smoke.py

test-ollama-smoke: ## Run optional live Ollama app-flow smoke tests
	python3 -m pytest tests/test_ollama_smoke.py -m ollama

status: ## Show the current implementation phase
	@echo "Phase 9 complete: local and Dockerized test infrastructure"
