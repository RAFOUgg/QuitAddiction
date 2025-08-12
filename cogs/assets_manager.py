# --- cogs/asset_manager.py ---

import discord
from discord.ext import commands
import os
from utils.logger import get_logger # Assumant que vous avez un logger

logger = get_logger(__name__)

# Récupérez l'ID du salon depuis vos variables d'environnement
ASSET_CHANNEL_ID = int(os.getenv("ASSET_CHANNEL_ID", 0))

class AssetManager(commands.Cog):
    """
    Gère le chargement et la mise en cache des URLs des assets du bot
    en les téléchargeant dans un canal Discord dédié.
    """
    def __init__(self, bot):
        self.bot = bot
        self.asset_urls = {} # Dictionnaire pour stocker les URLs: {'happy': 'http://...', 'sad': 'http://...'}

    async def cog_load(self):
        """Cette fonction est appelée automatiquement lorsque le cog est chargé."""
        logger.info("AssetManager a été chargé. Lancement de la mise en cache des assets...")
        # On attend que le bot soit pleinement connecté pour pouvoir fetch le channel.
        await self.bot.wait_until_ready()
        await self.load_and_cache_assets()

    async def load_and_cache_assets(self):
        """Charge les images depuis le dossier local, les poste sur Discord si nécessaire, et met en cache leurs URLs."""
        if not ASSET_CHANNEL_ID:
            logger.error("ASSET_CHANNEL_ID n'est pas défini dans le fichier .env ! Le chargement des assets est annulé.")
            return

        try:
            asset_channel = await self.bot.fetch_channel(ASSET_CHANNEL_ID)
        except (discord.NotFound, discord.Forbidden):
            logger.error(f"Impossible de trouver ou d'accéder au salon d'assets (ID: {ASSET_CHANNEL_ID}). Vérifiez l'ID et les permissions du bot.")
            return

        asset_directory = "assets/cooker"
        if not os.path.isdir(asset_directory):
            logger.error(f"Le répertoire d'assets '{asset_directory}' n'a pas été trouvé.")
            return

        # 1. Parcourir les messages existants pour trouver les assets déjà uploadés
        existing_assets = {}
        async for message in asset_channel.history(limit=100):
            if message.attachments:
                for attachment in message.attachments:
                    # Stocker l'URL par nom de fichier (ex: 'happy.png')
                    if attachment.filename not in existing_assets:
                         existing_assets[attachment.filename] = attachment.url

        # 2. Parcourir les fichiers locaux et les uploader s'ils manquent
        for filename in os.listdir(asset_directory):
            if filename.endswith(".png"):
                asset_name = filename.split('.')[0] # 'happy.png' -> 'happy'

                if filename in existing_assets:
                    # L'asset existe déjà, on utilise son URL
                    self.asset_urls[asset_name] = existing_assets[filename]
                    logger.info(f"Asset trouvé dans le cache Discord : '{asset_name}'")
                else:
                    # L'asset n'existe pas, on l'upload
                    try:
                        filepath = os.path.join(asset_directory, filename)
                        file = discord.File(filepath, filename=filename)
                        message = await asset_channel.send(file=file)
                        if message.attachments:
                            self.asset_urls[asset_name] = message.attachments[0].url
                            logger.info(f"Asset uploadé et mis en cache : '{asset_name}'")
                    except Exception as e:
                        logger.error(f"Erreur lors de l'upload de l'asset '{filename}': {e}")
        
        logger.info("Mise en cache des assets terminée.")
        logger.info(f"URLs mises en cache : {self.asset_urls}")

    def get_url(self, asset_name: str) -> str | None:
        """Récupère l'URL d'un asset par son nom (ex: 'happy')."""
        return self.asset_urls.get(asset_name)

async def setup(bot):
    await bot.add_cog(AssetManager(bot))