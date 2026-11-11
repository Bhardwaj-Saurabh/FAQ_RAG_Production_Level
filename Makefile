.PHONY: help setup test lint format typecheck check

help: ## List available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

setup: ## Install the package and dev tools with uv
	uv sync

test: ## Run the test suite (no API key or network needed)
	uv run pytest -q

lint: ## Check style and likely bugs
	uv run ruff check .
	uv run ruff format --check .

format: ## Auto-fix lint issues and format code
	uv run ruff check --fix .
	uv run ruff format .

typecheck: ## Static type check (strict)
	uv run mypy

check: lint typecheck test ## Everything CI runs
