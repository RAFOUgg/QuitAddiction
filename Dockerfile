# --- STAGE 1: The Builder ---
FROM python:3.12-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y git --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- STAGE 2: The Final Image ---
FROM python:3.12-slim

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash appuser
# We will switch to this user later

WORKDIR /home/appuser/app

# Copy installed packages and binaries from the builder stage
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/bin/git /usr/bin/git

# Copy all project code
COPY . .

# --- THIS IS THE FIX ---
# Change the ownership of all files in the app directory to our new user.
# This ensures that 'appuser' can write to the 'logs' and 'db' subdirectories.
RUN chown -R appuser:appuser /home/appuser/app

# Now, switch to the non-root user
USER appuser

# The command to run the bot
CMD ["python", "bot.py"]