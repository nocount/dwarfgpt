# Makefile for the dwarfgpt project.
#
# Most targets shell out to `uv run` so they work in a fresh checkout without
# needing a manually-activated venv.

.PHONY: help install test score extract clean

help:
	@echo "Targets:"
	@echo "  install      uv sync --extra dev (creates .venv, installs all deps)"
	@echo "  test         run the khuzdul_translator unit + smoke tests"
	@echo "  score        score khuzdul_translator against the gold set (requires verified entries)"
	@echo "  extract      regenerate data/*.json from the .xlsm (slow, ~3 minutes)"
	@echo "  clean        remove caches and the .venv"

install:
	uv sync

test:
	uv run pytest khuzdul_translator/tests/ -v

score:
	uv run python scripts/score_gold_set.py

extract:
	uv run python scripts/extract_tables.py

clean:
	rm -rf .venv .pytest_cache __pycache__ khuzdul_translator/__pycache__
