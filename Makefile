.DEFAULT_GOAL := help
.PHONY: help test-unit test-smoke test-integration test-browser test-pg test-pg-contract test-a1-gate test-focused check-selection test-gate lint format hooks

REPO_ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
PYTHON_BIN ?= $(REPO_ROOT)/venv/bin/python
# These entrypoints select sequential runs, independent of inherited pytest flags.
PYTEST = env -u DJANGO_SETTINGS_MODULE PYTEST_ADDOPTS= "$(PYTHON_BIN)" -m pytest
# These two Django targets explicitly exercise synthetic SQLite. PostgreSQL
# requires separate provisioning/ownership evidence and is never selected here.
SQLITE_ENV = env -u DOCUMENT_TEST_PG_SOCKET -u DOCUMENT_TEST_PG_NAME \
	-u DOCUMENT_TEST_PG_USER -u DOCUMENT_TEST_PG_HOST \
	-u DOCUMENT_TEST_PG_PORT -u DOCUMENT_TEST_PG_PASSWORD

help:
	@printf '%s\n' \
		'test-focused / test-unit: bounded reliability contract checks' \
		'test-smoke: boot/readiness helper checks' \
		'test-integration: synthetic SQLite document-service integration' \
		'test-browser: synthetic SQLite Chromium journey' \
		'test-pg-contract: PostgreSQL target/guard contracts only' \
		'test-pg: Chromium integration on a newly owned local PostgreSQL cluster' \
		'test-a1-gate: optional A1 quality-gate regressions' \
		'check-selection / test-gate: dependency consistency and staged check selection only' \
		'lint / format / hooks: explicit developer maintenance commands'

test-unit: test-focused

test-smoke:
	$(PYTEST) -q \
		tests/test_wsgi_asgi.py \
		tests/test_playwright_smoke.py \
		tests/test_check_readiness.py

test-integration:
	@printf '%s\n' 'Synthetic SQLite integration; PostgreSQL and restart acceptance are separate.'
	$(SQLITE_ENV) DJANGO_SETTINGS_MODULE=portal.settings_document_tests \
		"$(PYTHON_BIN)" manage.py test \
		tests.document_web.test_inbox \
		tests.document_web.test_field_review \
		tests.document_web.test_identity_review --noinput --verbosity 1

test-browser:
	@printf '%s\n' 'Synthetic SQLite browser journey; PostgreSQL and restart acceptance are separate.'
	$(SQLITE_ENV) DJANGO_SETTINGS_MODULE=portal.settings_browser_tests \
		"$(PYTHON_BIN)" manage.py test tests.document_web.test_browser_journey \
		--noinput --verbosity 1

test-pg:
	@printf '%s\n' 'Owned local PostgreSQL browser integration; deployed-target and restart acceptance are separate.'
	"$(PYTHON_BIN)" scripts/test_document_intake.py \
		--settings portal.settings_browser_tests tests.document_web.test_browser_journey

test-pg-contract:
	$(PYTEST) -q \
		tests/test_test_pg_contract.py \
		tests/test_disposable_pg_guard.py

test-a1-gate:
	$(PYTEST) -q tests/test_a1_quality_gate.py

test-focused:
	$(PYTEST) -q \
		tests/test_automation_entrypoints.py \
		tests/test_document_intake_runner.py \
		tests/test_no_networkidle_regression.py \
		tests/test_disposable_pg_guard.py \
		tests/test_test_pg_contract.py \
		tests/test_release_reproducer.py \
		tests/test_persistence_verifier.py

check-selection:
	@printf '%s\n' 'Dependency consistency and check selection only; selected checks are not executed by this target.'
	"$(PYTHON_BIN)" -m pip check
	"$(PYTHON_BIN)" scripts/validate_change_packages.py --staged --json

test-gate: check-selection

lint:
	"$(PYTHON_BIN)" -m ruff check scripts/ tests/ portal/

format:
	"$(PYTHON_BIN)" -m ruff format scripts/ tests/ portal/

hooks:
	"$(REPO_ROOT)/scripts/install-git-hooks.sh"
