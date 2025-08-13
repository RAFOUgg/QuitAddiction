# --- bot.py (CORRECTED STRUCTURE) ---
import discord
from discord.ext import commands
import os
import asyncio

from config import BOT_TOKEN, GUILD_ID
from db.database import init_db
from utils.logger import get_logger

logger = get_logger(__name__)
COGS_DIR = "cogs"

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
        
        asset_cog = self.get_cog("AssetManager")
        if asset_cog:
            await asset_cog.initialize_assets()
        else:
            logger.warning("AssetManager cog not found after setup, cannot initialize assets.")

    async def setup_hook(self):
        # --- MODIFICATION CLÉ ---
        # 1. Initialiser la DB en premier. Si ça échoue ici, le bot ne démarrera pas, ce qui est bien.
        logger.info("--- Initializing Database ---")
        try:
            init_db()
            logger.info("✅ Database initialization check complete.")
        except Exception as e:
            logger.critical(f"❌ CRITICAL: FAILED TO INITIALIZE DATABASE. SHUTTING DOWN. Error: {e}", exc_info=True)
            await self.close() # Empêche le bot de démarrer sans DB
            return

        # 2. Charger les cogs APRÈS l'initialisation de la DB.
        logger.info("--- Loading Cogs ---")
        for filename in os.listdir(f'./{COGS_DIR}'):
            # J'exclus les fichiers non-cogs pour être propre
            if filename.endswith('.py') and not filename.startswith('__'):
                try:
                    await self.load_extension(f'{COGS_DIR}.{filename[:-3]}')
                    logger.info(f'✅ Cog loaded: {filename}')
                except commands.errors.NoEntryPointError:
                    logger.warning(f"⚠️  Skipping {filename}: Not a valid cog (missing setup function).")
                except Exception as e:
                    logger.error(f'❌ Failed to load cog {filename}: {type(e).__name__} - {e}', exc_info=True)
        
        # 3. Synchroniser les commandes
        logger.info("--- Syncing Commands ---")
        try:
            if self.test_guild:
                logger.info(f"Syncing commands to test guild: {self.test_guild.id}")
                self.tree.copy_global_to(guild=self.test_guild)
                await self.tree.sync(guild=self.test_guild)
                logger.info("✅ Commands synced to test guild.")
            else:
                await self.tree.sync()
                logger.info("✅ Global slash commands synced.")
        except Exception as e:
            logger.error(f"❌ Command sync failed: {e}", exc_info=True)

async def main():
    bot = QuitAddictionBot()
    await bot.start(BOT_TOKEN)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutting down by KeyboardInterrupt.")