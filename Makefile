# ---------------------------------
# Repo-specific variables
# ---------------------------------

# Define these variables for consistency in the repo
REPO_NAME ?= filter-event-sink
REPO_NAME_SNAKECASE ?= filter_event_sink
REPO_NAME_PASCALCASE ?= FilterEventSink

# Unique pipeline configuration for this repo
# Note: Event Sink requires API configuration via environment variables:
# - FILTER_API_ENDPOINT (required)
# - FILTER_API_TOKEN (required)
# - FILTER_API_CUSTOM_HEADERS (optional, for X-Scope-OrgID, etc.)
#
# Usage: source .env && make run
# The variables are read from the shell environment and passed as command-line args.
PIPELINE := \
	- VideoIn \
		--sources 'file://data/sample-video.mp4!loop' \
		--outputs 'tcp://*:5550' \
	- $(REPO_NAME_SNAKECASE).filter.$(REPO_NAME_PASCALCASE) \
		--sources 'tcp://localhost:5550??;>VideoIn' \
		--mq_log pretty \
		--api_endpoint '$(FILTER_API_ENDPOINT)' \
		--api_token '$(FILTER_API_TOKEN)' \
		$(if $(FILTER_API_CUSTOM_HEADERS),--api_custom_headers '$(FILTER_API_CUSTOM_HEADERS)') \
	- Webvis \
		--sources 'tcp://localhost:5550' \
		--port 8001

IMAGE ?= containers.openfilter.io/plainsightai/openfilter-event-sink
PYPI_REPO ?= https://python.openfilter.io/simple/
VERSION ?= $(shell cat VERSION)
CONTAINER_EXEC := docker

check-tag = !(git rev-parse -q --verify "refs/tags/v${VERSION}" > /dev/null 2>&1) || \
	(echo "the version: ${VERSION} has been released already" && exit 1)

# ---------------------------------
# Repo-specific targets
# ---------------------------------

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install:  ## Install package with dev dependencies
	pip install -e .[dev] \
		--index-url https://python.openfilter.io/simple \
		--extra-index-url https://pypi.org/simple

.PHONY: run
run:  ## Run locally with supporting Filters in other processes
	openfilter run ${PIPELINE}

.PHONY: test
test:  ## Run unit tests
	pytest -vv -s tests/ --junitxml=results/pytest-results.xml

.PHONY: test-coverage
test-coverage:  ## Run unit tests and generate coverage report
	@mkdir -p Reports
	@pytest -vv --cov=tests --junitxml=Reports/coverage.xml --cov-report=json:Reports/coverage.json -s tests/
	@jq -r '["File Name", "Statements", "Missing", "Coverage%"], (.files | to_entries[] | [.key, .value.summary.num_statements, .value.summary.missing_lines, .value.summary.percent_covered_display]) | @csv'  Reports/coverage.json >  Reports/coverage_report.csv
	@jq -r '["TOTAL", (.totals.num_statements // 0), (.totals.missing_lines // 0), (.totals.percent_covered_display // "0")] | @csv'  Reports/coverage.json >>  Reports/coverage_report.csv

.PHONY: build-wheel
build-wheel:  ## Build python wheel
	python -m pip install setuptools build wheel twine setuptools-scm --index-url https://pypi.org/simple
	python -m build --wheel

.PHONY: clean
clean:  ## Delete all generated files and directories
	sudo rm -rf build/ cache/ dist/ $(REPO_NAME_SNAKECASE).egg-info/ telemetry/
	find . -name __pycache__ -type d -exec rm -rf {} +

.PHONY: lint
lint:  ## Run code linting
	@echo "Running flake8..."
	flake8 filter_event_sink/ tests/

.PHONY: format
format:  ## Format code using black and isort
	@echo "Formatting code with black..."
	black filter_event_sink/ tests/
	@echo "Sorting imports with isort..."
	isort filter_event_sink/ tests/

.PHONY: format.check
format.check:  ## Check code formatting
	@echo "Checking code formatting with black..."
	black --check filter_event_sink/ tests/
	@echo "Checking imports with isort..."
	isort --check-only filter_event_sink/ tests/

.PHONY: check-version
check-version:  ## Check if VERSION has already been released/tagged
	@$(check-tag)

.PHONY: publish
publish:  ## Tag with VERSION and git push
	@$(check-tag)
	git tag v${VERSION}
	git push origin v${VERSION}

.PHONY: publish-wheel
publish-wheel: build-wheel  ## Publish python wheel
	TWINE_USERNAME=${PYPI_USERNAME} TWINE_PASSWORD=${PYPI_API_KEY} twine upload --repository-url ${PYPI_REPO} dist/*

.PHONY: build-image
build-image:  ## Build docker image
	${CONTAINER_EXEC} build \
		-t ${IMAGE}:${VERSION} \
		--platform linux/amd64,linux/arm64 \
		.

.PHONY: publish-image
publish-image:  ## Publish docker image
	${CONTAINER_EXEC} push ${IMAGE}:${VERSION}

.PHONY: run-image
run-image:  ## Run image in docker container
	${CONTAINER_EXEC} compose up
