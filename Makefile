.PHONY: help install install-dev test lint docker-build docker-build-prod docker-run build clean

VENV ?= .venv
PYTHON ?= python3
PIP ?= pip

help:
	@echo "Makefile targets:"
	@echo "  install         Install runtime requirements"
	@echo "  install-dev     Install development requirements (pydocstyle, pytest, pre-commit)"
	@echo "  test            Run unit tests"
	@echo "  lint            Run pydocstyle against package"
	@echo "  docker-build    Build the development Docker image (includes dev deps)"
	@echo "  docker-build-prod  Build the production Docker image (if Dockerfile.prod exists)"
	@echo "  docker-run      Run the container image (expects env var INPUT or pass args to docker)"
	@echo "  clean           Remove build artifacts"

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PIP) install -r requirements.txt || true

install-dev:
	$(PYTHON) -m pip install --upgrade pip
	$(PIP) install -r requirements-dev.txt || true

test:
	PYTHONPATH=. $(PYTHON) -m unittest discover -v tests

lint:
	# Prefer running pydocstyle from your venv. This will try to run system pydocstyle if available.
	$(PYTHON) -m pydocstyle msproject_validator || true

docker-build:
	docker build -t msproject-validator:latest .

docker-build-prod:
	@if [ -f Dockerfile.prod ]; then \
		docker build -f Dockerfile.prod -t msproject-validator:prod .; \
	else \
		echo "Dockerfile.prod not found — create a multi-stage Dockerfile named Dockerfile.prod for a smaller runtime image"; exit 1; \
	fi

docker-run:
	# Example: make docker-run INPUT=project.xml
	@if [ -z "$(INPUT)" ]; then \
		echo "Set INPUT=path/to/project.xml (and optional OUTPUT=path/to/out.xml). Example: make docker-run INPUT=project.xml"; exit 1; \
	fi
	-docker run --rm -v "$(PWD)":/data msproject-validator:latest /data/$(INPUT) $(OUTPUT)

build:
	# Build a wheel for local distribution
	$(PYTHON) -m pip wheel . -w dist || true

clean:
	rm -rf build dist *.egg-info .pytest_cache
