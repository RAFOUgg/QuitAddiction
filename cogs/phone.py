# --- cogs/phone.py ---
from discord.ext import commands
import discord
from db.database import SessionLocal
from db.models import ServerState # Importé pour accéder aux données si nécessaire

class Phone(commands.Cog):
    """Gestion du téléphone : quiz, messages et missions sociales."""
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def quiz(self, ctx):
        """
        Envoie une question éducative avec boutons pour interagir.
        """
        # Récupérer l'état du serveur si nécessaire pour personnaliser la question
        db = SessionLocal()
        state = db.query(ServerState).filter_by(guild_id=str(ctx.guild.id)).first()
        db.close()

        # Question exemple
        question = "Quel est le mode de consommation le moins nocif ?"
        
        # Création des options de réponse
        options = [
            discord.SelectOption(label="A) La consommation régulière et modérée", value="regular_moderate"),
            discord.SelectOption(label="B) L'abstinence totale", value="abstinence"),
            discord.SelectOption(label="C) La consommation occasionnelle et à faible dose", value="occasional_low_dose"),
            discord.SelectOption(label="D) Le 'binge drinking' (consommation excessive)", value="binge_drinking")
        ]

        # Création du message avec la question et un menu déroulant pour les réponses
        # Note: Pour utiliser des SelectOptions, il faut créer une classe Select personnalisée qui hérite de ui.Select.
        # Ici, on va rester sur un message simple pour l'instant, car la logique du Select n'est pas implémentée ici.
        await ctx.send(f"📱 Nouveau message : {question}")
        # Si vous voulez des boutons, vous devrez créer une classe `discord.ui.Button` et l'ajouter à une vue.

async def setup(bot):
    await bot.add_cog(Phone(bot))