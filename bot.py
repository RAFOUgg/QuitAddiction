# --- bot.py (ROBUST SYNCING) ---
import discord
from discord.ext import commands
import os
import asyncio
import traceback

from config import BOT_TOKEN, GUILD_ID
from utils.logger import get_logger
from db.database import engine, Base
from db.models import ServerState, PlayerProfile, ActionLog

logger = get_logger(__name__)
COGS_DIR = "cogs"

# Création des tables (inchangé)
logger.info("--- Initializing Database Schema ---")
try:
    Base.metadata.create_all(bind=engine)
    logger.info("--- Database Schema Initialized/Checked ---")
except Exception as e:
    logger.critical(f"FATAL: Could not create database tables. Error: {e}")
    exit()

class QuitAddictionBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def on_ready(self):
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logger.info('------')
        
        asset_cog = self.get_cog("AssetManager")
        if asset_cog and hasattr(asset_cog, 'initialize_assets'):
            await asset_cog.initialize_assets()
        else:
            logger.warning("AssetManager cog not found after setup, cannot initialize assets.")

    async def setup_hook(self):
        logger.info("--- Loading Cogs ---")
        for filename in os.listdir(f'./{COGS_DIR}'):
            if filename.endswith('.py') and not filename.startswith('__'):
                try:
                    await self.load_extension(f'{COGS_DIR}.{filename[:-3]}')
                    logger.info(f'✅ Cog loaded: {filename}')
                except Exception as e:
                    logger.error(f'❌ Failed to load cog {filename}:')
                    traceback.print_exc()
        
        # --- AMÉLIORATION: Synchronisation propre et sécurisée ---
        logger.info("--- Syncing Commands ---")
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            # Copie toutes les commandes globales vers notre guilde de test
            self.tree.copy_global_to(guild=guild)
            # Synchronise uniquement pour cette guilde. C'est instantané.
            synced_commands = await self.tree.sync(guild=guild)
            logger.info(f"✅ Synced {len(synced_commands)} commands to test guild (ID: {GUILD_ID}).")
        else:
            # Comportement par défaut si aucun GUILD_ID n'est fourni
            synced_commands = await self.tree.sync()
            logger.info(f"✅ Synced {len(synced_commands)} global commands.")

# --- Le reste du fichier main() et __main__ est inchangé ---
async def main():
    if not BOT_TOKEN:
        logger.critical("BOT_TOKEN is not set in the environment variables.")
        return
        
    bot = QuitAddictionBot()
    async with bot:
        await bot.start(BOT_TOKEN)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutting down by KeyboardInterrupt.")