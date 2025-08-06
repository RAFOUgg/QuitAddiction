# --- Fichier : config.py (ou utils/embed_builder.py) ---

import discord
import os
import dotenv

# Charger les variables d'environnement
dotenv.load_dotenv()

# --- Configurations Générales ---
# Définissez ici les constantes globales si elles ne sont pas déjà là.
# Par exemple :
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO_OWNER = os.getenv("GITHUB_REPO_OWNER")
GITHUB_REPO_NAME = os.getenv("GITHUB_REPO_NAME")

BOT_PREFIX = os.getenv("BOT_PREFIX", "!") # Préfixe par défaut
BOT_TOKEN = os.getenv("BOT_TOKEN")

# --- Utilitaires Divers ---

def create_styled_embed(title: str, description: str, color: discord.Color) -> discord.Embed:
    """
    Crée un embed Discord avec un style cohérent.
    """
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    # Vous pouvez ajouter ici des logos, des pieds de page, etc. pour plus de style.
    # Par exemple, un pied de page avec le nom du bot ou une date.
    # embed.set_footer(text=f"Bot V1.0")
    return embed

# --- Logger (si vous en avez un configuré ici) ---
# Si votre logger est global, assurez-vous qu'il est disponible.
# Exemple basique si vous n'avez pas de logger avancé :
class Logger:
    @staticmethod
    def info(message: str):
        print(f"INFO: {message}")
    @staticmethod
    def error(message: str):
        print(f"ERROR: {message}")
    @staticmethod
    def warning(message: str):
        print(f"WARNING: {message}")