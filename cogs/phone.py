# --- cogs/phone.py ---
from discord.ext import commands
import discord

class Phone(commands.Cog):
    """Gestion du téléphone : quiz, messages et missions sociales."""
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def quiz(self, ctx):
        # Envoie une question éducative avec boutons
        await ctx.send("📱 Nouveau message : Quel est le mode de consommation le moins nocif ?")

async def setup(bot):
    await bot.add_cog(Phone(bot))