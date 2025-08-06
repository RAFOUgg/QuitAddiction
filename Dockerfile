# Use a lightweight Python image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy only the requirements file first to leverage Docker's layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project files
COPY . .

# Environment variable for the token (can be overridden by docker-compose)
ENV DISCORD_TOKEN=changeme

# The command to run the bot
CMD ["python", "bot.py"]