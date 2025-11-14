FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project metadata first (for Docker layer caching)
COPY pyproject.toml requirements.txt requirements-dev.txt ./

# Copy package and CLI
COPY msproject_validator ./msproject_validator
COPY validate.py ./

# Upgrade pip and install requirements (runtime + dev for convenience)
RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt || true
RUN pip install --no-cache-dir -r requirements-dev.txt || true

# Install the package
RUN pip install --no-cache-dir .

# Default entrypoint: run CLI; pass args like `<input> [output]`
ENTRYPOINT ["python", "validate.py"]
