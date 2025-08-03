# cogs/cooker_brain.py
from discord.ext import commands
# ... autres imports ...

class CookerBrain(commands.Cog): # La classe doit s'appeler CookerBrain
    def __init__(self, bot):
        self.bot = bot
        # ... votre logique ...

async def setup(bot):
    # Instancier la classe correcte
    await bot.add_cog(CookerBrain(bot))