.DEFAULT_GOAL := help

.PHONY: docker-build docker-down docker-logs docker-up help install-backend install-dev install-frontend run-backend run-frontend status test

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
	@echo "  make test              Run the backend pytest suite"
	@echo "  make docker-build      Build the backend and frontend images"
	@echo "  make docker-up         Build and start the Compose services"
	@echo "  make docker-down       Stop and remove the Compose services"
	@echo "  make docker-logs       Follow Compose service logs"
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

docker-build: ## Build the backend and frontend images
	docker compose build

docker-up: ## Build and start the Compose services
	docker compose up --build --detach

docker-down: ## Stop and remove the Compose services
	docker compose down

docker-logs: ## Follow Compose service logs
	docker compose logs --follow

test: ## Run the backend pytest suite
	python3 -m pytest

status: ## Show the current implementation phase
	@echo "Phase 9 complete: automated FastAPI tests with pytest"
