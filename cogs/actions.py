from discord.ext import commands
import discord
from discord import app_commands 
from utils.calculations import calculations
class Actions(commands.Cog):
    """Gestion des actions du joueur (manger, boire, fumer...)."""

    def __init__(self, bot):
        self.bot = bot
        self.pending_effects = []

    @commands.command()
    async def manger(self, ctx):
        # Applique les effets de l'action
        # Note: L'appel à calculations.apply_action_effects ne passe pas l'état,
        # ce qui n'est pas idéal. Il faudrait passer l'état actuel du joueur.
        # Pour l'instant, on le laisse comme ça pour corriger les erreurs de chargement.
        effects = calculations.apply_action_effects({}, "manger")
        await ctx.send("🍽️ Le cuisinier a mangé et se sent mieux!")

    @commands.command()
    async def fumer(self, ctx, type_fumette: str):
        # fumer leger / lourd / dab
        effects = calculations.apply_action_effects({}, f"fumer_{type_fumette}")
        await ctx.send(f"💨 Le cuisinier a fumé ({type_fumette}) et réagit...")

async def setup(bot):
    await bot.add_cog(Actions(bot))