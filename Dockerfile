# Multi-stage build for optimized CLI version
FROM python:3.12-slim AS base

WORKDIR /app

# Install only what we need (no GUI dependencies)
# Copy only required files for CLI
COPY src/__init__.py /app/src/__init__.py
COPY src/core/__init__.py /app/src/core/__init__.py
COPY src/core/engine.py /app/src/core/engine.py
COPY src/cli/__init__.py /app/src/cli/__init__.py
COPY src/cli/cli_app.py /app/src/cli/cli_app.py
COPY assets/quotes.txt /app/assets/quotes.txt
COPY assets/words.txt /app/assets/words.txt
COPY config.json /app/config.json
COPY run_cli.py /app/run_cli.py

# Set environment variables for better Python performance
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Run the CLI app
CMD ["python", "-u", "run_cli.py"]
