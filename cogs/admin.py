# --- cogs/admin.py (FULLY CORRECTED) ---

import discord
from discord.ext import commands
from discord import app_commands, ui
import hashlib
import datetime
import math
from typing import List, Tuple, Dict
import os
import traceback

# --- CORRECT: Centralized Imports ---
from db.database import SessionLocal
from db.models import ServerState, PlayerProfile
from utils.logger import get_logger
from utils.embed_builder import create_styled_embed

# --- Setup Logger for this Cog ---
logger = get_logger(__name__)


# --- Setup Logger for this Cog ---
logger = get_logger(__name__)

# --- Constants ---
MAX_OPTIONS_PER_PAGE = 25

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO_OWNER = os.getenv("GITHUB_REPO_OWNER")
GITHUB_REPO_NAME = os.getenv("GITHUB_REPO_NAME")

class AdminCog(commands.Cog):
    """Gestion des configurations du bot et du jeu pour le serveur."""
    def __init__(self, bot):
        self.bot = bot

    GAME_MODES = { "peaceful": { "tick_interval_minutes": 60, "rates": { "hunger": 5.0, "thirst": 4.0, "bladder": 5.0, "energy": 3.0, "stress": 1.0, "boredom": 2.0, "addiction_base": 0.05, "toxins_base": 0.1, } }, "medium": { "tick_interval_minutes": 30, "rates": { "hunger": 10.0, "thirst": 8.0, "bladder": 15.0, "energy": 5.0, "stress": 3.0, "boredom": 7.0, "addiction_base": 0.1, "toxins_base": 0.5, } }, "hard": { "tick_interval_minutes": 15, "rates": { "hunger": 20.0, "thirst": 16.0, "bladder": 30.0, "energy": 10.0, "stress": 6.0, "boredom": 14.0, "addiction_base": 0.2, "toxins_base": 1.0, } } }
    GAME_DURATIONS = { "short": {"days": 14, "label": "Court (14 jours)"}, "medium": {"days": 31, "label": "Moyen (31 jours)"}, "long": {"days": 72, "label": "Long (72 jours)"}, }
    MAX_OPTION_LENGTH = 25
    MIN_OPTION_LENGTH = 1

    # -------------------
    # Commandes Admin (Slash Commands)
    # -------------------
    
    @app_commands.command(name="config", description="Configure les paramètres du bot et du jeu pour le serveur.")
    @app_commands.default_permissions(administrator=True) # Restriction aux administrateurs
    async def config(self, interaction: discord.Interaction):
        """Affiche l'interface de configuration principale."""
        guild_id_str = str(interaction.guild.id)
        db = SessionLocal()
        state = db.query(ServerState).filter_by(guild_id=guild_id_str).first()

        # Si aucun état de serveur n'existe pour ce serveur, en créer un.
        if not state:
            state = ServerState(guild_id=guild_id_str)
            db.add(state)
            db.commit() 
            state = db.query(ServerState).filter_by(guild_id=guild_id_str).first() # Recharger pour les valeurs par défaut

        # Envoyer le message interactif principal
        await interaction.response.send_message(
            embed=self.generate_config_menu_embed(state),
            view=self.generate_config_menu_view(guild_id_str, interaction.guild), # Passer le guild
            ephemeral=True 
        )
        db.close()

    # --- Méthodes pour Générer les Embeds et Vues de Configuration ---
        # Méthode principale pour générer la vue du menu de configuration
    class ProjectStatsButton(ui.Button):
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle, row: int, cog: 'AdminCog'):
            super().__init__(label=label, style=style, row=row)
            self.guild_id = guild_id
            self.cog = cog
        async def callback(self, interaction: discord.Interaction):
            await interaction.response.defer(thinking=True, ephemeral=True)
            try:
                bot = interaction.client
                dev_stats_cog = bot.get_cog("DevStatsCog")
                if not dev_stats_cog:
                    await interaction.followup.send("Error: DevStatsCog not found.", ephemeral=True)
                    return
                commit_data = await dev_stats_cog.get_commit_stats()
                loc_data = dev_stats_cog.get_loc_stats()
                if "error" in commit_data:
                    await interaction.followup.send(f"❌ GitHub Error: {commit_data['error']}", ephemeral=True)
                    return
                if "error" in loc_data:
                    await interaction.followup.send(f"❌ Local Error: {loc_data['error']}", ephemeral=True)
                    return
                embed = create_styled_embed(title=f"📊 Project Stats - {GITHUB_REPO_NAME}", description="A snapshot of the project's development activity.", color=discord.Color.dark_green())
                first_commit_ts, last_commit_ts = int(commit_data['first_commit_date'].timestamp()), int(commit_data['last_commit_date'].timestamp())
                project_duration_days = (commit_data['last_commit_date'] - commit_data['first_commit_date']).days
                commit_text = (f"**Total commits:** `{commit_data['total_commits']}`\n" f"**First commit:** <t:{first_commit_ts}:D>\n" f"**Last commit:** <t:{last_commit_ts}:R>\n" f"**Project duration:** `{project_duration_days} days`")
                embed.add_field(name="⚙️ Commit Activity", value=commit_text, inline=False)
                loc_text = (f"**Lines of code:** `{loc_data['total_lines']:,}`\n" f"**Characters:** `{loc_data['total_chars']:,}`\n" f"**Python files:** `{loc_data['total_files']}`")
                embed.add_field(name="💻 Source Code (.py)", value=loc_text, inline=True)
                total_hours = commit_data['estimated_duration'].total_seconds() / 3600
                time_text = f"**Estimation:**\n`{total_hours:.2f} hours`"
                embed.add_field(name="⏱️ Development Time", value=time_text, inline=True)
                embed.set_footer(text="Data via GitHub API & local git commands.")
                await interaction.followup.send(embed=embed, ephemeral=True)
            except Exception as e:
                logger.error(f"Error in ProjectStatsButton callback: {e}", exc_info=True)
                await interaction.followup.send("A critical error occurred while fetching project stats.", ephemeral=True)

    # --- Modification de generate_config_menu_view pour inclure le bouton ---
    def generate_config_menu_view(self, guild_id: str, guild: discord.Guild) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        view.add_item(self.SetupGameModeButton("🕹️ Mode & Duration", guild_id, discord.ButtonStyle.primary, row=0, cog=self))
        view.add_item(self.ConfigButton("🎮 Start/Reset Game", guild_id, discord.ButtonStyle.success, row=0, cog=self))
        view.add_item(self.GeneralConfigButton("⚙️ Roles & Channels", guild_id, discord.ButtonStyle.primary, row=0, cog=self))
        view.add_item(self.ConfigButton("🔔 Notifications", guild_id, discord.ButtonStyle.primary, row=1, cog=self))
        view.add_item(self.ConfigButton("📊 View Stats", guild_id, discord.ButtonStyle.primary, row=1, cog=self))
        view.add_item(self.ProjectStatsButton("📈 Project Stats", guild_id, discord.ButtonStyle.secondary, row=1, cog=self))
        view.add_item(self.BackButton("⬅ Back", guild_id, discord.ButtonStyle.red, row=2, cog=self))
        return view

    # --- Classe ProjectStatsButton (celle que nous avons définie précédemment) ---
    def create_options_and_mapping(self, items: list, item_type: str, guild: discord.Guild | None) -> Tuple[List[discord.SelectOption], Dict[str, str]]:
        options, id_mapping = [], {}
        if not guild: return [discord.SelectOption(label="Server Error", value="error_guild", default=True)], {}
        try:
            if item_type == "role": sorted_items = sorted(items, key=lambda x: x.position, reverse=True)
            elif item_type == "channel": sorted_items = sorted(items, key=lambda x: (getattr(x, 'category_id', float('inf')), x.position))
            else: sorted_items = items
        except Exception as e:
            logger.error(f"Error sorting {item_type}s: {e}"); sorted_items = items
        for item in sorted_items:
            if not (hasattr(item, 'id') and hasattr(item, 'name')): continue
            item_id, item_name = str(item.id), item.name
            if item_type == "role":
                if item.is_default(): continue
                label = f"🔹 {item_name}"
            elif item_type == "channel":
                if not isinstance(item, discord.TextChannel): continue
                category_name = item.category.name if item.category else "No Category"
                label = f"📁 {category_name} | #{item_name}"
            else: label = item_name
            label = label[:self.MAX_OPTION_LENGTH]
            hashed_id = hashlib.sha256(item_id.encode()).hexdigest()[:self.MAX_OPTION_LENGTH]
            options.append(discord.SelectOption(label=label, value=hashed_id, description=f"ID: {item_id}"))
            id_mapping[hashed_id] = item_id
        if not options: options.append(discord.SelectOption(label="No items found", value="no_items", default=True))
        return options, id_mapping

    def generate_config_menu_embed(self, state: ServerState) -> discord.Embed:
        embed = discord.Embed(title="⚙️ Bot & Game Configuration", description="Use the buttons below to adjust server settings.", color=discord.Color.blue())
        embed.add_field(name="▶️ **General Status**", value=f"**Game:** `{'In Progress' if state.game_started else 'Not Started'}`\n**Mode:** `{state.game_mode.capitalize() if state.game_mode else 'Medium (Default)'}`\n**Duration:** `{self.GAME_DURATIONS.get(state.duration_key, {}).get('label', 'Medium (31 days)')}`", inline=False)
        admin_role, notif_role, game_channel = (f"<@&{state.admin_role_id}>" if state.admin_role_id else "Not set"), (f"<@&{state.notification_role_id}>" if state.notification_role_id else "Not set"), (f"<#{state.game_channel_id}>" if state.game_channel_id else "Not set")
        embed.add_field(name="📍 **Server Config**", value=f"**Admin Role:** {admin_role}\n**Notification Role:** {notif_role}\n**Game Channel:** {game_channel}", inline=False)
        embed.add_field(name="⏱️ **Game Parameters**", value=f"**Tick Interval (min):** `{state.game_tick_interval_minutes or 30}`", inline=False)
        embed.add_field(name="📉 **Degradation Rates / Tick**", value=f"**Hunger:** `{state.degradation_rate_hunger:.1f}` | **Thirst:** `{state.degradation_rate_thirst:.1f}` | **Bladder:** `{state.degradation_rate_bladder:.1f}`\n**Energy:** `{state.degradation_rate_energy:.1f}` | **Stress:** `{state.degradation_rate_stress:.1f}` | **Boredom:** `{state.degradation_rate_boredom:.1f}`", inline=False)
        embed.set_footer(text="Use the buttons below to navigate and modify settings.")
        return embed

    class SetupGameModeButton(ui.Button):
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle, row: int, cog: 'AdminCog'):
            super().__init__(label=label, style=style, row=row); self.guild_id = guild_id; self.cog = cog
        async def callback(self, interaction: discord.Interaction):
            await interaction.response.edit_message(embed=self.cog.generate_setup_game_mode_embed(), view=self.cog.generate_setup_game_mode_view(self.guild_id))

    def generate_setup_game_mode_embed(self) -> discord.Embed:
        return discord.Embed(title="🎮 Mode & Duration Setup", description="Select a difficulty and duration for the game.", color=discord.Color.teal())

    def generate_setup_game_mode_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        view.add_item(self.GameModeSelect(guild_id, "mode", 0, self)); view.add_item(self.GameDurationSelect(guild_id, "duration", 1, self)); view.add_item(self.BackButton("⬅ Back to Settings", guild_id, discord.ButtonStyle.secondary, 2, self))
        return view

    class GameModeSelect(ui.Select):
        def __init__(self, guild_id: str, select_type: str, row: int, cog: 'AdminCog'):
            options = [discord.SelectOption(label="Peaceful", description="Low degradation rates.", value="peaceful"), discord.SelectOption(label="Medium (Default)", description="Standard degradation rates.", value="medium"), discord.SelectOption(label="Hard", description="High degradation rates. More challenging.", value="hard")]
            super().__init__(placeholder="Choose a difficulty mode...", options=options, custom_id=f"select_gamemode_{guild_id}", row=row); self.guild_id = guild_id; self.cog = cog
        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            try:
                selected_mode = self.values[0]; state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()
                if state and (mode_data := self.cog.GAME_MODES.get(selected_mode)):
                    state.game_mode, state.game_tick_interval_minutes = selected_mode, mode_data["tick_interval_minutes"]
                    for key, value in mode_data["rates"].items(): setattr(state, f"degradation_rate_{key}", value)
                    db.commit()
                    embed = self.cog.generate_setup_game_mode_embed(); embed.description = f"✅ Difficulty set to **{selected_mode.capitalize()}**.\n{embed.description}"
                    await interaction.response.edit_message(embed=embed, view=self.cog.generate_setup_game_mode_view(self.guild_id))
            finally: db.close()

    class GameDurationSelect(ui.Select):
        def __init__(self, guild_id: str, select_type: str, row: int, cog: 'AdminCog'):
            options = [discord.SelectOption(label=data["label"], value=key) for key, data in AdminCog.GAME_DURATIONS.items()]
            super().__init__(placeholder="Choose the game duration...", options=options, custom_id=f"select_gameduration_{guild_id}", row=row); self.guild_id = guild_id; self.cog = cog
        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            try:
                selected_key = self.values[0]; state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()
                if state and (duration_data := self.cog.GAME_DURATIONS.get(selected_key)):
                    state.duration_key = selected_key; db.commit()
                    embed = self.cog.generate_setup_game_mode_embed(); embed.description = f"✅ Game duration set to **{duration_data['label']}**.\n{embed.description}"
                    await interaction.response.edit_message(embed=embed, view=self.cog.generate_setup_game_mode_view(self.guild_id))
            finally: db.close()

    class BackButton(ui.Button):
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle, row: int = 0, cog: 'AdminCog'=None):
            super().__init__(label=label, style=style, row=row); self.guild_id = guild_id; self.cog = cog
        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            try:
                state = db.query(ServerState).filter_by(guild_id=str(self.guild_id)).first()
                await interaction.response.edit_message(embed=self.cog.generate_config_menu_embed(state), view=self.cog.generate_config_menu_view(self.guild_id, interaction.guild))
            finally: db.close()

    class ConfigButton(ui.Button):
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle, row: int, cog: 'AdminCog'):
            super().__init__(label=label, style=style, row=row); self.guild_id = guild_id; self.label = label; self.cog = cog
        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            try:
                state = db.query(ServerState).filter_by(guild_id=str(self.guild_id)).first()
                if self.label == "🎮 Start/Reset Game":
                    if state:
                        state.game_started = not state.game_started; state.game_start_time = datetime.datetime.utcnow() if state.game_started else None
                        db.commit()
                        await interaction.response.edit_message(embed=self.cog.generate_config_menu_embed(state), view=self.cog.generate_config_menu_view(self.guild_id, interaction.guild))
                        await interaction.followup.send(f"The game has been {'started' if state.game_started else 'stopped/reset'}.", ephemeral=True)
                elif self.label == "📊 View Stats": await interaction.response.edit_message(embed=self.cog.generate_stats_embed(self.guild_id), view=self.cog.generate_stats_view(self.guild_id))
                elif self.label == "🔔 Notifications": await interaction.response.edit_message(embed=self.cog.generate_notifications_embed(self.guild_id), view=self.cog.generate_notifications_view(self.guild_id))
            finally: db.close()

    class GeneralConfigButton(ui.Button):
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle, row: int, cog: 'AdminCog'):
            super().__init__(label=label, style=style, row=row); self.guild_id = guild_id; self.cog = cog
        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            try:
                state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()
                await interaction.response.edit_message(embed=self.cog.generate_role_and_channel_config_embed(state), view=self.cog.generate_general_config_view(self.guild_id, interaction.guild))
            finally: db.close()

    def generate_role_and_channel_config_embed(self, state: ServerState) -> discord.Embed:
        embed = discord.Embed(title="⚙️ General Config (Roles & Channels)", description="Use the dropdowns to select roles and channels.", color=discord.Color.purple())
        current_admin_role = f"<@&{state.admin_role_id}>" if state.admin_role_id else "Not set"; current_notif_role = f"<@&{state.notification_role_id}>" if state.notification_role_id else "Not set"; current_game_channel = f"<#{state.game_channel_id}>" if state.game_channel_id else "Not set"
        embed.add_field(name="👑 Admin Role", value=current_admin_role, inline=False); embed.add_field(name="🔔 Notification Role", value=current_notif_role, inline=False); embed.add_field(name="🎮 Game Channel", value=current_game_channel, inline=False)
        return embed

    def generate_general_config_view(self, guild_id: str, guild: discord.Guild) -> discord.ui.View:
        view = discord.ui.View(timeout=180)
        role_options, role_id_mapping = self.create_options_and_mapping(guild.roles if guild else [], "role", guild)
        channel_options, channel_id_mapping = self.create_options_and_mapping([ch for ch in guild.channels if isinstance(ch, discord.TextChannel)] if guild else [], "channel", guild)
        view.add_item(PaginatedSelect(guild_id, "admin_role", role_options, role_id_mapping, 0, self))
        view.add_item(PaginatedSelect(guild_id, "notification_role", role_options, role_id_mapping, 0, self, row=1))
        view.add_item(PaginatedSelect(guild_id, "channel", channel_options, channel_id_mapping, 0, self, row=2))
        view.add_item(self.BackButton("⬅ Back to Settings", guild_id, discord.ButtonStyle.secondary, 3, self))
        return view

    # --- Classe de Menu pour la sélection des Rôles ---
    class RoleSelect(ui.Select):
        def __init__(self, guild_id: str, select_type: str, row: int, options: list[discord.SelectOption], id_mapping: dict, cog: 'AdminCog'): # Ajout de cog
            placeholder = f"Sélectionnez le rôle pour {'l\'admin' if select_type == 'admin_role' else 'les notifications'}..."
            placeholder = placeholder[:100] # Assurer que le placeholder ne dépasse pas 100 caractères
            
            # Il faut s'assurer que le nombre d'options ne dépasse pas 25.
            # Si c'est le cas, on doit soit tronquer, soit implémenter une pagination.
            # Ici, on suppose qu'il y a moins de 25 rôles.
            
            super().__init__(placeholder=placeholder, options=options[:MAX_OPTIONS_PER_PAGE], custom_id=f"select_role_{select_type}_{guild_id}", row=row)
            self.guild_id = guild_id
            self.select_type = select_type
            self.id_mapping = id_mapping 
            self.cog = cog # Stocker l'instance du cog

        async def callback(self, interaction: discord.Interaction):
            if not interaction.guild:
                await interaction.response.send_message("Erreur: Impossible de trouver le serveur courant pour cette action.", ephemeral=True)
                return

            if not self.values or self.values[0] in ["no_items", "error_guild"]:
                await interaction.response.send_message("Veuillez sélectionner un rôle valide.", ephemeral=True)
                return

            selected_short_id = self.values[0]
            selected_role_id = self.id_mapping.get(selected_short_id)

            if not selected_role_id:
                await interaction.response.send_message("Erreur: Impossible de récupérer l'ID du rôle.", ephemeral=True)
                return

            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()

            if state:
                if self.select_type == "admin_role":
                    state.admin_role_id = selected_role_id
                elif self.select_type == "notification_role":
                    state.notification_role_id = selected_role_id
                
                try:
                    db.commit()
                    db.refresh(state) 

                    # Rafraîchir la vue complète pour refléter le changement
                    await interaction.response.edit_message(
                        embed=self.cog.generate_role_and_channel_config_embed(state), # Utiliser self.cog
                        view=self.cog.generate_general_config_view(self.guild_id, interaction.guild) # Utiliser self.cog
                    )
                    await interaction.followup.send(f"Rôle pour {'l\'administration' if self.select_type == 'admin_role' else 'les notifications'} mis à jour.", ephemeral=True)
                except Exception as e:
                    db.rollback()
                    await interaction.response.send_message(f"Erreur lors de la sauvegarde : {e}", ephemeral=True)
            else:
                await interaction.response.send_message("Erreur: Impossible de trouver l'état du serveur pour sauvegarder la configuration.", ephemeral=True)
            
            db.close()

    # --- Classe pour la sélection des Salons avec Pagination ---
    class ChannelSelect(ui.Select):
        def __init__(self, guild_id: str, select_type: str, row: int, options: list[discord.SelectOption], id_mapping: dict, page: int = 0, cog: 'AdminCog'=None):
            self.guild_id = guild_id
            self.select_type = select_type
            self.id_mapping = id_mapping
            self.page = page
            self.cog = cog # Stocker l'instance du cog

            # Filtrer les options pour la page actuelle
            start_index = page * MAX_OPTIONS_PER_PAGE
            end_index = start_index + MAX_OPTIONS_PER_PAGE
            current_page_options = options[start_index:end_index]

            if not current_page_options:
                current_page_options.append(discord.SelectOption(label="Aucun salon sur cette page", value="no_channels", default=True))

            placeholder = f"Sélectionnez le salon pour le jeu (Page {page + 1})..."
            placeholder = placeholder[:100]
            # Le custom_id doit inclure la page pour être unique par page,
            # car chaque page aura son propre SelectMenu.
            super().__init__(placeholder=placeholder, options=current_page_options, custom_id=f"select_channel_{select_type}_{guild_id}_page{page}", row=row)

        async def callback(self, interaction: discord.Interaction):
            if not interaction.guild:
                await interaction.response.send_message("Erreur: Impossible de trouver le serveur courant pour cette action.", ephemeral=True)
                return

            if not self.values or self.values[0] in ["no_channels", "error_guild", "no_items"]:
                await interaction.response.send_message("Veuillez sélectionner un salon valide.", ephemeral=True)
                return

            selected_short_id = self.values[0]
            selected_channel_id = self.id_mapping.get(selected_short_id)

            if not selected_channel_id:
                await interaction.response.send_message("Erreur: Impossible de récupérer l'ID du salon.", ephemeral=True)
                return

            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()

            if state:
                if self.select_type == "game_channel":
                    state.game_channel_id = selected_channel_id
                
                try:
                    db.commit()
                    db.refresh(state)

                    # Rafraîchir la vue entière pour que le changement de page soit bien géré
                    # dans le cas où l'utilisateur change de page et sélectionne un salon.
                    # On utilise le cog pour générer la vue complète.
                    await interaction.response.edit_message(
                        embed=self.cog.generate_role_and_channel_config_embed(state), # Utiliser self.cog
                        view=self.cog.generate_general_config_view(self.guild_id, interaction.guild) # Utiliser self.cog
                    )
                    await interaction.followup.send(f"Salon de jeu mis à jour.", ephemeral=True)
                except Exception as e:
                    db.rollback()
                    await interaction.response.send_message(f"Erreur lors de la sauvegarde : {e}", ephemeral=True)
            else:
                await interaction.response.send_message("Erreur: Impossible de trouver l'état du serveur pour sauvegarder la configuration.", ephemeral=True)
            
            db.close()

    # --- Classe pour gérer la vue paginée des salons ---
    class PaginatedViewManager(ui.View):
        def __init__(self, guild_id: str, all_options: list[discord.SelectOption], id_mapping: dict, select_type: str, initial_page: int = 0, cog: 'AdminCog'=None):
            super().__init__(timeout=180)
            self.guild_id = guild_id
            self.all_options = all_options
            self.id_mapping = id_mapping
            self.select_type = select_type
            self.current_page = initial_page
            self.cog = cog

            self.total_pages = max(1, math.ceil(len(self.all_options) / MAX_OPTIONS_PER_PAGE))

            # Création du menu
            self.selection_menu = self.create_select()
            self.add_item(self.selection_menu)

            # Créer la pagination uniquement si plus d'une page
            if self.total_pages > 1:
                self.prev_button = ui.Button(label="◀", style=discord.ButtonStyle.secondary)
                self.page_button = ui.Button(label=f"{self.current_page+1}/{self.total_pages}", style=discord.ButtonStyle.gray, disabled=True)
                self.next_button = ui.Button(label="▶", style=discord.ButtonStyle.secondary)

                self.prev_button.callback = self.prev_page
                self.next_button.callback = self.next_page

                self.add_item(self.prev_button)
                self.add_item(self.page_button)
                self.add_item(self.next_button)

        def create_select(self):
            start_index = self.current_page * MAX_OPTIONS_PER_PAGE
            end_index = start_index + MAX_OPTIONS_PER_PAGE
            current_page_options = self.all_options[start_index:end_index]

            if not current_page_options:
                current_page_options = [discord.SelectOption(label="Aucun élément", value="no_items", default=True)]

            placeholder = f"Sélectionnez {('un rôle' if 'role' in self.select_type else 'un salon')} (Page {self.current_page+1}/{self.total_pages})"
            return (AdminCog.RoleSelect if 'role' in self.select_type else AdminCog.ChannelSelect)(
                guild_id=self.guild_id,
                select_type=self.select_type,
                row=0,
                options=current_page_options,
                id_mapping=self.id_mapping,
                cog=self.cog
            )

        async def prev_page(self, interaction: discord.Interaction):
            if self.current_page > 0:
                self.current_page -= 1
                await self.update_page(interaction)

        async def next_page(self, interaction: discord.Interaction):
            if self.current_page < self.total_pages - 1:
                self.current_page += 1
                await self.update_page(interaction)

        async def update_page(self, interaction: discord.Interaction):
            # Rebuild menu
            self.remove_item(self.selection_menu)
            self.selection_menu = self.create_select()
            self.add_item(self.selection_menu)

            # Update page button
            if self.total_pages > 1:
                self.page_button.label = f"{self.current_page+1}/{self.total_pages}"
                self.prev_button.disabled = self.current_page == 0
                self.next_button.disabled = self.current_page >= self.total_pages-1

            await interaction.response.edit_message(view=self)


    # --- Méthodes pour les autres configurations (Statistiques, Notifications, Avancées) ---
    # ... (reste des méthodes : generate_stats_embed, generate_stats_view, etc.) ...
    def generate_stats_embed(self, guild_id: str) -> discord.Embed: return discord.Embed(title="📊 Server Statistics", description="This feature is under development.", color=discord.Color.purple())
    def generate_stats_view(self, guild_id: str) -> discord.ui.View: view = discord.ui.View(timeout=None); view.add_item(self.BackButton("⬅ Back to Settings", guild_id, discord.ButtonStyle.secondary, 3, self)); return view

    # Dans admin.py, dans AdminCog
        # --- Méthodes pour les configurations spécifiques (Rôle Admin, Salon, Rôle Notif) ---
    
    # ... (generate_role_and_channel_config_embed, etc.) ...

    # --- L'EMBED POUR LES PARAMÈTRES DE NOTIFICATIONS ---
    def generate_notifications_embed(self, guild_id: str) -> discord.Embed:
        db = SessionLocal()
        try:
            state = db.query(ServerState).filter_by(guild_id=guild_id).first()
            if not state: return discord.Embed(title="🔔 Notification Settings", description="Could not load server configuration.", color=discord.Color.red())
            embed = discord.Embed(title="🔔 Notification Settings", color=discord.Color.green())
            notif_role_mention = f"<@&{state.notification_role_id}>" if state.notification_role_id else "Not set"
            embed.add_field(name="📍 General Notification Role", value=notif_role_mention, inline=False)
            embed.add_field(name="🚨 Specific Alert Roles", value=(f"📉 Low Vitals: {f'<@&{state.notify_vital_low_role_id}>' if state.notify_vital_low_role_id else 'Not set'}\n" f"🚨 Critical: {f'<@&{state.notify_critical_role_id}>' if state.notify_critical_role_id else 'Not set'}\n" f"🚬 Cravings: {f'<@&{state.notify_envie_fumer_role_id}>' if state.notify_envie_fumer_role_id else 'Not set'}\n" f"💬 Friend/Quiz Msg: {f'<@&{state.notify_friend_message_role_id}>' if state.notify_friend_message_role_id else 'Not set'}\n" f"🛒 Shop Promos: {f'<@&{state.notify_shop_promo_role_id}>' if state.notify_shop_promo_role_id else 'Not set'}"), inline=False)
            embed.set_footer(text="Use the buttons below to adjust preferences.")
            return embed
        finally: db.close()

    class NotificationRoleSelect(ui.Select):
        def __init__(self, guild_id: str, select_type: str, row: int, options: list[discord.SelectOption], id_mapping: dict, cog: 'AdminCog'):
            placeholder = f"Select role for: {select_type.replace('_role_id', '').replace('_', ' ').title()}"; super().__init__(placeholder=placeholder[:100], options=options[:MAX_OPTIONS_PER_PAGE], custom_id=f"select_notif_role_{select_type}_{guild_id}", row=row)
            self.guild_id, self.select_type, self.id_mapping, self.cog = guild_id, select_type, id_mapping, cog
        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            try:
                selected_short_id = self.values[0]
                if selected_short_id in ["no_items", "error_guild"]: await interaction.response.send_message("Please select a valid role.", ephemeral=True); return
                selected_role_id = self.id_mapping.get(selected_short_id)
                if not selected_role_id: await interaction.response.send_message("Error retrieving role ID.", ephemeral=True); return
                state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()
                if state:
                    setattr(state, self.select_type, selected_role_id); db.commit(); db.refresh(state)
                    await interaction.response.edit_message(embed=self.cog.generate_notifications_embed(self.guild_id), view=self.cog.generate_notifications_view(self.guild_id))
                    await interaction.followup.send(f"Notification role for '{self.select_type.replace('_role_id', '').replace('_', ' ').title()}' updated.", ephemeral=True)
            except Exception as e:
                logger.error(f"Error saving notification role {self.select_type}: {e}", exc_info=True); db.rollback()
                await interaction.response.send_message(f"Error saving: {e}", ephemeral=True)
            finally: db.close()

    def generate_notifications_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=180)
        db = SessionLocal()
        try:
            state = db.query(ServerState).filter_by(guild_id=guild_id).first()
            if not state:
                view.add_item(self.BackButton("⬅ Back", guild_id, discord.ButtonStyle.secondary, row=0, cog=self)); return view
            view.add_item(self.NotificationToggle("🔴 Low Vitals", "notify_on_low_vital_stat", guild_id, discord.ButtonStyle.danger if state.notify_on_low_vital_stat else discord.ButtonStyle.secondary, self, 0))
            view.add_item(self.NotificationToggle("🔴 Critical Event", "notify_on_critical_event", guild_id, discord.ButtonStyle.danger if state.notify_on_critical_event else discord.ButtonStyle.secondary, self, 1))
            view.add_item(self.NotificationToggle("🚬 Cravings", "notify_on_envie_fumer", guild_id, discord.ButtonStyle.success if state.notify_on_envie_fumer else discord.ButtonStyle.secondary, self, 1))
            view.add_item(self.NotificationToggle("💬 Friend/Quiz", "notify_on_friend_message", guild_id, discord.ButtonStyle.primary if state.notify_on_friend_message else discord.ButtonStyle.secondary, self, 2))
            view.add_item(self.NotificationToggle("💛 Shop Promo", "notify_on_shop_promo", guild_id, discord.ButtonStyle.primary if state.notify_on_shop_promo else discord.ButtonStyle.secondary, self, 2))
            guild = self.bot.get_guild(int(guild_id))
            if guild:
                role_options, role_id_mapping = self.create_options_and_mapping(guild.roles, "role", guild)
                view.add_item(PaginatedSelect(guild_id, "notification_role", role_options, role_id_mapping, 0, self, row=3))
            view.add_item(self.BackButton("⬅ Back", guild_id, discord.ButtonStyle.secondary, row=4, cog=self))
            return view
        finally: db.close()

    class NotificationToggle(ui.Button):
        def __init__(self, label: str, toggle_key: str, guild_id: str, style: discord.ButtonStyle, cog: 'AdminCog', row: int):
            super().__init__(label=label, style=style, row=row); self.toggle_key = toggle_key; self.guild_id = guild_id; self.cog = cog
        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            try:
                state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()
                if not state: await interaction.response.send_message("Error: Server state not found.", ephemeral=True); return
                if state.game_started: await interaction.response.send_message("Cannot change notification settings while a game is in progress.", ephemeral=True); return
                new_value = not getattr(state, self.toggle_key); setattr(state, self.toggle_key, new_value)
                db.commit(); db.refresh(state)
                await interaction.response.edit_message(embed=self.cog.generate_notifications_embed(self.guild_id), view=self.cog.generate_notifications_view(self.guild_id))
                await interaction.followup.send(f"Notifications for '{self.toggle_key.replace('_', ' ').title()}' set to {'Enabled' if new_value else 'Disabled'}.", ephemeral=True)
            finally: db.close()

class PaginatedSelect(discord.ui.Select):
    def __init__(self, guild_id: str, select_type: str, options: list[discord.SelectOption], id_mapping: dict, page: int, cog: 'AdminCog', row: int = 0):
        self.guild_id, self.select_type, self.id_mapping, self.page, self.cog = guild_id, select_type, id_mapping, page, cog
        self.all_options = options; self.items_per_page = 24; self.total_pages = max(1, math.ceil(len(options) / self.items_per_page))
        start, end = page * self.items_per_page, (page + 1) * self.items_per_page
        page_options = options[start:end]
        if self.total_pages > 1:
            if page < self.total_pages - 1: page_options.append(discord.SelectOption(label=f"… Next Page ({page+2}/{self.total_pages})", value="__next_page__"))
            else: page_options.append(discord.SelectOption(label=f"↩ Back to Page 1", value="__first_page__"))
        placeholder = f"Select a {'role' if 'role' in select_type else 'channel'} (Page {page+1}/{self.total_pages})"
        super().__init__(placeholder=placeholder, options=page_options, custom_id=f"paginated_{select_type}_{guild_id}_p{page}", row=row)
    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        if selected in ["__next_page__", "__first_page__"]:
            self.page = self.page + 1 if selected == "__next_page__" else 0
            # Rebuild the entire parent view to replace the select
            await interaction.response.edit_message(view=self.cog.generate_general_config_view(self.guild_id, interaction.guild))
            return
        db = SessionLocal()
        try:
            selected_item_id = self.id_mapping.get(selected)
            if not selected_item_id: await interaction.response.send_message("Error: item not found.", ephemeral=True); return
            state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()
            if state:
                if self.select_type == "admin_role": state.admin_role_id = selected_item_id
                elif self.select_type == "notification_role": state.notification_role_id = selected_item_id
                elif self.select_type == "channel": state.game_channel_id = selected_item_id
                db.commit()
            await interaction.response.edit_message(view=self.cog.generate_general_config_view(self.guild_id, interaction.guild))
            await interaction.followup.send("✅ Selection updated.", ephemeral=True)
        finally: db.close()

async def setup(bot):
    await bot.add_cog(AdminCog(bot))