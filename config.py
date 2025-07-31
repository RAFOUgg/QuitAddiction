# config.py
import os
from dotenv import load_dotenv

load_dotenv() # Charge les variables depuis un fichier .env

BOT_TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", 0)) # L'ID de votre serveur de test, optionnel