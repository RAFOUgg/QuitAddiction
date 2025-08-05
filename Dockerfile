# Utilise une image Python légère
FROM python:3.12-slim

WORKDIR /app

# Copier tous les fichiers du projet
COPY . .

# Installer les dépendances Python nécessaires
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir discord.py sqlalchemy python-dotenv

# Variable d'environnement (si jamais .env absent)
ENV DISCORD_TOKEN=changeme

# Lancer le bot
CMD ["python", "bot.py"]
