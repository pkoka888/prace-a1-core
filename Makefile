.PHONY: help test-unit test-smoke test-integration test-browser test-pg test-a1-gate test-focused test-gate test-all lint format hooks

REPO_ROOT := $(shell git rev-parse --show-toplevel)
VENV := $(REPO_ROOT)/venv/bin/python
PYTEST := $(VENV) -m pytest

help:
	@just --list 2>/dev/null || grep -E '^[a-z-]+:' Makefile | sed 's/://' | sort

test-unit:
	$(PYTEST) -q \
		--ignore=tests/m2 \
		--ignore=tests/architecture \
		--ignore=tests/document_web/test_browser_journey.py \
		--ignore=tests/test_rehearse_synthetic_site_lifecycle.py \
		--deselect=tests/test_rehearse_workflow.py \
		--deselect=tests/test_rehearse_synthetic_site.py

test-smoke:
	$(PYTEST) -q \
		tests/test_wsgi_asgi.py \
		tests/test_playwright_smoke.py \
		tests/test_check_readiness.py

test-integration:
	$(PYTEST) -q \
		tests/test_rehearse_synthetic_site_lifecycle.py \
		tests/document_web/test_browser_journey.py \
		tests/test_rehearse_workflow.py

test-browser:
	DJANGO_SETTINGS_MODULE=portal.settings_browser_tests $(PYTEST) -q \
		tests/document_web/test_browser_journey.py

test-pg:
	$(PYTEST) -q \
		tests/test_test_pg_contract.py \
		tests/test_disposable_pg_guard.py \
		tests/test_rehearse_workflow.py \
		--ignore=tests/m2/test_release1a_vertical.py

test-a1-gate:
	$(PYTEST) -q tests/test_a1_quality_gate.py

test-focused:
	$(PYTEST) -q -o "addopts=" \
		tests/test_no_networkidle_regression.py \
		tests/test_disposable_pg_guard.py \
		tests/test_test_pg_contract.py \
		tests/test_release_reproducer.py \
		tests/test_persistence_verifier.py

test-gate:
	$(VENV) -m pip check
	$(VENV) scripts/validate_change_packages.py --staged --json

test-all: test-unit test-smoke test-gate
	@echo "All checks passed"

lint:
	$(VENV) -m ruff check scripts/ tests/ portal/

format:
	$(VENV) -m ruff format scripts/ tests/ portal/

hooks:
	$(REPO_ROOT)/scripts/install-git-hooks.sh
