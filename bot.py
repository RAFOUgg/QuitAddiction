import discord
from discord.ext import commands
import os
import asyncio
import logging

# Importe notre configuration
from config import BOT_TOKEN, GUILD_ID
from core.database import init_db # On importera la fonction pour initialiser la DB

# Configure le logging pour avoir des infos claires dans la console
logging.basicConfig(level=logging.INFO)

# Le dossier où se trouvent nos modules de commandes
COGS_DIR = "cogs"

class QuitAddictionBot(commands.Bot):
    def __init__(self):
        # Définit les "Intents", les permissions que notre bot demande à Discord
        intents = discord.Intents.default()
        intents.message_content = True  # Pour la commande /counting
        intents.members = True          # Pour savoir quand des membres rejoignent/partent

        # Initialise la classe parente 'Bot'
        super().__init__(command_prefix="!", intents=intents)
        
        # Un objet discord.Object pour notre serveur de test, s'il est défini
        self.test_guild = discord.Object(id=GUILD_ID) if GUILD_ID else None

    async def on_ready(self):
        """Événement appelé lorsque le bot est connecté et prêt."""
        logging.info(f'Connecté en tant que {self.user} (ID: {self.user.id})')
        logging.info('------')

    async def setup_hook(self):
        """
        Un crochet qui s'exécute avant que le bot ne soit complètement connecté.
        C'est l'endroit idéal pour charger les cogs, initialiser la DB, etc.
        """
        # Initialise la base de données et crée les tables si elles n'existent pas
        init_db()
        logging.info("Base de données initialisée.")

        # Charge tous les fichiers .py dans le dossier cogs/
        for filename in os.listdir(f'./{COGS_DIR}'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'{COGS_DIR}.{filename[:-3]}')
                    logging.info(f'✅ Cog chargé : {filename}')
                except Exception as e:
                    logging.error(f'❌ Erreur de chargement du cog {filename}: {type(e).__name__} - {e}')

        # Synchronise les commandes slash avec le serveur de test (plus rapide)
        # ou avec tous les serveurs si aucun serveur de test n'est défini
        if self.test_guild:
            self.tree.copy_global_to(guild=self.test_guild)
            await self.tree.sync(guild=self.test_guild)
            logging.info(f"Commandes synchronisées avec le serveur de test (ID: {GUILD_ID}).")
        else:
            await self.tree.sync()
            logging.info("Commandes synchronisées globalement.")


async def main():
    """Fonction principale pour lancer le bot."""
    bot = QuitAddictionBot()
    await bot.start(BOT_TOKEN)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Arrêt du bot.")