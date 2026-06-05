# HackRitual — developer convenience targets
# Requires: uv (https://docs.astral.sh/uv/)
# Run from the repo root.
#
# Quick start:
#   make install-dev   # create .venv and install all deps
#   make test          # run the test suite
#   make serve         # start the dev server

UV := $(shell command -v uv 2>/dev/null || echo ~/.local/bin/uv)
BACKEND := backend

.PHONY: help install install-dev test test-backend serve migrate health info lint fmt

help:
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*##"}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

install:       ## Install production dependencies via uv
	cd $(BACKEND) && $(UV) sync

install-dev:   ## Install all dependencies including dev/test tools
	cd $(BACKEND) && $(UV) sync --extra dev

test: test-backend  ## Run all tests

test-backend:  ## Run the backend test suite via uv
	cd $(BACKEND) && $(UV) run pytest -v

serve:         ## Start the dev server with hot-reload on port 7860
	cd $(BACKEND) && $(UV) run hackritual serve --reload

migrate:       ## Run Alembic migrations (upgrade head)
	cd $(BACKEND) && $(UV) run hackritual migrate

health:        ## Check health of the running server (localhost:7860)
	cd $(BACKEND) && $(UV) run hackritual health

info:          ## Print current configuration (secrets masked)
	cd $(BACKEND) && $(UV) run hackritual info

lint:          ## Run ruff linter
	cd $(BACKEND) && $(UV) run ruff check app tests

fmt:           ## Run ruff formatter
	cd $(BACKEND) && $(UV) run ruff format app tests
