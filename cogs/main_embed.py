# --- cogs/main_embed.py (REFACTORED AND CORRECTED) ---

import discord
from discord.ext import commands
from discord import ui
from db.database import SessionLocal
from db.models import ServerState, PlayerProfile
import datetime
import traceback
from .phone import PhoneMainView
from utils.helpers import clamp

def generate_progress_bar(value: float, max_value: float = 100.0, length: int = 10, high_is_bad: bool = False) -> str:
    if not isinstance(value, (int, float)): value = 0.0
    value = clamp(value, 0, max_value)
    percent = value / max_value
    filled_length = int(length * percent)
    bar_filled = '🟥' if (high_is_bad and percent > 0.7) or (not high_is_bad and percent < 0.3) else '🟧' if (high_is_bad and percent > 0.4) or (not high_is_bad and percent < 0.6) else '🟩'
    bar_empty = '⬛'
    return f"`{bar_filled * filled_length}{bar_empty * (length - filled_length)}`"

# --- VUES ---

class DashboardView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=None)
        self.update_buttons(player)

    def update_buttons(self, player: PlayerProfile):
        self.clear_items()
        self.add_item(ui.Button(label="🏃‍♂️ Actions", style=discord.ButtonStyle.primary, custom_id="nav_actions"))
        self.add_item(ui.Button(label="👖 Inventaire", style=discord.ButtonStyle.secondary, custom_id="nav_inventory"))
        self.add_item(ui.Button(label="📱 Téléphone", style=discord.ButtonStyle.blurple, custom_id="phone_open"))

        stats_label = "Cacher Cerveau" if player.show_stats_in_view else "Afficher Cerveau"
        stats_style = discord.ButtonStyle.success if player.show_stats_in_view else discord.ButtonStyle.secondary
        self.add_item(ui.Button(label=stats_label, style=stats_style, custom_id="nav_toggle_stats", row=1, emoji="🧠"))

class ActionsView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=None)
        # ... (button definitions as before)
        self.add_item(ui.Button(label="⬅️ Retour", style=discord.ButtonStyle.grey, custom_id="nav_main_menu", row=2))

# ... (Other view classes as before) ...

class InventoryView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ui.Button(label="⬅️ Retour au Tableau de Bord", style=discord.ButtonStyle.grey, custom_id="nav_main_menu"))

# --- COG ---

class MainEmbed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_image_url(self, player: PlayerProfile) -> str | None:
        # ... (implementation as before)
        pass

    @staticmethod
    def get_character_thoughts(player: PlayerProfile) -> str:
        # ... (implementation as before)
        pass

    def generate_dashboard_embed(self, player: PlayerProfile, state: ServerState, guild: discord.Guild) -> discord.Embed:
        embed = discord.Embed(title="👨‍🍳 Le Quotidien du Cuisinier", color=0x3498db)
        image_url = self.get_image_url(player)
        
        if image_url:
            embed.set_image(url=image_url) # Always set the main image
            if player.show_stats_in_view: # If stats are shown, ALSO set the thumbnail
                embed.set_thumbnail(url=image_url)

        embed.description = f"**Pensées du Cuisinier :**\n*\"{self.get_character_thoughts(player)}\""*

        # ... (rest of the embed generation as before)
        return embed

    def generate_inventory_embed(self, player: PlayerProfile, guild: discord.Guild) -> discord.Embed:
        embed = discord.Embed(title="👖 Inventaire du Cuisinier", color=0x2ecc71)
        # ... (field generation as before)
        
        image_url = self.get_image_url(player)
        if image_url:
            embed.set_thumbnail(url=image_url) # Set thumbnail for sub-menus
            
        return embed

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.data or "custom_id" not in interaction.data: return
        
        custom_id = interaction.data["custom_id"]
        db = SessionLocal()
        try:
            state = db.query(ServerState).filter_by(guild_id=str(interaction.guild.id)).first()
            
            # CRITICAL FIX: Ignore interactions that are not on the main game message
            if not state or not state.game_message_id or interaction.message.id != state.game_message_id:
                # This interaction is not for us, unless it's a phone interaction which is handled separately.
                if not custom_id.startswith(("phone_", "shop_buy_", "ubereats_buy_")):
                    # We can send a generic error if we want, but it's better to just ignore.
                    # A simple return is the safest to avoid conflicts with other cogs.
                    return

            if custom_id.startswith(("phone_", "shop_buy_", "ubereats_buy_")):
                player = db.query(PlayerProfile).filter_by(guild_id=str(interaction.guild.id)).first()
                if not player:
                    try: await interaction.response.send_message("Erreur: Profil du joueur introuvable.", ephemeral=True)
                    except discord.errors.InteractionResponded: pass
                    return
                phone_cog = self.bot.get_cog("Phone")
                if phone_cog: await phone_cog.handle_interaction(interaction, db, player, state, self)
                return

            player = db.query(PlayerProfile).filter_by(guild_id=str(interaction.guild.id)).first()
            if not player:
                try: await interaction.response.send_message("Erreur: Profil du joueur introuvable.", ephemeral=True)
                except discord.errors.InteractionResponded: pass
                return

            # Defer all other game interactions
            await interaction.response.defer()

            # ... (rest of the on_interaction logic as before)

        except Exception as e:
            print(f"Erreur critique dans le listener on_interaction: {e}")
            traceback.print_exc()
            db.rollback()
        finally:
            db.close()

async def setup(bot):
    await bot.add_cog(MainEmbed(bot))