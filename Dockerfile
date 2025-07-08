# Use an official Python runtime as a parent image (slim version for smaller size)
FROM python:3.11-slim-bullseye

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies that might be needed by some Python packages (e.g., psycopg2)
# For psycopg2, libpq-dev is needed. For Pillow (image processing), other libs might be needed.
# Keep this minimal.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    # Add other build-time dependencies here if necessary (e.g., gcc for C extensions)
    # build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
# Using --no-cache-dir to reduce image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Application specific environment variables
# FLASK_APP is set to run.py which should contain `app = create_app()`
ENV FLASK_APP=run.py
ENV FLASK_ENV=production
# PORT will be set by Render. Gunicorn will bind to this.
# Defaulting to 10000 if PORT is not set, common for Render.

# Gunicorn settings (can also be in a gunicorn_config.py)
# Example: CMD ["gunicorn", "-c", "gunicorn_config.py", "run:app"]
# For Render, the start command in render.yaml is usually preferred.
# This CMD is a fallback or for direct Docker runs.
# The 'app' object in 'run:app' is expected to be the Flask app instance.
# In run.py: from app import create_app; app = create_app()
CMD ["gunicorn", "--bind", "0.0.0.0:${PORT:-10000}", "--workers", "2", "--threads", "4", "--worker-class", "gthread", "run:app"]

# Note: No EXPOSE needed as Render handles port mapping based on its service configuration.
# Note: Running as non-root user is good practice but omitted here for simplicity.
#       If added, ensure file permissions and UPLOAD_FOLDER are handled.
