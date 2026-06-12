.DEFAULT_GOAL := help

.PHONY: help status

help: ## Show available commands
	@echo "Local AI Coding Assistant"
	@echo ""
	@echo "Available commands:"
	@echo "  make help    Show this help message"
	@echo "  make status  Show the current implementation phase"

status: ## Show the current implementation phase
	@echo "Phase 1 complete: project scaffold and documentation placeholders"
