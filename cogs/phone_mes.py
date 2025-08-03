# cogs/phone_mes.py
from discord.ext import commands
import discord
# ... autres imports ...

class PhoneMessages(commands.Cog): # Nom de classe supposé
    def __init__(self, bot):
        self.bot = bot
        # ... votre logique ...

async def setup(bot):
    # Instancier la classe correcte
    await bot.add_cog(PhoneMessages(bot))