# --- cogs/admin.py (FINAL, COMPLETE, AND RESTRUCTURED) ---

import discord
from discord.ext import commands
from discord import app_commands, ui
import hashlib
import datetime
import math
from typing import List, Tuple, Dict, Type
import os
import traceback

# --- Imports from your project ---
from db.database import SessionLocal
from db.models import ServerState
from utils.logger import get_logger
from utils.embed_builder import create_styled_embed

# --- Setup ---
logger = get_logger(__name__)
MAX_OPTIONS_PER_PAGE = 24  # Discord's limit is 25, we use one for the pagination button.
GITHUB_REPO_OWNER = os.getenv("GITHUB_REPO_OWNER")
GITHUB_REPO_NAME = os.getenv("GITHUB_REPO_NAME")

# ======================================================================================
# SECTION 1: CORE HELPER & REUSABLE COMPONENTS
# Ces composants sont la fondation de notre interface robuste.
# ======================================================================================

def create_options_and_mapping(items: list, item_type: str, guild: discord.Guild) -> Tuple[List[discord.SelectOption], Dict[str, str]]:
    """Crée les options pour un SelectMenu et un mapping ID -> ID haché."""
    options, id_mapping = [], {}
    if item_type == "role":
        sorted_items = sorted(items, key=lambda x: x.position, reverse=True)
    else:  # channel
        sorted_items = sorted(items, key=lambda x: (x.category.position if x.category else 999, x.position))
    
    for item in sorted_items:
        if (item_type == "role" and item.is_default()) or \
           (item_type == "channel" and not isinstance(item, discord.TextChannel)):
            continue
        
        item_id, item_name = str(item.id), item.name
        label = f"🔹 {item_name}" if item_type == "role" else f"📁 {item.category.name if item.category else 'No Category'} | #{item_name}"
        hashed_id = hashlib.sha256(item_id.encode()).hexdigest()[:25]
        options.append(discord.SelectOption(label=label[:100], value=hashed_id, description=f"ID: {item_id}"))
        id_mapping[hashed_id] = item_id
        
    if not options:
        options.append(discord.SelectOption(label="No items found", value="no_items"))
    return options, id_mapping


class BackButton(ui.Button):
    """Bouton flexible pour revenir à une vue précédente définie."""
    def __init__(self, target_view_class: Type[ui.View], cog: 'AdminCog', row: int, label: str = "⬅ Back"):
        super().__init__(label=label, style=discord.ButtonStyle.red, row=row)
        self.target_view_class = target_view_class
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        view = self.target_view_class(self.cog)
        await view.refresh(interaction, is_initial=True)


class PaginatedSelect(ui.Select):
    """Un menu déroulant paginé réutilisable qui délègue la gestion de la pagination à sa vue parente."""
    def __init__(self, select_type: str, all_options: list, id_mapping: dict, current_page: int, row: int, placeholder_text: str):
        self.select_type = select_type
        self.all_options = all_options
        self.id_mapping = id_mapping
        self.current_page = current_page
        self.total_pages = max(1, math.ceil(len(self.all_options) / MAX_OPTIONS_PER_PAGE))
        start = self.current_page * MAX_OPTIONS_PER_PAGE
        page_options = self.all_options[start : start + MAX_OPTIONS_PER_PAGE]

        if self.total_pages > 1:
            if self.current_page < self.total_pages - 1:
                page_options.append(discord.SelectOption(label=f"… Page Suivante ({self.current_page + 2}/{self.total_pages})", value="__next_page__"))
            else:
                page_options.append(discord.SelectOption(label=f"↩ Revenir à la Page 1", value="__first_page__"))
        
        placeholder = f"{placeholder_text} (Page {self.current_page + 1}/{self.total_pages})"
        super().__init__(placeholder=placeholder, options=page_options, row=row)

    async def callback(self, interaction: discord.Interaction):
        selected_value = self.values[0]
        if selected_value in ["__next_page__", "__first_page__"]:
            new_page = 0 if selected_value == "__first_page__" else self.current_page + 1
            await self.view.handle_pagination(interaction, self.select_type, new_page)
            return
        
        db = SessionLocal()
        try:
            selected_item_id = self.id_mapping.get(selected_value)
            if not selected_item_id:
                await interaction.response.send_message("Erreur: Item non trouvé.", ephemeral=True); return
            state = db.query(ServerState).filter_by(guild_id=str(interaction.guild_id)).first()
            if state:
                setattr(state, self.select_type, selected_item_id)
                db.commit()
            await self.view.refresh(interaction)
            await interaction.followup.send("✅ Sélection mise à jour.", ephemeral=True)
        finally:
            db.close()

# ======================================================================================
# SECTION 2: "STATEFUL" VIEWS
# Chaque "écran" est une classe View qui conserve son propre état.
# ======================================================================================

class MainConfigView(ui.View):
    """Vue principale du menu de configuration. Point d'entrée de l'interface."""
    def __init__(self, cog: 'AdminCog'):
        super().__init__(timeout=None)
        self.cog = cog
        # Ajout de tous vos boutons originaux
        self.add_item(self.SetupGameModeButton())
        self.add_item(self.StartResetGameButton())
        self.add_item(self.GeneralConfigButton())
        self.add_item(self.NotificationsButton())
        self.add_item(self.ViewStatsButton())
        self.add_item(self.ProjectStatsButton())

    async def create_embed(self, guild: discord.Guild) -> discord.Embed:
        db = SessionLocal()
        try:
            state = db.query(ServerState).filter_by(guild_id=str(guild.id)).first()
            embed = create_styled_embed("⚙️ Bot & Game Configuration", "Use the buttons below to adjust server settings.", discord.Color.blue())
            duration_label = self.cog.GAME_DURATIONS.get(state.duration_key, {}).get('label', 'Medium (31 days)')
            embed.add_field(name="▶️ **General Status**", value=f"**Game:** `{'In Progress' if state.game_started else 'Not Started'}`\n**Mode:** `{state.game_mode.capitalize() if state.game_mode else 'Medium (Default)'}`\n**Duration:** `{duration_label}`", inline=False)
            admin_role = f"<@&{state.admin_role_id}>" if state.admin_role_id else "Not set"
            notif_role = f"<@&{state.notification_role_id}>" if state.notification_role_id else "Not set"
            game_chan = f"<#{state.game_channel_id}>" if state.game_channel_id else "Not set"
            embed.add_field(name="📍 **Server Config**", value=f"**Admin Role:** {admin_role}\n**Notification Role:** {notif_role}\n**Game Channel:** {game_chan}", inline=False)
            embed.add_field(name="⏱️ **Game Parameters**", value=f"**Tick Interval (min):** `{state.game_tick_interval_minutes or 30}`", inline=False)
            degradation_text = f"**Hunger:** `{state.degradation_rate_hunger:.1f}` | **Thirst:** `{state.degradation_rate_thirst:.1f}` | **Bladder:** `{state.degradation_rate_bladder:.1f}`\n**Energy:** `{state.degradation_rate_energy:.1f}` | **Stress:** `{state.degradation_rate_stress:.1f}` | **Boredom:** `{state.degradation_rate_boredom:.1f}`"
            embed.add_field(name="📉 **Degradation Rates / Tick**", value=degradation_text, inline=False)
            embed.set_footer(text="Use the buttons below to navigate and modify settings.")
            return embed
        finally:
            db.close()

    async def refresh(self, interaction: discord.Interaction, is_initial: bool = False):
        """Méthode standard pour afficher ou rafraîchir la vue."""
        embed = await self.create_embed(interaction.guild)
        if is_initial:
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.edit_original_response(embed=embed, view=self)

    # --- Nested Button Classes for better organization and to access self.view ---
    class SetupGameModeButton(ui.Button):
        def __init__(self):
            super().__init__(label="🕹️ Mode & Duration", style=discord.ButtonStyle.primary, row=0)
        async def callback(self, interaction: discord.Interaction):
            view = ModeDurationView(self.view.cog)
            await view.refresh(interaction, is_initial=True)

    class StartResetGameButton(ui.Button):
        def __init__(self):
            super().__init__(label="🎮 Start/Reset Game", style=discord.ButtonStyle.success, row=0)
        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            try:
                state = db.query(ServerState).filter_by(guild_id=str(interaction.guild_id)).first()
                if state:
                    state.game_started = not state.game_started
                    state.game_start_time = datetime.datetime.utcnow() if state.game_started else None
                    db.commit()
                    # We need to use followup for the confirmation message after a defer/edit
                    await interaction.response.defer() # Acknowledge the interaction
                    await self.view.refresh(interaction)
                    await interaction.followup.send(f"The game has been {'started' if state.game_started else 'stopped/reset'}.", ephemeral=True)
            finally: db.close()

    class GeneralConfigButton(ui.Button):
        def __init__(self):
            super().__init__(label="⚙️ Roles & Channels", style=discord.ButtonStyle.primary, row=0)
        async def callback(self, interaction: discord.Interaction):
            view = RolesChannelsView(self.view.cog)
            await view.refresh(interaction, is_initial=True)

    class NotificationsButton(ui.Button):
        def __init__(self):
            super().__init__(label="🔔 Notifications", style=discord.ButtonStyle.primary, row=1)
        async def callback(self, interaction: discord.Interaction):
            view = NotificationsView(self.view.cog)
            await view.refresh(interaction, is_initial=True)

    class ViewStatsButton(ui.Button):
        def __init__(self):
            super().__init__(label="📊 View Stats", style=discord.ButtonStyle.primary, row=1)
        async def callback(self, interaction: discord.Interaction):
            await interaction.response.send_message("This feature is under development.", ephemeral=True)

    class ProjectStatsButton(ui.Button):
        def __init__(self):
            super().__init__(label="📈 Project Stats", style=discord.ButtonStyle.secondary, row=1)
        async def callback(self, interaction: discord.Interaction):
            await interaction.response.defer(thinking=True, ephemeral=True)
            try:
                dev_stats_cog = interaction.client.get_cog("DevStatsCog")
                if not dev_stats_cog:
                    await interaction.followup.send("Error: DevStatsCog not found.", ephemeral=True); return
                commit_data = await dev_stats_cog.get_commit_stats()
                loc_data = dev_stats_cog.get_loc_stats()
                if "error" in commit_data: await interaction.followup.send(f"❌ GitHub Error: {commit_data['error']}", ephemeral=True); return
                if "error" in loc_data: await interaction.followup.send(f"❌ Local Error: {loc_data['error']}", ephemeral=True); return
                
                embed = create_styled_embed(title=f"📊 Project Stats - {GITHUB_REPO_NAME}", description="A snapshot of the project's development activity.", color=discord.Color.dark_green())
                first_commit_ts, last_commit_ts = int(commit_data['first_commit_date'].timestamp()), int(commit_data['last_commit_date'].timestamp())
                project_duration_days = (commit_data['last_commit_date'] - commit_data['first_commit_date']).days
                commit_text = f"**Total commits:** `{commit_data['total_commits']}`\n**First commit:** <t:{first_commit_ts}:D>\n**Last commit:** <t:{last_commit_ts}:R>\n**Project duration:** `{project_duration_days} days`"
                embed.add_field(name="⚙️ Commit Activity", value=commit_text, inline=False)
                loc_text = f"**Lines of code:** `{loc_data['total_lines']:,}`\n**Characters:** `{loc_data['total_chars']:,}`\n**Python files:** `{loc_data['total_files']}`"
                embed.add_field(name="💻 Source Code (.py)", value=loc_text, inline=True)
                total_hours = commit_data['estimated_duration'].total_seconds() / 3600
                embed.add_field(name="⏱️ Development Time", value=f"**Estimation:**\n`{total_hours:.2f} hours`", inline=True)
                embed.set_footer(text="Data via GitHub API & local git commands.")
                await interaction.followup.send(embed=embed, ephemeral=True)
            except Exception as e:
                logger.error(f"Error in ProjectStatsButton callback: {e}", exc_info=True)
                await interaction.followup.send("A critical error occurred while fetching project stats.", ephemeral=True)


class ModeDurationView(ui.View):
    """Vue pour la configuration du mode et de la durée du jeu."""
    def __init__(self, cog: 'AdminCog'):
        super().__init__(timeout=180)
        self.cog = cog
        self.add_item(self.GameModeSelect(self.cog))
        self.add_item(self.GameDurationSelect(self.cog))
        self.add_item(BackButton(target_view_class=MainConfigView, cog=self.cog, row=2, label="⬅ Back to Main Settings"))

    def create_embed(self, message: str = None) -> discord.Embed:
        desc = "Select a difficulty and duration for the game."
        if message:
            desc = f"✅ {message}\n\n{desc}"
        return create_styled_embed("🎮 Mode & Duration Setup", desc, discord.Color.teal())
    
    async def refresh(self, interaction: discord.Interaction, is_initial: bool = False, message: str = None):
        if is_initial:
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
        else:
            await interaction.edit_original_response(embed=self.create_embed(message), view=self)

    class GameModeSelect(ui.Select):
        def __init__(self, cog: 'AdminCog'):
            self.cog = cog
            options = [discord.SelectOption(label=mode.capitalize(), value=mode) for mode in cog.GAME_MODES.keys()]
            super().__init__(placeholder="Choose a difficulty mode...", options=options, row=0)
        async def callback(self, interaction: discord.Interaction):
            db, selected_mode = SessionLocal(), self.values[0]
            try:
                state = db.query(ServerState).filter_by(guild_id=str(interaction.guild_id)).first()
                mode_data = self.view.cog.GAME_MODES.get(selected_mode)
                if state and mode_data:
                    state.game_mode = selected_mode
                    state.game_tick_interval_minutes = mode_data["tick_interval_minutes"]
                    for key, value in mode_data["rates"].items(): setattr(state, f"degradation_rate_{key.replace('_base', '')}", value)
                    db.commit()
                    await self.view.refresh(interaction, message=f"Difficulty set to **{selected_mode.capitalize()}**.")
            finally: db.close()

    class GameDurationSelect(ui.Select):
        def __init__(self, cog: 'AdminCog'):
            self.cog = cog
            options = [discord.SelectOption(label=data["label"], value=key) for key, data in cog.GAME_DURATIONS.items()]
            super().__init__(placeholder="Choose the game duration...", options=options, row=1)
        async def callback(self, interaction: discord.Interaction):
            db, selected_key = SessionLocal(), self.values[0]
            try:
                state = db.query(ServerState).filter_by(guild_id=str(interaction.guild_id)).first()
                duration_data = self.view.cog.GAME_DURATIONS.get(selected_key)
                if state and duration_data:
                    state.duration_key = selected_key
                    db.commit()
                    await self.view.refresh(interaction, message=f"Duration set to **{duration_data['label']}**.")
            finally: db.close()

class RolesChannelsView(ui.View):
    """Vue Stateful pour la configuration des Rôles & Canaux."""
    def __init__(self, cog: 'AdminCog', page_admin=0, page_notif=0, page_channel=0):
        super().__init__(timeout=180)
        self.cog = cog
        self.page_admin, self.page_notif, self.page_channel = page_admin, page_notif, page_channel

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
        finally: db.close()
    
    def populate_items(self, guild: discord.Guild):
        self.clear_items()
        role_options, role_map = create_options_and_mapping(guild.roles, "role", guild)
        channel_options, channel_map = create_options_and_mapping(guild.text_channels, "channel", guild)
        self.add_item(PaginatedSelect("admin_role_id", role_options, role_map, self.page_admin, row=0, placeholder_text="Select an Admin Role"))
        self.add_item(PaginatedSelect("notification_role_id", role_options, role_map, self.page_notif, row=1, placeholder_text="Select a Notification Role"))
        self.add_item(PaginatedSelect("game_channel_id", channel_options, channel_map, self.page_channel, row=2, placeholder_text="Select a Game Channel"))
        self.add_item(BackButton(target_view_class=MainConfigView, cog=self.cog, row=3, label="⬅ Back to Main Settings"))

    async def handle_pagination(self, interaction: discord.Interaction, select_type: str, new_page: int):
        if select_type == "admin_role_id": self.page_admin = new_page
        elif select_type == "notification_role_id": self.page_notif = new_page
        elif select_type == "game_channel_id": self.page_channel = new_page
        await self.refresh(interaction)

    async def refresh(self, interaction: discord.Interaction, is_initial: bool = False):
        self.populate_items(interaction.guild)
        embed = self.create_embed(interaction.guild)
        if is_initial:
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.edit_original_response(embed=embed, view=self)


class NotificationsView(ui.View):
    """Vue Stateful pour la configuration des notifications."""
    def __init__(self, cog: 'AdminCog', role_page=0):
        super().__init__(timeout=180)
        self.cog = cog
        self.role_page = role_page

    def create_embed(self, guild: discord.Guild) -> discord.Embed:
        #... (votre logique de création d'embed)
        db = SessionLocal()
        try:
            state = db.query(ServerState).filter_by(guild_id=str(guild.id)).first()
            embed = discord.Embed(title="🔔 Notification Settings", color=discord.Color.green())
            notif_role_mention = f"<@&{state.notification_role_id}>" if state.notification_role_id else "Not set"
            embed.add_field(name="📍 General Notification Role", value=notif_role_mention, inline=False)
            specific_roles_text = (
                f"📉 Low Vitals: {f'<@&{state.notify_vital_low_role_id}>' if state.notify_vital_low_role_id else 'Not set'}\n"
                f"🚨 Critical: {f'<@&{state.notify_critical_role_id}>' if state.notify_critical_role_id else 'Not set'}\n"
                f"🚬 Cravings: {f'<@&{state.notify_envie_fumer_role_id}>' if state.notify_envie_fumer_role_id else 'Not set'}\n"
                f"💬 Friend/Quiz Msg: {f'<@&{state.notify_friend_message_role_id}>' if state.notify_friend_message_role_id else 'Not set'}\n"
                f"🛒 Shop Promos: {f'<@&{state.notify_shop_promo_role_id}>' if state.notify_shop_promo_role_id else 'Not set'}")
            embed.add_field(name="🚨 Specific Alert Roles", value=specific_roles_text, inline=False)
            embed.set_footer(text="Use the buttons to toggle and the menu to set roles.")
            return embed
        finally:
            db.close()
    
    def populate_items(self, guild: discord.Guild, state: ServerState):
        self.clear_items()
        # Boutons de bascule
        self.add_item(self.NotificationToggle("🔴 Low Vitals", "notify_on_low_vital_stat", state.notify_on_low_vital_stat, row=0))
        self.add_item(self.NotificationToggle("🔴 Critical Event", "notify_on_critical_event", state.notify_on_critical_event, row=0))
        self.add_item(self.NotificationToggle("🚬 Cravings", "notify_on_envie_fumer", state.notify_on_envie_fumer, row=1))
        self.add_item(self.NotificationToggle("💬 Friend/Quiz", "notify_on_friend_message", state.notify_on_friend_message, row=1))
        self.add_item(self.NotificationToggle("💛 Shop Promo", "notify_on_shop_promo", state.notify_on_shop_promo, row=1))
        
        # Menu déroulant paginé pour le rôle de notification général
        role_options, role_map = create_options_and_mapping(guild.roles, "role", guild)
        self.add_item(PaginatedSelect("notification_role_id", role_options, role_map, self.role_page, row=2, placeholder_text="Set General Notification Role"))
        
        # Bouton retour
        self.add_item(BackButton(target_view_class=MainConfigView, cog=self.cog, row=3, label="⬅ Back to Main Settings"))

    async def handle_pagination(self, interaction: discord.Interaction, select_type: str, new_page: int):
        self.role_page = new_page
        await self.refresh(interaction)

    async def refresh(self, interaction: discord.Interaction, is_initial: bool = False):
        db = SessionLocal()
        try:
            state = db.query(ServerState).filter_by(guild_id=str(interaction.guild_id)).first()
            self.populate_items(interaction.guild, state)
            embed = self.create_embed(interaction.guild)
            if is_initial:
                await interaction.response.edit_message(embed=embed, view=self)
            else:
                await interaction.edit_original_response(embed=embed, view=self)
        finally:
            db.close()

    class NotificationToggle(ui.Button):
        def __init__(self, label: str, toggle_key: str, is_enabled: bool, row: int):
            style = discord.ButtonStyle.success if is_enabled else discord.ButtonStyle.secondary
            super().__init__(label=label, style=style, row=row)
            self.toggle_key = toggle_key
        
        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            try:
                state = db.query(ServerState).filter_by(guild_id=str(interaction.guild_id)).first()
                if state:
                    if state.game_started:
                        await interaction.response.send_message("Cannot change notification settings while a game is in progress.", ephemeral=True); return
                    current_value = getattr(state, self.toggle_key, False)
                    setattr(state, self.toggle_key, not current_value)
                    db.commit()
                    await self.view.refresh(interaction)
            finally:
                db.close()

# ======================================================================================
# SECTION 3: THE MAIN ADMIN COG
# ======================================================================================

class AdminCog(commands.Cog):
    """Gestion des configurations du bot et du jeu pour le serveur."""
    def __init__(self, bot):
        self.bot = bot
        self.GAME_MODES = { "peaceful": { "tick_interval_minutes": 60, "rates": { "hunger": 5.0, "thirst": 4.0, "bladder": 5.0, "energy": 3.0, "stress": 1.0, "boredom": 2.0, "addiction_base": 0.05, "toxins_base": 0.1 } }, "medium": { "tick_interval_minutes": 30, "rates": { "hunger": 10.0, "thirst": 8.0, "bladder": 15.0, "energy": 5.0, "stress": 3.0, "boredom": 7.0, "addiction_base": 0.1, "toxins_base": 0.5 } }, "hard": { "tick_interval_minutes": 15, "rates": { "hunger": 20.0, "thirst": 16.0, "bladder": 30.0, "energy": 10.0, "stress": 6.0, "boredom": 14.0, "addiction_base": 0.2, "toxins_base": 1.0 } } }
        self.GAME_DURATIONS = { "short": {"days": 14, "label": "Court (14 jours)"}, "medium": {"days": 31, "label": "Moyen (31 jours)"}, "long": {"days": 72, "label": "Long (72 jours)"}, }

    @app_commands.command(name="config", description="Configure les paramètres du bot et du jeu pour le serveur.")
    @app_commands.default_permissions(administrator=True)
    async def config(self, interaction: discord.Interaction):
        db = SessionLocal()
        try:
            if not db.query(ServerState).filter_by(guild_id=str(interaction.guild_id)).first():
                db.add(ServerState(guild_id=str(interaction.guild_id)))
                db.commit()
            
            view = MainConfigView(self)
            embed = await view.create_embed(interaction.guild)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        finally:
            db.close()

async def setup(bot):
    await bot.add_cog(AdminCog(bot))