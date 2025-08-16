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
        for filename in os.listdir(COGS_DIR):
            if filename.endswith(".py") and not filename.startswith("__"):
                try:
                    await self.load_extension(f"{COGS_DIR}.{filename[:-3]}")
                    logger.info(f"✅ Cog loaded: {filename}")
                except Exception as e:
                    logger.error(f"❌ Failed to load cog {filename}: {e}", exc_info=True)
        
        self.asset_manager = self.get_cog("AssetManager")

    async def on_ready(self):
        logger.info(f"🚀 Logged in as {self.user} (ID: {self.user.id})")
        logger.info("--------------------------------------------------")

        if not self._synced:
            logger.info("--- First Time Ready: Syncing commands ---")
            
            try:
                target_guild = discord.Object(id=DEV_GUILD_ID) if DEV_GUILD_ID else None
                if target_guild:
                    logger.info(f"Syncing commands to DEVELOPMENT guild (ID: {DEV_GUILD_ID})...")
                else:
                    logger.info("Syncing GLOBAL commands...")

                synced = await self.tree.sync(guild=target_guild)
                logger.info(f"✅ Synced {len(synced)} commands.")
            except Exception as e:
                logger.error(f"❌ Failed to sync commands: {e}", exc_info=True)

            self._synced = True
            logger.info("--- Bot is fully operational ---")
        else:
            logger.info("--- Bot reconnected, skipping sync. ---")


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