# --- bot.py (CORRECTED & ROBUST STRUCTURE) ---
import discord
from discord.ext import commands
import os
import asyncio
import traceback

# Charger la configuration
from config import BOT_TOKEN, GUILD_ID
# Charger le logger
from utils.logger import get_logger
# --- NOUVELLE LOGIQUE D'INITIALISATION DE LA BDD ---
# 1. Importer les objets de connexion et la Base depuis database.py
from db.database import engine, Base

# 2. IMPORTER EXPLICITEMENT TOUS LES MODÈLES
# C'est l'étape cruciale. Cela remplit Base.metadata avec vos tables.
from db.models import ServerState, PlayerProfile, ActionLog

logger = get_logger(__name__)
COGS_DIR = "cogs"

# 3. CRÉER LES TABLES
# Cette opération est synchrone et se fait au démarrage, AVANT toute connexion à Discord.
logger.info("--- Initializing Database Schema ---")
try:
    Base.metadata.create_all(bind=engine)
    logger.info("--- Database Schema Initialized/Checked ---")
except Exception as e:
    logger.critical(f"FATAL: Could not create database tables. Error: {e}")
    exit() # On ne continue pas si la BDD ne peut pas être créée
# --- FIN DE LA NOUVELLE LOGIQUE ---


class QuitAddictionBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        self.test_guild = discord.Object(id=GUILD_ID) if GUILD_ID else None

    async def on_ready(self):
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logger.info('------')
        
        # L'initialisation des assets se fait ici, après que le bot soit connecté et ait accès aux salons.
        asset_cog = self.get_cog("AssetManager")
        if asset_cog and hasattr(asset_cog, 'initialize_assets'):
            await asset_cog.initialize_assets()
        else:
            logger.warning("AssetManager cog not found after setup, cannot initialize assets.")

    async def setup_hook(self):
        # La DB est déjà initialisée, on charge juste les cogs.
        logger.info("--- Loading Cogs ---")
        for filename in os.listdir(f'./{COGS_DIR}'):
            if filename.endswith('.py') and not filename.startswith('__'):
                try:
                    await self.load_extension(f'{COGS_DIR}.{filename[:-3]}')
                    logger.info(f'✅ Cog loaded: {filename}')
                except commands.errors.NoEntryPointError:
                    # Gère les fichiers .py qui ne sont pas des cogs
                    pass
                except Exception as e:
                    logger.error(f'❌ Failed to load cog {filename}:')
                    traceback.print_exc() # Imprime le traceback complet pour le débogage
        
        logger.info("--- Syncing Commands ---")
        try:
            # Synchronisation des commandes slash
            await self.tree.sync()
            logger.info("✅ Global slash commands synced.")
        except Exception as e:
            logger.error(f"❌ Command sync failed: {e}", exc_info=True)


async def main():
    if not BOT_TOKEN:
        logger.critical("BOT_TOKEN is not set in the environment variables. The bot cannot start.")
        return
        
    bot = QuitAddictionBot()
    async with bot:
        await bot.start(BOT_TOKEN)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutting down by KeyboardInterrupt.")