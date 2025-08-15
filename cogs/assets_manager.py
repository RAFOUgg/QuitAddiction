# --- cogs/asset_manager.py (CORRECTED) ---

import discord
from discord.ext import commands
import os
from utils.logger import get_logger

logger = get_logger(__name__)
ASSET_CHANNEL_ID = int(os.getenv("ASSET_CHANNEL_ID", 0))

class AssetManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.asset_urls = {}
        self.required_images = [
            'sporting.png',  # Pour l'activité sportive
            'smoke_bang.png',  # Pour l'utilisation du bong
            # ... autres images existantes
        ]

    # La méthode cog_load est supprimée car elle est la source du deadlock.
    # Nous la remplaçons par une méthode d'initialisation manuelle.

    async def initialize_assets(self):
        """Charge les images et met en cache leurs URLs. Doit être appelée après on_ready."""
        logger.info("Initializing and caching assets...")
        if not ASSET_CHANNEL_ID:
            logger.error("ASSET_CHANNEL_ID is not set in .env! Asset loading cancelled.")
            return

        try:
            asset_channel = await self.bot.fetch_channel(ASSET_CHANNEL_ID)
        except (discord.NotFound, discord.Forbidden):
            logger.error(f"Cannot find or access asset channel (ID: {ASSET_CHANNEL_ID}). Check ID and bot permissions.")
            return

        asset_directory = "assets/cooker"
        if not os.path.isdir(asset_directory):
            logger.error(f"Asset directory '{asset_directory}' not found.")
            return

        existing_assets = {msg.attachments[0].filename: msg.attachments[0].url async for msg in asset_channel.history(limit=100) if msg.attachments}

        for filename in os.listdir(asset_directory):
            if filename.endswith(".png"):
                asset_name = filename.split('.')[0]
                if filename in existing_assets:
                    self.asset_urls[asset_name] = existing_assets[filename]
                    logger.info(f"Found cached asset: '{asset_name}'")
                else:
                    try:
                        filepath = os.path.join(asset_directory, filename)
                        file = discord.File(filepath, filename=filename)
                        message = await asset_channel.send(file=file)
                        if message.attachments:
                            self.asset_urls[asset_name] = message.attachments[0].url
                            logger.info(f"Uploaded and cached asset: '{asset_name}'")
                    except Exception as e:
                        logger.error(f"Failed to upload asset '{filename}': {e}")
        
        logger.info("Asset caching finished.")
        logger.info(f"Cached URLs: {self.asset_urls}")

    def get_url(self, asset_name: str) -> str | None:
        return self.asset_urls.get(asset_name)

async def setup(bot):
    cog = AssetManager(bot)
    await bot.add_cog(cog)

    # Schedule initialization once the bot is fully ready to avoid deadlocks.
    async def _init_assets_when_ready():
        await bot.wait_until_ready()
        try:
            await cog.initialize_assets()
        except Exception as e:
            logger.error(f"Asset initialization failed: {e}")

    try:
        bot.loop.create_task(_init_assets_when_ready())
    except Exception:
        # If scheduling fails, ignore; initialization can be triggered manually.
        pass