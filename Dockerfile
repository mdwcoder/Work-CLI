FROM python:3.12-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir rich typer

# Copy source code
COPY src/ /app/src/

# Create data directories to ensure permissions
RUN mkdir -p /app/data /app/backup

# Set entrypoint
ENTRYPOINT ["python", "/app/src/Working_Code.py"]
