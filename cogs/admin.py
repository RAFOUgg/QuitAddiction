# --- cogs/admin.py (FINAL REFACTORED VERSION) ---

import discord
from discord.ext import commands
from discord import app_commands, ui
import hashlib
import math
from typing import List, Tuple, Dict
import os
import traceback

from db.database import SessionLocal
from db.models import ServerState
from utils.logger import get_logger
from utils.embed_builder import create_styled_embed

logger = get_logger(__name__)
MAX_OPTIONS_PER_PAGE = 24  # 24 items + 1 for pagination

# --- Helper Function (moved outside the class for clarity) ---
def create_options_and_mapping(items: list, item_type: str, guild: discord.Guild) -> Tuple[List[discord.SelectOption], Dict[str, str]]:
    options, id_mapping = [], {}
    
    if item_type == "role":
        sorted_items = sorted(items, key=lambda x: x.position, reverse=True)
    else: # channel
        sorted_items = sorted(items, key=lambda x: (x.category.position if x.category else 999, x.position))
    
    for item in sorted_items:
        if (item_type == "role" and item.is_default()) or (item_type == "channel" and not isinstance(item, discord.TextChannel)):
            continue
        
        item_id, item_name = str(item.id), item.name
        label = f"🔹 {item_name}" if item_type == "role" else f"📁 {item.category.name if item.category else 'No Category'} | #{item_name}"
        
        hashed_id = hashlib.sha256(item_id.encode()).hexdigest()[:25]
        options.append(discord.SelectOption(label=label[:100], value=hashed_id, description=f"ID: {item_id}"))
        id_mapping[hashed_id] = item_id
        
    if not options:
        options.append(discord.SelectOption(label="No items found", value="no_items"))
    return options, id_mapping

# --- Reusable UI Components ---
class BackToMainButton(ui.Button):
    """A button that returns the user to the main configuration menu."""
    def __init__(self, cog: 'AdminCog', row: int):
        super().__init__(label="⬅ Back to Main Menu", style=discord.ButtonStyle.red, row=row)
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        # CORRECTION : Simplification du callback.
        # Il n'est pas nécessaire de defer() si l'opération est rapide.
        # interaction.response.edit_message est la manière directe de mettre à jour le message.
        view = MainConfigView(self.cog)
        # On modifie le message pour afficher l'embed et la vue du menu principal, ce qui correspond à un "retour".
        await interaction.response.edit_message(embed=view.create_embed(interaction.guild), view=view)

class PaginatedSelect(ui.Select):
    """A reusable paginated select menu that correctly interacts with its parent view."""
    def __init__(self, select_type: str, all_options: list, id_mapping: dict, current_page: int, row: int):
        self.select_type = select_type
        self.all_options = all_options
        self.id_mapping = id_mapping
        self.current_page = current_page
        self.total_pages = max(1, math.ceil(len(self.all_options) / MAX_OPTIONS_PER_PAGE))

        start = self.current_page * MAX_OPTIONS_PER_PAGE
        page_options = self.all_options[start : start + MAX_OPTIONS_PER_PAGE]

        if self.total_pages > 1:
            if self.current_page < self.total_pages - 1:
                page_options.append(discord.SelectOption(label=f"… Next Page ({self.current_page + 2}/{self.total_pages})", value="__next_page__"))
            else:
                page_options.append(discord.SelectOption(label=f"↩ Back to Page 1", value="__first_page__"))
        
        placeholder = f"Select a {'role' if 'role' in self.select_type else 'channel'} (Page {self.current_page + 1}/{self.total_pages})"
        super().__init__(placeholder=placeholder, options=page_options, row=row)

    async def callback(self, interaction: discord.Interaction):
        selected_value = self.values[0]

        if selected_value in ["__next_page__", "__first_page__"]:
            new_page = 0 if selected_value == "__first_page__" else self.current_page + 1
            # Délègue la gestion de la pagination à la vue parente. C'est la bonne approche.
            await self.view.handle_pagination(interaction, self.select_type, new_page)
            return

        db = SessionLocal()
        try:
            selected_item_id = self.id_mapping.get(selected_value)
            if not selected_item_id:
                await interaction.response.send_message("Error: Item not found.", ephemeral=True); return

            state = db.query(ServerState).filter_by(guild_id=str(interaction.guild_id)).first()
            if state:
                setattr(state, self.select_type, selected_item_id)
                db.commit()
            
            # Rafraîchit la vue parente pour afficher le statut mis à jour dans l'embed.
            await self.view.refresh(interaction)
            await interaction.followup.send("✅ Selection updated.", ephemeral=True)
        except Exception as e:
            logger.error(f"DB Error in PaginatedSelect: {e}", exc_info=True); db.rollback()
        finally:
            db.close()

# --- Stateful Views for each Menu ---

class MainConfigView(ui.View):
    """The main entry point for configuration."""
    def __init__(self, cog: 'AdminCog'):
        super().__init__(timeout=None)
        self.cog = cog

    def create_embed(self, guild: discord.Guild) -> discord.Embed:
        db = SessionLocal()
        try:
            state = db.query(ServerState).filter_by(guild_id=str(guild.id)).first()
            embed = create_styled_embed("⚙️ Bot & Game Configuration", "Use the buttons below to adjust server settings.", discord.Color.blue())
            embed.add_field(name="▶️ General Status", value=f"**Game:** `{'Started' if state.game_started else 'Not Started'}`\n**Mode:** `{state.game_mode or 'Medium'}`", inline=False)
            admin_role = f"<@&{state.admin_role_id}>" if state.admin_role_id else "Not set"
            notif_role = f"<@&{state.notification_role_id}>" if state.notification_role_id else "Not set"
            game_chan = f"<#{state.game_channel_id}>" if state.game_channel_id else "Not set"
            embed.add_field(name="📍 Server Config", value=f"**Admin Role:** {admin_role}\n**Notification Role:** {notif_role}\n**Game Channel:** {game_chan}", inline=False)
            return embed
        finally:
            db.close()

    @ui.button(label="⚙️ Roles & Channels", style=discord.ButtonStyle.primary, row=0)
    async def roles_channels(self, interaction: discord.Interaction, button: ui.Button):
        view = RolesChannelsView(self.cog)
        # CORRECTION : On peuple les items de la vue AVANT de l'envoyer.
        # La vue doit être entièrement construite avant l'envoi. La méthode `create_embed`
        # ne doit pas être responsable de la construction des composants de l'interface.
        view.populate_items(interaction.guild)
        await interaction.response.edit_message(embed=view.create_embed(interaction.guild), view=view)

    @ui.button(label="🔔 Notifications", style=discord.ButtonStyle.primary, row=1)
    async def notifications(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("Notification settings coming soon! This is a placeholder.", ephemeral=True)
        
class RolesChannelsView(ui.View):
    """View for managing Admin Role, Notification Role, and Game Channel."""
    def __init__(self, cog: 'AdminCog', page_admin=0, page_notif=0, page_channel=0):
        super().__init__(timeout=180)
        self.cog = cog
        self.page_admin = page_admin
        self.page_notif = page_notif
        self.page_channel = page_channel

    # CORRECTION : La méthode `create_embed` est maintenant propre.
    # Elle est uniquement responsable de la création de l'embed, pas de la modification de l'état de la vue.
    # Cela évite les effets de bord et rend le code plus facile à suivre.
    def create_embed(self, guild: discord.Guild) -> discord.Embed:
        db = SessionLocal()
        try:
            state = db.query(ServerState).filter_by(guild_id=str(guild.id)).first()
            embed = create_styled_embed("⚙️ General Config (Roles & Channels)", "Use the dropdowns to select roles and channels.", discord.Color.purple())
            admin_role = f"<@&{state.admin_role_id}>" if state.admin_role_id else "Not set"
            notif_role = f"<@&{state.notification_role_id}>" if state.notification_role_id else "Not set"
            game_chan = f"<#{state.game_channel_id}>" if state.game_channel_id else "Not set"
            embed.add_field(name="👑 Admin Role", value=f"Current: {admin_role}", inline=False)
            embed.add_field(name="🔔 Notification Role", value=f"Current: {notif_role}", inline=False)
            embed.add_field(name="🎮 Game Channel", value=f"Current: {game_chan}", inline=False)
            return embed
        finally:
            db.close()

    def populate_items(self, guild: discord.Guild):
        """Rebuilds the UI components of the view based on current state."""
        self.clear_items()
        role_options, role_map = create_options_and_mapping(guild.roles, "role", guild)
        channel_options, channel_map = create_options_and_mapping(guild.text_channels, "channel", guild)
        
        self.add_item(PaginatedSelect("admin_role", role_options, role_map, self.page_admin, row=0))
        self.add_item(PaginatedSelect("notification_role", role_options, role_map, self.page_notif, row=1))
        self.add_item(PaginatedSelect("game_channel", channel_options, channel_map, self.page_channel, row=2))
        self.add_item(BackToMainButton(self.cog, row=3))

    async def handle_pagination(self, interaction: discord.Interaction, select_type: str, new_page: int):
        """Updates the page number for the correct select menu and refreshes the view."""
        if select_type == "admin_role": self.page_admin = new_page
        elif select_type == "notification_role": self.page_notif = new_page
        elif select_type == "game_channel": self.page_channel = new_page
        await self.refresh(interaction)

    # CORRECTION : La logique de rafraîchissement est maintenant plus propre et robuste.
    # Elle peuple explicitement les items, puis crée l'embed, et enfin envoie la mise à jour.
    # Cela résout le bug de la pagination.
    async def refresh(self, interaction: discord.Interaction):
        """Fully redraws the view and embed."""
        self.populate_items(interaction.guild)
        await interaction.response.edit_message(embed=self.create_embed(interaction.guild), view=self)

# --- Main Admin Cog ---
class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        """Generic error handler for views in this cog."""
        logger.error(f"Unhandled error in AdminCog view: {error}", exc_info=True)
        if interaction.response.is_done():
            await interaction.followup.send("An unexpected error occurred. Please check the logs.", ephemeral=True)
        else:
            await interaction.response.send_message("An unexpected error occurred. Please check the logs.", ephemeral=True)

    @app_commands.command(name="config", description="Configure bot and game settings.")
    @app_commands.default_permissions(administrator=True)
    async def config(self, interaction: discord.Interaction):
        db = SessionLocal()
        try:
            guild_id_str = str(interaction.guild.id)
            if not db.query(ServerState).filter_by(guild_id=guild_id_str).first():
                db.add(ServerState(guild_id=guild_id_str))
                db.commit()
            
            view = MainConfigView(self)
            await interaction.response.send_message(embed=view.create_embed(interaction.guild), view=view, ephemeral=True)
        except Exception as e:
            logger.error(f"Error in /config: {e}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message("An error occurred.", ephemeral=True)
        finally:
            db.close()

async def setup(bot):
    await bot.add_cog(AdminCog(bot))