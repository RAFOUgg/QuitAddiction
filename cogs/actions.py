# --- cogs/actions.py ---
from discord.ext import commands
import discord
from utils import calculations

class Actions(commands.Cog):
    """Gestion des actions du joueur (manger, boire, fumer...)."""

    def __init__(self, bot):
        self.bot = bot
        self.pending_effects = []

    @commands.command()
    async def manger(self, ctx):
        # Applique les effets de l'action
        effects = calculations.apply_action_effects({}, "manger")
        await ctx.send("🍽️ Le cuisinier a mangé et se sent mieux!")

    @commands.command()
    async def fumer(self, ctx, type_fumette: str):
        # fumer leger / lourd / dab
        effects = calculations.apply_action_effects({}, f"fumer_{type_fumette}")
        await ctx.send(f"💨 Le cuisinier a fumé ({type_fumette}) et réagit...")

async def setup(bot):
    await bot.add_cog(Actions(bot))
