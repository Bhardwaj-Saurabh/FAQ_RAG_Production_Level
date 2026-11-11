.PHONY: help setup test

# Scripts run with `uv run python scripts/...` need the repo root on the
# import path so `import src...` works. Pytest gets it from pyproject.toml.
export PYTHONPATH := .

help: ## List available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

setup: ## Install dependencies with uv
	uv sync

test: ## Run the test suite (no API key or network needed)
	uv run pytest -q
