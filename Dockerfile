# --- STAGE 1: Le Builder ---
# On utilise une image python "slim" comme base, qui contient les outils pour installer des paquets.
FROM python:3.12-slim as builder

# Mettre à jour les paquets et installer 'git', qui est une dépendance système pour dev_stats_cog.py
# --no-install-recommends évite d'installer des paquets inutiles.
# Les commandes de nettoyage réduisent la taille de cette couche.
RUN apt-get update && apt-get install -y git --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Définir le répertoire de travail
WORKDIR /app

# Copier uniquement le fichier des dépendances pour profiter du cache Docker
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt


# --- STAGE 2: L'Image Finale ---
# On repart d'une image "slim" propre pour un résultat minimaliste.
FROM python:3.12-slim

# Créer un utilisateur non-root pour plus de sécurité
RUN useradd --create-home --shell /bin/bash appuser
USER appuser
WORKDIR /home/appuser/app

# Copier les paquets Python installés depuis l'étape "builder"
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# Copier l'exécutable 'git' installé depuis l'étape "builder"
COPY --from=builder /usr/bin/git /usr/bin/git

# Copier tout le code du projet
COPY . .

# La commande pour lancer le bot
CMD ["python", "bot.py"]