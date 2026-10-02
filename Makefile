UV ?= uv

.PHONY: install run lint format test build check

install:
	$(UV) sync --locked --dev

run:
	$(UV) run database

lint:
	$(UV) run ruff check .

format:
	$(UV) run ruff format .

test:
	$(UV) run python tests/run_tests.py

build:
	$(UV) build

check: lint test
