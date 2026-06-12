.DEFAULT_GOAL := help

.PHONY: help install-backend run-backend status

help: ## Show available commands
	@echo "Local AI Coding Assistant"
	@echo ""
	@echo "Available commands:"
	@echo "  make help             Show this help message"
	@echo "  make install-backend  Install backend dependencies"
	@echo "  make run-backend      Start the FastAPI development server"
	@echo "  make status           Show the current implementation phase"

install-backend: ## Install backend dependencies
	cd backend && python3 -m pip install -r requirements.txt

run-backend: ## Start the FastAPI development server
	cd backend && python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

status: ## Show the current implementation phase
	@echo "Phase 3 complete: Bearer API key authentication for protected endpoints"
