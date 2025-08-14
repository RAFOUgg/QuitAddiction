# --- cogs/admin.py (CORRECTED) ---

import discord
from discord.ext import commands
from discord.errors import Forbidden, NotFound
from discord import app_commands, ui
import hashlib
import datetime
import math
from typing import List, Tuple, Dict, Literal
import os
import traceback

# --- CORRECT: Centralized Imports ---
from db.database import SessionLocal
from db.models import ServerState, PlayerProfile
from utils.logger import get_logger
from utils.embed_builder import create_styled_embed
from cogs.main_embed import DashboardView

# --- Setup Logger for this Cog ---
logger = get_logger(__name__)

# --- Constants ---
MAX_OPTIONS_PER_PAGE = 25
PAGINATED_SELECT_ITEMS_PER_PAGE = 24

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO_OWNER = os.getenv("GITHUB_REPO_OWNER")
GITHUB_REPO_NAME = os.getenv("GITHUB_REPO_NAME")


# --- NOUVELLE VUE DE PAGINATION (APPROCHE CORRECTE) ---

class RoleSelect(ui.Select):
    def __init__(self, guild_id: str, setting_key: str, id_mapping: dict, cog: 'AdminCog'):
        self.guild_id = guild_id
        self.setting_key = setting_key # Ex: "admin_role_id", "notify_craving_role_id"
        self.id_mapping = id_mapping
        self.cog = cog
        super().__init__(placeholder="Sélectionnez un rôle...", row=0)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        selected_hash = self.values[0]
        selected_id = self.id_mapping.get(selected_hash)

        if not selected_id:
            await interaction.followup.send("Erreur: Rôle introuvable.", ephemeral=True)
            return

        db = SessionLocal()
        try:
            state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()
            if not state:
                await interaction.followup.send("Erreur: Configuration du serveur introuvable.", ephemeral=True)
                return

            setattr(state, self.setting_key, selected_id)
            db.commit()
            
            await interaction.followup.send(f"✅ Rôle mis à jour !", ephemeral=True)
            
            db.refresh(state)
            new_embed = self.cog.generate_notifications_config_embed(state)
            new_view = self.cog.generate_notifications_config_view(self.guild_id)
            await interaction.edit_original_response(embed=new_embed, view=new_view)
        except Exception as e:
            db.rollback()
            logger.error(f"Erreur de mise à jour du rôle: {e}", exc_info=True)
        finally:
            db.close()


class PaginatedViewManager(ui.View):
    """ Une vue qui gère un menu déroulant paginé avec des boutons Précédent/Suivant. """
    def __init__(self, guild_id: str, all_options: list[discord.SelectOption], id_mapping: dict, select_type: Literal['admin_role', 'notification_role', 'game_channel'], cog: 'AdminCog'):
        super().__init__(timeout=180)
        self.guild_id = guild_id
        self.all_options = all_options
        self.id_mapping = id_mapping
        self.select_type = select_type
        self.cog = cog
        self.current_page = 0
        self.total_pages = max(1, math.ceil(len(self.all_options) / PAGINATED_SELECT_ITEMS_PER_PAGE))

        self.select_menu = None
        self.update_components()

    def update_components(self):
        self.clear_items()
        
        start = self.current_page * PAGINATED_SELECT_ITEMS_PER_PAGE
        end = start + PAGINATED_SELECT_ITEMS_PER_PAGE
        page_options = self.all_options[start:end]

        if not page_options:
            page_options = [discord.SelectOption(label="No items on this page", value="no_items", default=True)]

        # Note: This is a generic ItemSelect which needs to be defined or replaced.
        # Assuming you'll replace `ItemSelect` with a concrete implementation like `RoleSelect` or a generic handler.
        # For now, let's create a generic select that will need a handler.
        # This part of the code (`ItemSelect`) is not fully defined in the provided file, so I will assume a generic select for now.
        # Let's assume `ItemSelect` is intended to be a general version of `RoleSelect`
        # and create a generic version.
        
        class ItemSelect(ui.Select):
             # A generic select for the paginator
            def __init__(self, guild_id: str, select_type: str, id_mapping: dict, cog: 'AdminCog'):
                self.guild_id = guild_id
                self.select_type = select_type
                self.id_mapping = id_mapping
                self.cog = cog
                super().__init__(placeholder="Select an item...", row=0)

            async def callback(self, interaction: discord.Interaction):
                await interaction.response.defer()
                selected_hash = self.values[0]
                selected_id = self.id_mapping.get(selected_hash)
                
                if not selected_id:
                    await interaction.followup.send("Error: Item not found.", ephemeral=True)
                    return
                
                db = SessionLocal()
                try:
                    state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()
                    if not state:
                        await interaction.followup.send("Error: Server config not found.", ephemeral=True)
                        return
                    
                    db_field_map = {
                        'admin_role': 'admin_role_id',
                        'notification_role': 'notification_role_id',
                        'game_channel': 'game_channel_id'
                    }
                    field_to_update = db_field_map.get(self.select_type)
                    if not field_to_update:
                        await interaction.followup.send(f"Error: Unknown select type '{self.select_type}'.", ephemeral=True)
                        return

                    setattr(state, field_to_update, selected_id)
                    db.commit()
                    db.refresh(state)

                    await interaction.followup.send("✅ Setting updated!", ephemeral=True)

                    # Return to the correct config menu
                    new_embed = self.cog.generate_role_and_channel_config_embed(state)
                    new_view = self.cog.generate_general_config_view(self.guild_id, interaction.guild)
                    await interaction.edit_original_response(embed=new_embed, view=new_view)
                except Exception as e:
                    db.rollback()
                    logger.error(f"Error updating paginated selection: {e}", exc_info=True)
                finally:
                    db.close()


        self.select_menu = ItemSelect(self.guild_id, self.select_type, self.id_mapping, self.cog)
        self.select_menu.options = page_options
        self.select_menu.placeholder = f"Select... (Page {self.current_page + 1}/{self.total_pages})"
        self.add_item(self.select_menu)

        self.prev_button = ui.Button(label="Prev", emoji="◀️", style=discord.ButtonStyle.secondary, row=1, disabled=(self.current_page == 0))
        self.page_indicator = ui.Button(label=f"{self.current_page + 1}/{self.total_pages}", style=discord.ButtonStyle.grey, disabled=True, row=1)
        self.next_button = ui.Button(label="Next", emoji="▶️", style=discord.ButtonStyle.secondary, row=1, disabled=(self.current_page >= self.total_pages - 1))
        
        self.prev_button.callback = self.prev_page
        self.next_button.callback = self.next_page
        
        self.add_item(self.prev_button)
        self.add_item(self.page_indicator)
        self.add_item(self.next_button)

        back_button = self.cog.BackButton("Back to Config", self.guild_id, discord.ButtonStyle.red, row=2, cog=self.cog)
        self.add_item(back_button)


    async def prev_page(self, interaction: discord.Interaction):
        self.current_page -= 1
        self.update_components()
        await interaction.response.edit_message(view=self)

    async def next_page(self, interaction: discord.Interaction):
        self.current_page += 1
        self.update_components()
        await interaction.response.edit_message(view=self)

class StopGameConfirmationModal(ui.Modal, title="Confirm Game Stop"):
    def __init__(self, guild_id: str, cog: 'AdminCog'):
        super().__init__()
        self.guild_id = guild_id
        self.cog = cog

    confirmation_input = ui.TextInput(
        label='Type "STOP" to confirm',
        placeholder="This action will end the current game for all players.",
        style=discord.TextStyle.short,
        required=True,
        max_length=4,
        min_length=4
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        if self.confirmation_input.value.upper() != "STOP":
            await interaction.response.send_message("Confirmation failed. The game was not stopped.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        
        db = SessionLocal()
        try:
            state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()
            if not state or not state.game_started:
                await interaction.followup.send("There is no game currently running to stop.", ephemeral=True)
                return

            state.game_started = False
            state.game_start_time = None
            
            game_message_id_to_clear = state.game_message_id
            game_channel_id_to_use = state.game_channel_id
            state.game_message_id = None
            
            db.commit()
            db.refresh(state)

            # Update the admin panel from the original interaction that opened the modal
            await interaction.edit_original_response(
                embed=self.cog.generate_config_menu_embed(state),
                view=self.cog.generate_config_menu_view(self.guild_id, interaction.guild, state)
            )

            if game_message_id_to_clear and game_channel_id_to_use:
                try:
                    game_channel = await self.cog.bot.fetch_channel(game_channel_id_to_use)
                    game_message = await game_channel.fetch_message(game_message_id_to_clear)
                    
                    game_over_embed = discord.Embed(
                        title="🏁 Partie Terminée",
                        description="Cette session de jeu est terminée. Un administrateur peut en lancer une nouvelle via la commande `/config`.",
                        color=discord.Color.dark_grey()
                    )
                    await game_message.edit(embed=game_over_embed, view=None)
                except (NotFound, Forbidden):
                    logger.warning(f"Impossible de trouver ou modifier le message de jeu {game_message_id_to_clear} dans le salon {game_channel_id_to_use}")
                except Exception as e:
                    logger.error(f"Erreur lors de la modification du message de fin de jeu: {e}", exc_info=True)

            await interaction.followup.send("✅ The game has been successfully stopped.", ephemeral=True)

        except Exception as e:
            db.rollback()
            logger.error(f"Error stopping the game: {e}", exc_info=True)
            await interaction.followup.send(f"A database error occurred: {e}", ephemeral=True)
        finally:
            db.close()


class AdminCog(commands.Cog):
    """Gestion des configurations du bot et du jeu pour le serveur."""
    def __init__(self, bot):
        self.bot = bot
    
    # Step 1: Define base degradation for a standard 24-hour game day.
    BASE_DAILY_RATES = {
        "hunger": 150,      # Approx. 3 meals (3 * 50)
        "thirst": 200,      # Approx. 4 water bottles (4 * 60, rounded down)
        "bladder": 120,     # Fills up reasonably
        "stress": 40,       # Base stress from daily life
        "boredom": 200,     # Needs activities to be kept down
        "hygiene": 100,     # Needs one shower per day
    }

    # Step 2: Define difficulty multipliers.
    DIFFICULTY_MULTIPLIERS = {
        "peaceful": 0.75,
        "medium": 1.0,
        "hard": 1.5,
    }

    # Step 3: Define duration settings (how long a game day is in real minutes).
    DURATION_SETTINGS = {
        "test_day": {"minutes_per_day": 24,     "label": "Test (Jour = 24 mins)"},
        "day":      {"minutes_per_day": 1440,   "label": "Jour (Jour = 24h)"},
        "short":    {"minutes_per_day": 10080,  "label": "Court (Jour = 7 jours)"},
        "medium":   {"minutes_per_day": 20160,  "label": "Moyen (Jour = 14 jours)"},
        "long":     {"minutes_per_day": 43200,  "label": "Long (Jour = 30 jours)"}, # Adjusted 72 to 30 for sanity
    }
    MAX_OPTION_LENGTH = 100
    MIN_OPTION_LENGTH = 1
    # --- FINALIZED: Test day settings for 24 min duration ---
    TEST_DURATION_MINUTES = 24 
    TEST_RATE_MULTIPLIER = 60 # (24h * 60min) / 24min = 60. Rates are 60x faster.

    def _update_game_parameters(self, state: ServerState):
        """Recalculates and sets game parameters based on stored mode and duration."""
        difficulty = state.game_mode or "medium"
        duration_key = state.duration_key or "day"

        multiplier = self.DIFFICULTY_MULTIPLIERS.get(difficulty, 1.0)
        duration_setting = self.DURATION_SETTINGS.get(duration_key, self.DURATION_SETTINGS["day"])
        
        # Set final degradation rates
        for rate_name, base_value in self.BASE_DAILY_RATES.items():
            final_rate = base_value * multiplier
            setattr(state, f"degradation_rate_{rate_name}", final_rate)
            
        # Set game day duration
        state.game_minutes_per_day = duration_setting["minutes_per_day"]
        
        logger.info(f"Game parameters updated for guild {state.guild_id}: Difficulty={difficulty}, Duration={duration_key}")

    @app_commands.command(name="config", description="Configure les paramètres du bot et du jeu pour le serveur.")
    @app_commands.default_permissions(administrator=True)
    async def config(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild_id_str = str(interaction.guild.id)
        db = SessionLocal()
        try:
            state = db.query(ServerState).filter_by(guild_id=guild_id_str).first()
            if not state:
                state = ServerState(guild_id=guild_id_str)
                # Set default values for the first time
                self._update_game_parameters(state)
                db.add(state)
                db.commit()
                db.refresh(state)

            await interaction.followup.send(
                embed=self.generate_config_menu_embed(state),
                view=self.generate_config_menu_view(guild_id_str, interaction.guild, state),
            )
        except Exception as e:
            logger.error(f"Error in /config command: {e}", exc_info=True)
            if not interaction.is_expired():
                await interaction.followup.send("An error occurred while loading the configuration.", ephemeral=True)
        finally:
            db.close()

    # --- Classes de Boutons et Menus ---
    class NotificationsConfigButton(ui.Button):
        def __init__(self, guild_id: str, cog: 'AdminCog'):
            super().__init__(label="Notifications", emoji="🔔", style=discord.ButtonStyle.primary, row=1)
            self.guild_id = guild_id
            self.cog = cog
            
        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            try:
                state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()
                await interaction.response.edit_message(
                    embed=self.cog.generate_notifications_config_embed(state),
                    view=self.cog.generate_notifications_config_view(self.guild_id)
                )
            finally:
                db.close()

    def generate_notifications_config_embed(self, state: ServerState) -> discord.Embed:
        embed = discord.Embed(title="🔔 Configuration des Rôles de Notification", description="Configurez quel rôle sera notifié pour chaque type d'événement.", color=discord.Color.gold())
        
        roles = {
            "Général": state.notification_role_id,
            "Vitals Faibles": state.notify_vital_low_role_id,
            "Événement Critique": state.notify_critical_role_id,
            "Manque / Envies": state.notify_craving_role_id,
            "Message Ami": state.notify_friend_message_role_id,
            "Promotion Boutique": state.notify_shop_promo_role_id
        }
        
        value = "\n".join([f"**{name}:** {f'<@&{role_id}>' if role_id else 'Non défini'}" for name, role_id in roles.items()])
        embed.add_field(name="Rôles Actuels", value=value)
        embed.set_footer(text="Utilisez le menu pour changer un rôle, ou le bouton vert pour un rôle unique.")
        return embed

    # Le menu déroulant pour choisir quel rôle configurer
    class NotificationRoleTypeSelect(ui.Select):
        def __init__(self, guild_id: str, cog: 'AdminCog'):
            self.guild_id = guild_id
            self.cog = cog
            options = [
                discord.SelectOption(label="Rôle de notification général", value="notification_role_id"),
                discord.SelectOption(label="Rôle pour Vitals Faibles", value="notify_vital_low_role_id"),
                discord.SelectOption(label="Rôle pour Événement Critique", value="notify_critical_role_id"),
                discord.SelectOption(label="Rôle pour Manque / Envies", value="notify_craving_role_id"),
                discord.SelectOption(label="Rôle pour Message Ami", value="notify_friend_message_role_id"),
                discord.SelectOption(label="Rôle pour Promotion Boutique", value="notify_shop_promo_role_id"),
            ]
            # --- CORRECTION 1: Ajout de self.options_map ---
            # Cette variable était manquante et provoquait une erreur dans le callback.
            self.options_map = {opt.value: opt.label for opt in options}
            super().__init__(placeholder="Choisir le type de notification à configurer...", options=options)

        async def callback(self, interaction: discord.Interaction):
            setting_key = self.values[0]
            db = SessionLocal()
            try:
                state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()
                all_roles = interaction.guild.roles
                options, id_mapping = self.cog.create_options_and_mapping(all_roles, "role", interaction.guild)
                view = ui.View()
                select_menu = RoleSelect(self.guild_id, setting_key, id_mapping, self.cog)
                
                # S'il y a trop d'options, nous devrons utiliser la pagination.
                # Pour l'instant, limitons à 25 pour un seul menu déroulant.
                select_menu.options = options[:25] 
                view.add_item(select_menu)
                view.add_item(self.cog.BackButton("Retour", self.guild_id, discord.ButtonStyle.secondary, 1, self.cog))

                # --- CORRECTION 1 (suite): Utilisation de la variable corrigée ---
                # `self.options_map` est maintenant défini et peut être utilisé ici sans erreur.
                await interaction.response.edit_message(content=f"Sélectionnez le rôle pour : **{self.options_map[setting_key]}**", embed=None, view=view)
            
            except Exception as e:
                logger.error(f"Erreur dans NotificationRoleTypeSelect: {e}", exc_info=True)
            finally:
                db.close()

    class SetAllNotificationsRoleButton(ui.Button):
        def __init__(self, guild_id: str, cog: 'AdminCog'):
            super().__init__(label="Définir un Rôle pour Tout", style=discord.ButtonStyle.success, emoji="👑", row=1)
            self.guild_id = guild_id
            self.cog = cog
        
        async def callback(self, interaction: discord.Interaction):
            all_roles = interaction.guild.roles
            options, id_mapping = self.cog.create_options_and_mapping(all_roles, "role", interaction.guild)
            
            view = ui.View()
            view.add_item(SetAllNotificationsRole(self.guild_id, id_mapping, self.cog, options))
            view.add_item(self.cog.BackButton("Retour aux notifications", self.guild_id, discord.ButtonStyle.secondary, 1, self.cog, target_menu="notifications_config"))
            
            embed = discord.Embed(
                title="👑 Définir un rôle unique",
                description="Le rôle que vous sélectionnerez ci-dessous sera mentionné pour **toutes** les notifications du bot.",
                color=discord.Color.green()
            )
            await interaction.response.edit_message(embed=embed, view=view, content=None)

    def generate_notifications_config_view(self, guild_id: str) -> ui.View:
        view = ui.View(timeout=180)
        view.add_item(self.NotificationRoleTypeSelect(guild_id, self))
        view.add_item(self.SetAllNotificationsRoleButton(guild_id, self))
        view.add_item(self.BackButton("Retour au menu principal", guild_id, discord.ButtonStyle.red, 2, self))
        return view
        
    class ProjectStatsButton(ui.Button):
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle, row: int, cog: 'AdminCog'):
            super().__init__(label=label, style=style, row=row, emoji="📈")
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
                if "error" in commit_data: await interaction.followup.send(f"❌ GitHub Error: {commit_data['error']}", ephemeral=True); return
                if "error" in loc_data: await interaction.followup.send(f"❌ Local Error: {loc_data['error']}", ephemeral=True); return
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

    def generate_config_menu_view(self, guild_id: str, guild: discord.Guild, state: ServerState) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        is_game_running = state.game_started if state else False

        if is_game_running:
            start_stop_label = "Stop Game"
            start_stop_emoji = "⏹️"
            start_stop_style = discord.ButtonStyle.danger
        else:
            start_stop_label = "Start Game"
            start_stop_emoji = "▶️"
            start_stop_style = discord.ButtonStyle.success

        view.add_item(self.SetupGameModeButton("Mode & Duration", guild_id, discord.ButtonStyle.primary, row=0, cog=self, disabled=is_game_running))
        view.add_item(self.ConfigButton(start_stop_label, start_stop_emoji, guild_id, start_stop_style, row=0, cog=self))
        view.add_item(self.GeneralConfigButton("Roles & Channels", guild_id, discord.ButtonStyle.primary, row=0, cog=self, disabled=is_game_running))
        view.add_item(self.ConfigButton("Notifications", "🔔", guild_id, discord.ButtonStyle.primary, row=1, cog=self))
        view.add_item(self.ConfigButton("View Stats", "📊", guild_id, discord.ButtonStyle.primary, row=1, cog=self))
        view.add_item(self.ProjectStatsButton("Project Stats", guild_id, discord.ButtonStyle.secondary, row=1, cog=self))
        return view

    def create_options_and_mapping(self, items: list, item_type: str, guild: discord.Guild | None) -> Tuple[List[discord.SelectOption], Dict[str, str]]:
        options, id_mapping = [], {}
        if not guild: return [discord.SelectOption(label="Server Error", value="error_guild", default=True)], {}
        try:
            if item_type == "role": sorted_items = sorted(items, key=lambda x: x.position, reverse=True)
            elif item_type == "channel": sorted_items = sorted(items, key=lambda x: (getattr(x, 'category_id', float('inf')), x.position))
            else: sorted_items = items
        except Exception as e: logger.error(f"Error sorting {item_type}s: {e}"); sorted_items = items
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
            hashed_id = hashlib.sha256(item_id.encode()).hexdigest()[:25]
            options.append(discord.SelectOption(label=label, value=hashed_id, description=f"ID: {item_id}"))
            id_mapping[hashed_id] = item_id
        if not options: options.append(discord.SelectOption(label="No items found", value="no_items", default=True))
        return options, id_mapping

    def generate_config_menu_embed(self, state: ServerState) -> discord.Embed:
        embed = discord.Embed(title="⚙️ Bot & Game Configuration", description="Use the buttons below to adjust server settings.", color=discord.Color.blue())
        embed.add_field(name="▶️ **General Status**", value=f"**Game:** `{'In Progress' if state.game_started else 'Not Started'}`\n**Mode:** `{state.game_mode.capitalize() if state.game_mode else 'Medium (Default)'}`\n**Duration:** `{self.GAME_DURATIONS.get(state.duration_key, {}).get('label', 'Medium (31 jours)')}`", inline=False)
        admin_role, notif_role, game_channel = (f"<@&{state.admin_role_id}>" if state.admin_role_id else "Not set"), (f"<@&{state.notification_role_id}>" if state.notification_role_id else "Not set"), (f"<#{state.game_channel_id}>" if state.game_channel_id else "Not set")
        embed.add_field(name="📍 **Server Config**", value=f"**Admin Role:** {admin_role}\n**Notification Role:** {notif_role}\n**Game Channel:** {game_channel}", inline=False)
        embed.add_field(name="⏱️ **Game Parameters**", value=f"**Tick Interval (min):** `{state.game_tick_interval_minutes or 30}`", inline=False)
        embed.add_field(name="📉 **Degradation Rates / Tick**", value=f"**Hunger:** `{state.degradation_rate_hunger:.1f}` | **Thirst:** `{state.degradation_rate_thirst:.1f}` | **Bladder:** `{state.degradation_rate_bladder:.1f}`\n**Energy:** `{state.degradation_rate_energy:.1f}` | **Stress:** `{state.degradation_rate_stress:.1f}` | **Boredom:** `{state.degradation_rate_boredom:.1f}` | **Hygiene:** `{state.degradation_rate_hygiene:.1f}`", inline=False)
        embed.set_footer(text="Use the buttons below to navigate and modify settings.")
        return embed


    # --- Mode & Duration Section ---
    class ModeAndDurationButton(ui.Button):
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle, row: int, cog: 'AdminCog', disabled: bool = False):
            super().__init__(label=label, style=style, row=row, disabled=disabled, emoji="🕹️")
            self.guild_id = guild_id
            self.cog = cog
        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            try:
                state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()
                await interaction.response.edit_message(
                    embed=self.cog.generate_mode_duration_embed(state), 
                    view=self.cog.generate_mode_duration_view(self.guild_id, state)
                )
            finally:
                db.close()
    
    def generate_mode_duration_embed(self, state: ServerState) -> discord.Embed:
        embed = discord.Embed(title="🎮 Difficulté & Durée", description="Configurez séparément la difficulté du jeu (vitesse des besoins) et la durée (échelle de temps).", color=discord.Color.teal())
        
        difficulty = state.game_mode or "medium"
        duration_key = state.duration_key or "day"
        
        embed.add_field(name="Difficulté Actuelle", value=f"`{difficulty.capitalize()}` (Multiplicateur: x{self.DIFFICULTY_MULTIPLIERS.get(difficulty, 1.0)})", inline=False)
        embed.add_field(name="Durée Actuelle", value=f"`{self.DURATION_SETTINGS.get(duration_key, {}).get('label')}`", inline=False)
        
        return embed

    def generate_mode_duration_view(self, guild_id: str, state: ServerState) -> discord.ui.View:
        view = discord.ui.View(timeout=180)
        view.add_item(self.GameDifficultySelect(guild_id, self, state.game_mode))
        view.add_item(self.GameDurationSelect(guild_id, self, state.duration_key))
        view.add_item(self.BackButton("Retour aux Paramètres", guild_id, discord.ButtonStyle.secondary, 2, self))
        return view

    class GameDifficultySelect(ui.Select):
        def __init__(self, guild_id: str, cog: 'AdminCog', current_difficulty: str):
            options = [discord.SelectOption(label=f"{key.capitalize()}", value=key, default=(key == current_difficulty)) for key in self.DIFFICULTY_MULTIPLIERS.keys()]
            super().__init__(placeholder="Choisissez une difficulté...", options=options, row=0)
            self.guild_id = guild_id
            self.cog = cog

        async def callback(self, interaction: discord.Interaction):
            await interaction.response.defer()
            selected_difficulty = self.values[0]
            db = SessionLocal()
            try:
                state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()
                state.game_mode = selected_difficulty
                self.cog._update_game_parameters(state)
                db.commit()
                db.refresh(state)
                await interaction.edit_original_response(
                    embed=self.cog.generate_mode_duration_embed(state),
                    view=self.cog.generate_mode_duration_view(self.guild_id, state)
                )
            finally:
                db.close()

    class GameDurationSelect(ui.Select):
        def __init__(self, guild_id: str, cog: 'AdminCog', current_duration: str):
            options = [discord.SelectOption(label=data["label"], value=key, default=(key == current_duration)) for key, data in self.DURATION_SETTINGS.items()]
            super().__init__(placeholder="Choisissez une durée (échelle de temps)...", options=options, row=1)
            self.guild_id = guild_id
            self.cog = cog
            
        async def callback(self, interaction: discord.Interaction):
            await interaction.response.defer()
            selected_duration = self.values[0]
            db = SessionLocal()
            try:
                state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()
                state.duration_key = selected_duration
                self.cog._update_game_parameters(state)
                db.commit()
                db.refresh(state)
                await interaction.edit_original_response(
                    embed=self.cog.generate_mode_duration_embed(state),
                    view=self.cog.generate_mode_duration_view(self.guild_id, state)
                )
            finally:
                db.close()

    # --- Main Config View Generation ---
    def generate_config_menu_view(self, guild_id: str, guild: discord.Guild, state: ServerState) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        is_game_running = state.game_started if state else False
        start_label, start_emoji, start_style = ("Stop Game", "⏹️", discord.ButtonStyle.danger) if is_game_running else ("Start Game", "▶️", discord.ButtonStyle.success)
        
        # Use the new ModeAndDurationButton
        view.add_item(self.ModeAndDurationButton("Difficulté & Durée", guild_id, discord.ButtonStyle.primary, 0, self, disabled=is_game_running))
        
        view.add_item(self.ConfigButton(start_label, start_emoji, guild_id, start_style, 0, self))
        view.add_item(self.GeneralConfigButton("Rôles & Salons", guild_id, discord.ButtonStyle.primary, 0, self, disabled=is_game_running))
        view.add_item(self.ConfigButton("Notifications", "🔔", guild_id, discord.ButtonStyle.primary, 1, self))
        # ... other buttons
        return view

    def generate_config_menu_embed(self, state: ServerState) -> discord.Embed:
        embed = discord.Embed(title="⚙️ Bot & Game Configuration", description="Utilisez les boutons pour ajuster les paramètres.", color=discord.Color.blue())
        
        difficulty = state.game_mode or "medium"
        duration_key = state.duration_key or "day"
        mode_str = f"`{difficulty.capitalize()}`"
        duration_str = f"`{self.DURATION_SETTINGS.get(duration_key, {}).get('label')}`"

        embed.add_field(name="▶️ Statut Général", value=f"**Jeu:** `{'En cours' if state.game_started else 'Non démarré'}`", inline=False)
        embed.add_field(name="🕹️ Paramètres de Jeu", value=f"**Difficulté :** {mode_str}\n**Échelle de Temps :** {duration_str}", inline=False)
        
        admin_role, notif_role, game_channel = (f"<@&{state.admin_role_id}>", f"<@&{state.notification_role_id}>", f"<#{state.game_channel_id}>")
        embed.add_field(name="📍 Configuration Serveur", value=f"**Rôle Admin:** {admin_role or 'Non défini'}\n**Salon de Jeu:** {game_channel or 'Non défini'}", inline=False)

        rates_desc = f"**Faim/jour:** `{state.degradation_rate_hunger:.0f}` | **Soif/jour:** `{state.degradation_rate_thirst:.0f}`"
        embed.add_field(name="📉 Taux de Dégradation (calculés)", value=rates_desc, inline=False)
        embed.set_footer(text="Les changements de difficulté/durée sont désactivés pendant une partie.")
        return embed
    class BackButton(ui.Button):
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle, row: int = 0, cog: 'AdminCog'=None):
            super().__init__(label=label, style=style, row=row, emoji="⬅️")
            self.guild_id = guild_id
            self.cog = cog
        async def callback(self, interaction: discord.Interaction):
            await interaction.response.defer()
            db = SessionLocal()
            try:
                state = db.query(ServerState).filter_by(guild_id=str(self.guild_id)).first()
                await interaction.edit_original_response(
                    embed=self.cog.generate_config_menu_embed(state), 
                    view=self.cog.generate_config_menu_view(self.guild_id, interaction.guild, state)
                )
            finally: db.close()
    
    # --- General Purpose Buttons ---
    class ConfigButton(ui.Button):
        def __init__(self, label: str, emoji: str, guild_id: str, style: discord.ButtonStyle, row: int, cog: 'AdminCog', disabled: bool = False):
            super().__init__(label=label, emoji=emoji, style=style, row=row, disabled=disabled)
            self.guild_id = guild_id
            self.label = label
            self.cog = cog
        
        async def callback(self, interaction: discord.Interaction):
            if "Stop Game" in self.label:
                modal = StopGameConfirmationModal(guild_id=self.guild_id, cog=self.cog)
                await interaction.response.send_modal(modal)
                return

            await interaction.response.defer()
            db = SessionLocal()
            try:
                state = db.query(ServerState).filter_by(guild_id=str(self.guild_id)).first()
                if not state:
                    await interaction.followup.send("❌ **Error:** Server configuration not found.", ephemeral=True)
                    return

                if "Start Game" in self.label:
                    if not state or not state.game_channel_id:
                        await interaction.followup.send("❌ **Error:** Please configure a game channel via `⚙️ Roles & Channels` first.", ephemeral=True)
                        return
                    
                    try:
                        game_channel = await self.cog.bot.fetch_channel(state.game_channel_id)
                    except (NotFound, Forbidden):
                        await interaction.followup.send("❌ **Error:** The configured game channel is invalid.", ephemeral=True)
                        return

                    main_embed_cog = self.cog.bot.get_cog("MainEmbed")
                    if not main_embed_cog:
                        await interaction.followup.send("❌ **Critical Error:** The game module (`MainEmbed`) is not loaded.", ephemeral=True)
                        return

                    player = db.query(PlayerProfile).filter_by(guild_id=str(self.guild_id)).first()
                    now = datetime.datetime.utcnow()
                    if not player:
                        player = PlayerProfile(guild_id=str(self.guild_id), last_update=now, last_eaten_at=now, last_drank_at=now, last_slept_at=now, last_smoked_at=now, last_urinated_at=now, last_shower_at=now)
                        db.add(player)
                    
                    state.is_test_mode = False 
                    state.game_started = True
                    state.game_start_time = now
                    db.commit()
                    db.refresh(player)
                    db.refresh(state)

                    game_embed = main_embed_cog.generate_dashboard_embed(player, state, interaction.guild)
                    game_view = DashboardView(player)
                    game_message = await game_channel.send(embed=game_embed, view=game_view)
                    
                    state.game_message_id = game_message.id
                    db.commit()

                    await interaction.edit_original_response(
                        embed=self.cog.generate_config_menu_embed(state), 
                        view=self.cog.generate_config_menu_view(self.guild_id, interaction.guild, state)
                    )
                    await interaction.followup.send(f"✅ The game has started! The interface has been posted in {game_channel.mention}.", ephemeral=True)

                # --- CORRECTION 2: Logique du bouton "Notifications" ---
                # On redirige vers l'écran de configuration des rôles, pas celui des toggles.
                elif "Notifications" in self.label:
                    await interaction.edit_original_response(
                        embed=self.cog.generate_notifications_config_embed(state),
                        view=self.cog.generate_notifications_config_view(self.guild_id)
                    )
                
                elif "View Stats" in self.label:
                     await interaction.edit_original_response(
                        embed=self.cog.generate_stats_embed(self.guild_id),
                        view=self.cog.generate_stats_view(self.guild_id)
                    )

            except Exception as e:
                logger.error(f"Error in ConfigButton callback: {e}", exc_info=True)
                if not interaction.is_expired():
                    await interaction.followup.send(f"A critical error occurred.", ephemeral=True)
                db.rollback()
            finally:
                db.close()

    # --- NOUVELLE LOGIQUE POUR ROLES & CHANNELS ---
    class GeneralConfigButton(ui.Button):
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle, row: int, cog: 'AdminCog', disabled: bool = False):
            super().__init__(label=label, style=style, row=row, disabled=disabled, emoji="⚙️")
            self.guild_id = guild_id
            self.cog = cog
        async def callback(self, interaction: discord.Interaction):
            await interaction.response.edit_message(
                embed=self.cog.generate_role_and_channel_config_embed(
                    self.cog.get_server_state(self.guild_id)
                ),
                view=self.cog.generate_general_config_view(self.guild_id, interaction.guild)
            )

    def get_server_state(self, guild_id: str) -> ServerState:
        db = SessionLocal()
        try:
            return db.query(ServerState).filter_by(guild_id=guild_id).one()
        finally:
            db.close()

    def generate_role_and_channel_config_embed(self, state: ServerState) -> discord.Embed:
        embed = discord.Embed(title="⚙️ General Config (Roles & Channels)", description="Select an item to configure. This will open a new paginated selection menu.", color=discord.Color.purple())
        current_admin_role = f"<@&{state.admin_role_id}>" if state.admin_role_id else "Not set"
        current_notif_role = f"<@&{state.notification_role_id}>" if state.notification_role_id else "Not set"
        current_game_channel = f"<#{state.game_channel_id}>" if state.game_channel_id else "Not set"
        embed.add_field(name="👑 Admin Role", value=f"Current: {current_admin_role}", inline=False)
        embed.add_field(name="🎮 Game Channel", value=f"Current: {current_game_channel}", inline=False)
        return embed

    class OpenPaginatorButton(ui.Button):
        def __init__(self, label: str, guild_id: str, select_type: Literal['admin_role', 'notification_role', 'game_channel'], row: int, cog: 'AdminCog'):
            super().__init__(label=label, style=discord.ButtonStyle.primary, row=row)
            self.guild_id = guild_id; self.select_type = select_type; self.cog = cog
        async def callback(self, interaction: discord.Interaction):
            await interaction.response.defer() 
            if not interaction.guild: 
                await interaction.followup.send("Guild not found.", ephemeral=True); return
            if self.select_type in ["admin_role", "notification_role"]: 
                item_list, item_type_str = interaction.guild.roles, "role"
            else: 
                item_list, item_type_str = [ch for ch in interaction.guild.channels if isinstance(ch, discord.TextChannel)], "channel"
            options, id_mapping = self.cog.create_options_and_mapping(item_list, item_type_str, interaction.guild)
            paginated_view = PaginatedViewManager(guild_id=self.guild_id, all_options=options, id_mapping=id_mapping, select_type=self.select_type, cog=self.cog)
            await interaction.edit_original_response(embed=discord.Embed(title=f"Configuring: {self.label}"), view=paginated_view)

    def generate_general_config_view(self, guild_id: str, guild: discord.Guild) -> discord.ui.View:
        view = discord.ui.View(timeout=180)
        view.add_item(self.OpenPaginatorButton("Set Admin Role", guild_id, "admin_role", 0, self))
        view.add_item(self.OpenPaginatorButton("Set Game Channel", guild_id, "game_channel", 2, self))
        view.add_item(self.BackButton("Back to Main Menu", guild_id, discord.ButtonStyle.secondary, 3, self))
        return view

    # --- Sections for Stats & Notifications (largely unchanged) ---
    def generate_stats_embed(self, guild_id: str) -> discord.Embed: 
        return discord.Embed(title="📊 Server Statistics", description="This feature is under development.", color=discord.Color.purple())
    def generate_stats_view(self, guild_id: str) -> discord.ui.View: 
        view = discord.ui.View(timeout=None)
        view.add_item(self.BackButton("Back to Settings", guild_id, discord.ButtonStyle.secondary, 3, self))
        return view
    
    def generate_notifications_embed(self, guild_id: str):
        db = SessionLocal()
        try:
            state = db.query(ServerState).filter_by(guild_id=guild_id).first()
            if not state: return discord.Embed(title="🔔 Notification Settings", description="Could not load server configuration.", color=discord.Color.red())
            embed = discord.Embed(title="🔔 Notification Settings", color=discord.Color.green())
            notif_role_mention = f"<@&{state.notification_role_id}>" if state.notification_role_id else "Not set"
            embed.add_field(name="📍 General Notification Role", value=notif_role_mention, inline=False)
            
            embed.add_field(name="🚨 Specific Alert Roles", value=(
                f"📉 Low Vitals: {f'<@&{state.notify_vital_low_role_id}>' if state.notify_vital_low_role_id else 'Not set'}\n"
                f"🚨 Critical: {f'<@&{state.notify_critical_role_id}>' if state.notify_critical_role_id else 'Not set'}\n"
                f"🚬 Cravings: {f'<@&{state.notify_craving_role_id}>' if state.notify_craving_role_id else 'Not set'}\n"
                f"💬 Friend/Quiz Msg: {f'<@&{state.notify_friend_message_role_id}>' if state.notify_friend_message_role_id else 'Not set'}\n"
                f"🛒 Shop Promos: {f'<@&{state.notify_shop_promo_role_id}>' if state.notify_shop_promo_role_id else 'Not set'}"
            ), inline=False)
            embed.set_footer(text="Use the buttons below to adjust preferences.")
            return embed
        finally: db.close()

    def generate_notifications_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=180)
        db = SessionLocal()
        try:
            state = db.query(ServerState).filter_by(guild_id=guild_id).first()
            if not state:
                view.add_item(self.BackButton("Back", guild_id, discord.ButtonStyle.secondary, row=0, cog=self)); return view
            view.add_item(self.NotificationToggle("🔴 Low Vitals", "notify_on_low_vital_stat", guild_id, discord.ButtonStyle.danger if state.notify_on_low_vital_stat else discord.ButtonStyle.secondary, self, 0))
            view.add_item(self.NotificationToggle("🔴 Critical Event", "notify_on_critical_event", guild_id, discord.ButtonStyle.danger if state.notify_on_critical_event else discord.ButtonStyle.secondary, self, 1))
            view.add_item(self.NotificationToggle("🚬 Cravings", "notify_on_craving", guild_id, discord.ButtonStyle.success if state.notify_on_craving else discord.ButtonStyle.secondary, self, 1))
            view.add_item(self.NotificationToggle("💬 Friend/Quiz", "notify_on_friend_message", guild_id, discord.ButtonStyle.primary if state.notify_on_friend_message else discord.ButtonStyle.secondary, self, 2))
            view.add_item(self.NotificationToggle("💛 Shop Promo", "notify_on_shop_promo", guild_id, discord.ButtonStyle.primary if state.notify_on_shop_promo else discord.ButtonStyle.secondary, self, 2))
            view.add_item(self.BackButton("Back", guild_id, discord.ButtonStyle.secondary, row=4, cog=self))
            return view
        finally: db.close()

    class NotificationToggle(ui.Button):
        def __init__(self, label: str, toggle_key: str, guild_id: str, style: discord.ButtonStyle, cog: 'AdminCog', row: int):
            super().__init__(label=label, style=style, row=row)
            self.toggle_key = toggle_key
            self.guild_id = guild_id
            self.cog = cog
        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            try:
                state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()
                if not state: 
                    await interaction.response.send_message("Erreur: Server state not found.", ephemeral=True); return
                if state.game_started: 
                    await interaction.response.send_message("Cannot change notification settings while a game is in progress.", ephemeral=True); return
                
                new_value = not getattr(state, self.toggle_key)
                setattr(state, self.toggle_key, new_value)
                db.commit()
                db.refresh(state)

                await interaction.response.edit_message(embed=self.cog.generate_notifications_embed(self.guild_id), view=self.cog.generate_notifications_view(self.guild_id))
            finally:
                db.close()

async def setup(bot):
    await bot.add_cog(AdminCog(bot))