# --- cogs/phone.py (REFACTORED) ---
import discord
from discord.ext import commands
from discord import ui
from sqlalchemy.orm import Session
from db.models import PlayerProfile, ServerState
import json
from utils.helpers import get_player_notif_settings # Import the helper

# --- VUES ---
class PhoneMainView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=180)
        self.add_item(ui.Button(label="💬 SMS", style=discord.ButtonStyle.green, custom_id="phone_sms"))
        self.add_item(ui.Button(label="🔔 Notifications", style=discord.ButtonStyle.primary, custom_id="phone_notifications"))
        self.add_item(ui.Button(label="⚙️ Paramètres", style=discord.ButtonStyle.secondary, custom_id="phone_settings"))
        self.add_item(ui.Button(label="🍔 Uber Eats", style=discord.ButtonStyle.success, custom_id="phone_ubereats"))
        self.add_item(ui.Button(label="🛍️ Smoke-Shop", style=discord.ButtonStyle.blurple, custom_id="phone_shop", disabled=(not player.has_unlocked_smokeshop)))
        self.add_item(ui.Button(label="⬅️ Fermer le téléphone", style=discord.ButtonStyle.grey, custom_id="nav_main_menu", row=2))

class SMSView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=180)
        self.add_item(ui.Button(label="⬅️ Retour", style=discord.ButtonStyle.grey, custom_id="phone_open"))
        
class UberEatsView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=180)
        # ... (items as before, this view is illustrative)
        self.add_item(ui.Button(label="Tacos (6$)", emoji="🌮", style=discord.ButtonStyle.success, custom_id="ubereats_buy_tacos", disabled=(player.wallet < 6)))
        self.add_item(ui.Button(label="⬅️ Retour", style=discord.ButtonStyle.grey, custom_id="phone_open", row=2))

class ShopView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=180)
        # ... (items as before, this view is illustrative)
        self.add_item(ui.Button(label="Acheter Cigarettes (5$)", emoji="🚬", style=discord.ButtonStyle.secondary, custom_id="shop_buy_cigarettes", disabled=(player.wallet < 5)))
        self.add_item(ui.Button(label="⬅️ Retour", style=discord.ButtonStyle.grey, custom_id="phone_open", row=2))

class NotificationsView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=180)
        self.add_item(ui.Button(label="⬅️ Retour", style=discord.ButtonStyle.grey, custom_id="phone_open"))

class SettingsView(ui.View):
    def __init__(self, player: PlayerProfile, settings: dict):
        super().__init__(timeout=180)
        
        notif_types = {
            "low_vitals": "📉 Vitals Faibles",
            "cravings": "🚬 Envies",
            "friend_messages": "💬 Messages d'amis"
        }

        for key, label in notif_types.items():
            is_enabled = settings.get(key, True)
            style = discord.ButtonStyle.success if is_enabled else discord.ButtonStyle.danger
            button_label = f"{label}: {'Activé' if is_enabled else 'Désactivé'}"
            self.add_item(ui.Button(label=button_label, style=style, custom_id=f"phone_toggle_notif:{key}"))

        self.add_item(ui.Button(label="⬅️ Retour", style=discord.ButtonStyle.grey, custom_id="phone_open", row=2))

class Phone(commands.Cog):
    """Fournit la logique pour les applications du téléphone."""
    def __init__(self, bot):
        self.bot = bot

    def _add_thumbnail(self, embed: discord.Embed, player: PlayerProfile, main_embed_cog: commands.Cog):
        if image_url := main_embed_cog.get_image_url(player):
            embed.set_thumbnail(url=image_url)

    def generate_settings_embed(self, player: PlayerProfile, main_embed_cog: commands.Cog) -> discord.Embed:
        embed = discord.Embed(title="⚙️ Paramètres de Notification", description="Choisissez les notifications que vous souhaitez recevoir.", color=discord.Color.dark_grey())
        self._add_thumbnail(embed, player, main_embed_cog)
        return embed

    # ... (other generate_embed functions)

    async def handle_interaction(self, interaction: discord.Interaction, db: Session, player: PlayerProfile, state: ServerState, main_embed_cog: commands.Cog):
        """Gère toutes les interactions liées au téléphone."""
        try:
            await interaction.response.defer()
        except discord.errors.InteractionResponded:
            pass

        custom_id = interaction.data["custom_id"]
        
        if custom_id == "phone_settings":
            settings = get_player_notif_settings(player)
            await interaction.edit_original_response(embed=self.generate_settings_embed(player, main_embed_cog), view=SettingsView(player, settings))
        
        elif custom_id.startswith("phone_toggle_notif:"):
            key_to_toggle = custom_id.split(":")[1]
            settings = get_player_notif_settings(player)
            settings[key_to_toggle] = not settings.get(key_to_toggle, True)
            player.notifications_config = json.dumps(settings)
            db.commit()
            db.refresh(player)
            await interaction.edit_original_response(embed=self.generate_settings_embed(player, main_embed_cog), view=SettingsView(player, settings))

        # ... (rest of the handle_interaction logic)

async def setup(bot):
    await bot.add_cog(Phone(bot))