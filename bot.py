# --- bot.py (Corrected) ---
import discord
from discord.ext import commands
import os
import asyncio

# --- Our custom modules ---
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

    async def setup_hook(self):
        logger.info("Initializing database from setup_hook...")
        init_db()
        logger.info("Database initialization check complete.")

        for filename in os.listdir(f'./{COGS_DIR}'):
            if filename.endswith('.py') and not filename.startswith('__'):
                try:
                    await self.load_extension(f'{COGS_DIR}.{filename[:-3]}')
                    logger.info(f'✅ Cog loaded: {filename}')
                except Exception as e:
                    logger.error(f'❌ Failed to load cog {filename}: {type(e).__name__} - {e}', exc_info=True)
        
        # --- BLOC CORRIGÉ POUR ÉVITER LES DOUBLONS ---
        if self.test_guild:
            # Mode Développement : synchronise instantanément sur le serveur de test UNIQUEMENT.
            logger.info(f"Syncing commands to test guild: {self.test_guild.id}")
            self.tree.copy_global_to(guild=self.test_guild)
            await self.tree.sync(guild=self.test_guild)
            logger.info("Commands synced to test guild.")
        else:
            # Mode Production : synchronise globalement pour tous les serveurs.
            # (Peut prendre jusqu'à une heure pour se propager)
            await self.tree.sync()
            logger.info("Global slash commands synced.")
        # --- FIN DU BLOC CORRIGÉ ---

async def main():
    bot = QuitAddictionBot()
    await bot.start(BOT_TOKEN)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutting down by KeyboardInterrupt.")