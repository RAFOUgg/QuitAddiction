# bot.py
import discord
from discord.ext import commands
import os
import asyncio
import logging

# Importe notre configuration
from config import BOT_TOKEN, GUILD_ID
from db.database import init_db # On importera la fonction pour initialiser la DB

# Configure le logging pour avoir des infos claires dans la console
logging.basicConfig(level=logging.INFO)

# Le dossier où se trouvent nos modules de commandes
COGS_DIR = "cogs"

class QuitAddictionBot(commands.Bot):
    def __init__(self):
        # ... (vos intents et initialisation) ...
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True # Ajout pour certains événements si nécessaire

        super().__init__(command_prefix="!", intents=intents)
        self.test_guild = discord.Object(id=GUILD_ID) if GUILD_ID else None

    async def on_ready(self):
        logging.info(f'Connecté en tant que {self.user} (ID: {self.user.id})')
        logging.info('------')

    async def setup_hook(self):
        """
        Un crochet qui s'exécute avant que le bot ne soit complètement connecté.
        C'est l'endroit idéal pour charger les cogs, initialiser la DB, etc.
        """
        # >>> FAIT : Ceci est l'endroit idéal pour appeler init_db() <<<
        init_db()
        logging.info("Base de données initialisée.")

        # ... (chargement des cogs et synchronisation des commandes) ...
        for filename in os.listdir(f'./{COGS_DIR}'):
            if filename.endswith('.py') and filename != '__init__.py':
                try:
                    # S'assure que le fichier existe et est accessible avant de charger l'extension
                    if os.path.exists(os.path.join(f'./{COGS_DIR}', filename)):
                        await self.load_extension(f'{COGS_DIR}.{filename[:-3]}')
                        logging.info(f'✅ Cog chargé : {filename}')
                    else:
                        logging.warning(f"Fichier cog non trouvé : {filename}")
                except Exception as e:
                    logging.error(f'❌ Erreur de chargement du cog {filename}: {type(e).__name__} - {e}')
        # Et surtout :
        if self.test_guild:
            self.tree.copy_global_to(guild=self.test_guild) # Important pour TEST RAPIDE
            await self.tree.sync(guild=self.test_guild)
        else:
            await self.tree.sync() # Sync global (plus lent)

async def main():
    bot = QuitAddictionBot()
    await bot.start(BOT_TOKEN)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Arrêt du bot.")