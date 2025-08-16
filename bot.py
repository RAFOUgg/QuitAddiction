# --- bot.py (DEFINITIVE & STABLE VERSION) ---

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

class QuitAddictionBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._synced = False
        self.asset_manager = None

    async def setup_hook(self):
        logger.info("--- Loading Cogs ---")
        
        # Load AssetManager first
        try:
            await self.load_extension("cogs.assets_manager")
            logger.info("✅ Cog loaded: assets_manager.py")
            self.asset_manager = self.get_cog("AssetManager")
        except Exception as e:
            logger.error(f"❌ Failed to load AssetManager cog: {e}", exc_info=True)
            return  # Exit if AssetManager fails to load as it's critical
            
        # Then load other cogs
        for filename in os.listdir(COGS_DIR):
            if filename.endswith(".py") and not filename.startswith("__") and filename != "assets_manager.py":
                try:
                    await self.load_extension(f"{COGS_DIR}.{filename[:-3]}")
                    logger.info(f"✅ Cog loaded: {filename}")
                except Exception as e:
                    logger.error(f"❌ Failed to load cog {filename}: {e}", exc_info=True)

    async def on_ready(self):
        logger.info(f"🚀 Logged in as {self.user} (ID: {self.user.id})")
        logger.info("--------------------------------------------------")

        # Force sync commands every time in development
        if DEV_GUILD_ID:
            logger.info("--- Syncing commands (Development Mode) ---")
            try:
                target_guild = discord.Object(id=int(DEV_GUILD_ID))
                # Clear existing commands first
                self.tree.clear_commands(guild=target_guild)
                # Sync new commands
                synced = await self.tree.sync(guild=target_guild)
                logger.info(f"✅ Synced {len(synced)} commands to development guild.")
            except Exception as e:
                logger.error(f"❌ Failed to sync commands: {e}", exc_info=True)
        # In production, only sync once
        elif not self._synced:
            logger.info("--- First Time Ready: Syncing global commands ---")
            try:
                synced = await self.tree.sync()
                logger.info(f"✅ Synced {len(synced)} commands globally.")
                self._synced = True
            except Exception as e:
                logger.error(f"❌ Failed to sync commands: {e}", exc_info=True)

        logger.info("--- Bot is fully operational ---")


def init_db():
    logger.info("--- Initializing Database Schema ---")
    Base.metadata.create_all(bind=engine)
    logger.info("--- Database Schema Initialized/Checked ---")

if __name__ == '__main__':
    init_db()
    bot = QuitAddictionBot(command_prefix="!", intents=intents)
    
    async def main():
        if not TOKEN:
            logger.critical("BOT_TOKEN is not set in the environment variables.")
            return
        async with bot:
            await bot.start(TOKEN)

    asyncio.run(main())