# Utilise une image Python légère
FROM python:3.12-slim

# --- AJOUTÉ : Installer les dépendances système (git) ---
# Met à jour la liste des paquets et installe git.
# --no-install-recommends réduit la taille de l'image finale.
# Les commandes de nettoyage sont une bonne pratique pour garder l'image petite.
RUN apt-get update && apt-get install -y git --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy only the requirements file first to leverage Docker's layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project files
# IMPORTANT : Ceci copie aussi le dossier .git, ce qui est nécessaire pour la commande
COPY . .

# Environment variable for the token (can be overridden by docker-compose)
ENV DISCORD_TOKEN=changeme

# The command to run the bot
CMD ["python", "bot.py"]