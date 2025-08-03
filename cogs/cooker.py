# cogs/cooker.py
from discord.ext import commands
# ... autres imports ...

class Cooker(commands.Cog): # La classe doit être définie ici
    def __init__(self, bot):
        self.bot = bot
        # ... votre logique ...

async def setup(bot):
    await bot.add_cog(Cooker(bot)) # Assurez-vous que le nom de la classe est correct