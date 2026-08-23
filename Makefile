# Development tasks for MASAFI Sim Petri.
#
# Uses the project virtualenv when one is present, so the targets work whether
# or not it is activated. Override with e.g. `make test PYTHON=python3.13`.

PYTHON        ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
DOCS_DIR      := docs
COVERAGE_DIR  := test/coverage_reports
PACKAGE       := masafi_sim_petri

.PHONY: help docs doctest test test-cov build clean

help:  ## Show this help
	@grep -E '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

docs:  ## Build the Sphinx documentation into docs/build/html
	$(MAKE) -C $(DOCS_DIR) html SPHINXBUILD="$(abspath $(PYTHON)) -m sphinx"

doctest:  ## Run the examples embedded in the documentation
	$(MAKE) -C $(DOCS_DIR) doctest SPHINXBUILD="$(abspath $(PYTHON)) -m sphinx"

test:  ## Run the test suite
	$(PYTHON) -m pytest

test-cov:  ## Run the test suite with coverage; HTML report in test/coverage_reports
	$(PYTHON) -m pytest \
		--cov=$(PACKAGE) \
		--cov-report=term-missing \
		--cov-report=html:$(COVERAGE_DIR)
	@echo "Coverage report: $(COVERAGE_DIR)/index.html"

build:  ## Build the source distribution and wheel into dist/
	$(PYTHON) -m build

clean:  ## Remove build, docs and coverage artefacts
	rm -rf dist build $(DOCS_DIR)/build $(DOCS_DIR)/source/api $(COVERAGE_DIR) .coverage
	find src test -name '__pycache__' -type d -exec rm -rf {} +
