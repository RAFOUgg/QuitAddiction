# --- cogs/phone.py ---
import discord
from discord.ext import commands
from discord import ui

# La vue (les boutons) est définie ici pour être importée par main_embed.py
class PhoneMainView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        # custom_id doit être unique pour que le listener du Cog "Phone" puisse le traiter
        self.add_item(ui.Button(label="💬 SMS", style=discord.ButtonStyle.green, custom_id="phone_sms"))
        self.add_item(ui.Button(label="🛍️ Smoke-Shop", style=discord.ButtonStyle.blurple, custom_id="phone_shop"))
        # Le bouton de retour est géré par le listener principal dans main_embed.py
        self.add_item(ui.Button(label="⬅️ Retour", style=discord.ButtonStyle.grey, custom_id="nav_main_menu"))


class Phone(commands.Cog):
    """Gestion des applications du téléphone."""
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.data or "custom_id" not in interaction.data:
            return

        custom_id = interaction.data["custom_id"]

        # Ce listener ne s'occupe que des boutons du téléphone
        if not custom_id.startswith("phone_"):
            return

        if custom_id == "phone_sms":
            # Ici, vous pourriez ouvrir une nouvelle vue ou un modal pour les SMS
            await interaction.response.send_message("Messagerie en cours de développement.", ephemeral=True)
        
        elif custom_id == "phone_shop":
            # Ici, vous pourriez afficher l'embed de la boutique
            await interaction.response.send_message("La boutique du téléphone arrive bientôt !", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Phone(bot))