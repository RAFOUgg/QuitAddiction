# --- bot.py (CORRECTED & ROBUST) ---

import discord
from discord.ext import commands
import os
import asyncio
import traceback
from dotenv import load_dotenv

from utils.logger import get_logger
from db.database import Base, engine

# --- Setup ---
load_dotenv()
logger = get_logger(__name__)
TOKEN = os.getenv("DISCORD_TOKEN")
# Optionnel: Pour un développement plus rapide, mettez l'ID de votre serveur de test dans le .env
# En production, laissez cette variable vide.
DEV_GUILD_ID = os.getenv("DEV_GUILD_ID", None) 
COGS_DIR = "cogs"

# --- Define Intents ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

# --- Custom Bot Class ---
class QuitAddictionBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ce flag nous assurera que les opérations lourdes ne se font qu'une seule fois.
        self._synced = False
        self.asset_manager = None # On stocke une référence pour y accéder facilement

    async def setup_hook(self):
        """
        Le setup_hook est appelé une seule fois lors de la connexion initiale.
        C'est l'endroit idéal pour charger les cogs.
        """
        logger.info("--- Loading Cogs ---")
        for filename in os.listdir(COGS_DIR):
            if filename.endswith(".py") and not filename.startswith("__"):
                try:
                    await self.load_extension(f"{COGS_DIR}.{filename[:-3]}")
                    logger.info(f"✅ Cog loaded: {filename}")
                except Exception as e:
                    logger.error(f"❌ Failed to load cog {filename}: {e}", exc_info=True)
        
        # Récupère le cog après chargement
        self.asset_manager = self.get_cog("AssetManager")

    async def on_ready(self):
        """
        Cet événement est appelé à chaque connexion/reconnexion.
        Nous utilisons notre flag `_synced` pour n'exécuter les opérations lourdes qu'une fois.
        """
        logger.info(f"🚀 Logged in as {self.user} (ID: {self.user.id})")
        logger.info("--------------------------------------------------")

        if not self._synced:
            logger.info("--- First Time Ready: Syncing commands and initializing assets ---")
            
            # Synchronise les commandes slash avec Discord.
            try:
                if DEV_GUILD_ID:
                    # Si on est en mode dev, on synchronise seulement sur notre serveur. C'est instantané.
                    guild = discord.Object(id=DEV_GUILD_ID)
                    self.tree.copy_global_to(guild=guild)
                    synced = await self.tree.sync(guild=guild)
                    logger.info(f"✅ Synced {len(synced)} commands to DEVELOPMENT guild (ID: {DEV_GUILD_ID}).")
                else:
                    # En production, on synchronise globalement. Peut prendre jusqu'à 1 heure pour se propager.
                    synced = await self.tree.sync()
                    logger.info(f"✅ Synced {len(synced)} GLOBAL commands.")
            except Exception as e:
                logger.error(f"❌ Failed to sync commands: {e}", exc_info=True)

            # Initialise les assets (images)
            if self.asset_manager:
                try:
                    await self.asset_manager.initialize_assets()
                    logger.info("✅ Asset Manager initialized.")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize AssetManager: {e}", exc_info=True)

            self._synced = True
            logger.info("--- Bot is fully operational ---")
        else:
            logger.info("--- Bot reconnected, skipping sync and init. ---")


def init_db():
    """Initialise le schéma de la base de données."""
    logger.info("--- Initializing Database Schema ---")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("--- Database Schema Initialized/Checked ---")
    except Exception as e:
        logger.critical(f"FATAL: Could not create database tables. Error: {e}", exc_info=True)
        exit()

# --- Point d'Entrée ---
if __name__ == '__main__':
    init_db()

    bot = QuitAddictionBot(command_prefix="!", intents=intents)
    
    async def main():
        if not TOKEN:
            logger.critical("BOT_TOKEN is not set in the environment variables.")
            return
        async with bot:
            await bot.start(TOKEN)

    try:
        asyncio.run(main())
    except Exception as e:
        logger.critical(f"Bot failed to start: {e}", exc_info=True)