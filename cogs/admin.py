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

class ItemSelect(ui.Select):
    """ Un menu déroulant simple pour sélectionner un item (rôle/salon). """
    def __init__(self, guild_id: str, select_type: Literal['admin_role', 'notification_role', 'game_channel'], id_mapping: dict, cog: 'AdminCog'):
        self.guild_id = guild_id
        self.select_type = select_type
        self.id_mapping = id_mapping
        self.cog = cog
        super().__init__(placeholder=f"Select the item...", row=0)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        selected_hash = self.values[0]
        selected_id = self.id_mapping.get(selected_hash)

        if not selected_id:
            await interaction.followup.send("Error: Could not find the selected item ID.", ephemeral=True)
            return

        db = SessionLocal()
        try:
            state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()
            if not state:
                await interaction.followup.send("Error: Server configuration not found.", ephemeral=True)
                return

            if self.select_type == "admin_role":
                state.admin_role_id = selected_id
                type_label = "Admin role"
            elif self.select_type == "notification_role":
                state.notification_role_id = selected_id
                type_label = "Notification role"
            else: # game_channel
                state.game_channel_id = selected_id
                type_label = "Game channel"

            db.commit()
            await interaction.followup.send(f"✅ {type_label} has been updated!", ephemeral=True)
            
            db.refresh(state)
            new_embed = self.cog.generate_role_and_channel_config_embed(state)
            new_view = self.cog.generate_general_config_view(self.guild_id, interaction.guild)
            await interaction.edit_original_response(embed=new_embed, view=new_view)

        except Exception as e:
            db.rollback()
            logger.error(f"Error updating {self.select_type}: {e}", exc_info=True)
            await interaction.followup.send(f"A database error occurred: {e}", ephemeral=True)
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
    
    GAME_MODES = {
        "peaceful": {"tick_interval_minutes": 60, "rates": {"hunger": 5.0, "thirst": 4.0, "bladder": 5.0, "energy": 3.0, "stress": 1.0, "boredom": 2.0, "hygiene": 2.0}},
        "medium": {"tick_interval_minutes": 30, "rates": {"hunger": 10.0, "thirst": 8.0, "bladder": 15.0, "energy": 5.0, "stress": 3.0, "boredom": 7.0, "hygiene": 4.0}},
        "hard": {"tick_interval_minutes": 15, "rates": {"hunger": 20.0, "thirst": 16.0, "bladder": 30.0, "energy": 10.0, "stress": 6.0, "boredom": 14.0, "hygiene": 8.0}}
    }
    GAME_DURATIONS = { "short": {"days": 14, "label": "Court (14 jours)"}, "medium": {"days": 31, "label": "Moyen (31 jours)"}, "long": {"days": 72, "label": "Long (72 jours)"}, "test_day": {"label": "Test Day [24 Min]"} }

    MAX_OPTION_LENGTH = 100
    MIN_OPTION_LENGTH = 1
    # --- FINALIZED: Test day settings for 24 min duration ---
    TEST_DURATION_MINUTES = 24 
    TEST_RATE_MULTIPLIER = 60 # (24h * 60min) / 24min = 60. Rates are 60x faster.

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
    class SetupGameModeButton(ui.Button):
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle, row: int, cog: 'AdminCog', disabled: bool = False):
            super().__init__(label=label, style=style, row=row, disabled=disabled, emoji="🕹️")
            self.guild_id = guild_id
            self.cog = cog
        async def callback(self, interaction: discord.Interaction):
            await interaction.response.edit_message(embed=self.cog.generate_setup_game_mode_embed(), view=self.cog.generate_setup_game_mode_view(self.guild_id))

    def generate_setup_game_mode_embed(self) -> discord.Embed:
        return discord.Embed(title="🎮 Mode & Duration Setup", description="Select a difficulty and duration for the game.", color=discord.Color.teal())

    def generate_setup_game_mode_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        view.add_item(self.GameModeSelect(guild_id, "mode", 0, self)); view.add_item(self.GameDurationSelect(guild_id, "duration", 1, self)); view.add_item(self.BackButton("Back to Settings", guild_id, discord.ButtonStyle.secondary, 2, self))
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
            options = [discord.SelectOption(label=data["label"], value=key) for key, data in cog.GAME_DURATIONS.items()]
            super().__init__(placeholder="Choose the game duration...", options=options, custom_id=f"select_gameduration_{guild_id}", row=row)
            self.guild_id = guild_id
            self.cog = cog
            
        async def callback(self, interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True, thinking=True)
            selected_key = self.values[0]
            db = SessionLocal()
            try:
                state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()
                if not state or not self.cog.GAME_DURATIONS.get(selected_key):
                    await interaction.followup.send("Error processing selection.", ephemeral=True)
                    return
                
                state.duration_key = selected_key
                db.commit()

                if selected_key == "test_day":
                    await self.start_test_game(interaction, state, db)
                else:
                    duration_data = self.cog.GAME_DURATIONS[selected_key]
                    embed = self.cog.generate_setup_game_mode_embed()
                    embed.description = f"✅ Game duration set to **{duration_data['label']}**.\n{embed.description}"
                    # Use edit_original_response for the non-deferred path as well, for consistency
                    await interaction.edit_original_response(embed=embed, view=self.cog.generate_setup_game_mode_view(self.guild_id))
                    # And send a confirmation
                    await interaction.followup.send(f"Duration set to {duration_data['label']}.", ephemeral=True)

            except Exception as e:
                logger.error(f"Error in GameDurationSelect callback: {e}", exc_info=True)
                await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)
            finally:
                db.close()

        async def start_test_game(self, interaction: discord.Interaction, state: ServerState, db: SessionLocal):
            if not state.game_channel_id:
                return await interaction.followup.send("❌ **Error:** Configure a game channel before starting a test.", ephemeral=True)
            if state.game_started:
                return await interaction.followup.send("❌ **Error:** A game is already in progress.", ephemeral=True)

            main_embed_cog = self.cog.bot.get_cog("MainEmbed")
            if not main_embed_cog:
                return await interaction.followup.send("❌ Critical Error: `MainEmbed` module not loaded.", ephemeral=True)

            # Apply test mode settings
            state.is_test_mode = True
            mode_data = self.cog.GAME_MODES["hard"] # Use hard mode as base for test
            for rate_key, base_value in mode_data["rates"].items():
                setattr(state, f"degradation_rate_{rate_key}", base_value * self.cog.TEST_RATE_MULTIPLIER)
            state.game_tick_interval_minutes = 1 # Tick every minute for smooth clock updates
            state.game_day_start_hour = 8 # Game day starts at 8 AM

            # Reset player profile for a clean test
            player = db.query(PlayerProfile).filter_by(guild_id=str(interaction.guild.id)).first()
            if player:
                db.delete(player)
                db.commit()
            
            now = datetime.datetime.utcnow()
            player = PlayerProfile(
                guild_id=str(interaction.guild.id), 
                last_update=now, 
                recent_logs="--- Test Session Started ---\n"
            )
            db.add(player)
            
            state.game_started = True
            state.game_start_time = now
            db.commit()
            db.refresh(player)
            db.refresh(state)

            player.show_stats_in_view = True
            db.commit()
            db.refresh(player)
            
            game_view = DashboardView(player)
            game_embed = main_embed_cog.generate_dashboard_embed(player, state, interaction.guild)
            
            game_channel = await self.cog.bot.fetch_channel(state.game_channel_id)
            game_message = await game_channel.send(content="**--- ACCELERATED TEST DAY STARTING ---**", embed=game_embed, view=game_view)
            
            state.game_message_id = game_message.id
            db.commit()

            await interaction.followup.send(f"✅ The test game has started in {game_channel.mention}!", ephemeral=True)
            await interaction.edit_original_response(embed=self.cog.generate_config_menu_embed(state), view=self.cog.generate_config_menu_view(self.guild_id, interaction.guild, state))
            
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
                if "Start Game" in self.label:
                    state = db.query(ServerState).filter_by(guild_id=str(self.guild_id)).first()
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

                elif "Notifications" in self.label:
                    await interaction.edit_original_response(
                        embed=self.cog.generate_notifications_embed(self.guild_id),
                        view=self.cog.generate_notifications_view(self.guild_id)
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
        embed.add_field(name="🔔 Notification Role", value=f"Current: {current_notif_role}", inline=False)
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
        view.add_item(self.OpenPaginatorButton("Set Notification Role", guild_id, "notification_role", 1, self))
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
            super().__init__(label=label, style=style, row=row); self.toggle_key = toggle_key; self.guild_id = guild_id; self.cog = cog
        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            try:
                state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()
                if not state: 
                    await interaction.response.send_message("Error: Server state not found.", ephemeral=True); return
                if state.game_started: 
                    await interaction.response.send_message("Cannot change notification settings while a game is in progress.", ephemeral=True); return
                
                new_value = not getattr(state, self.toggle_key)
                setattr(state, self.toggle_key, new_value)
                db.commit()
                db.refresh(state)

                await interaction.response.edit_message(embed=self.cog.generate_notifications_embed(self.guild_id), view=self.cog.generate_notifications_view(self.guild_id))
                await interaction.followup.send(f"Notifications for '{self.label}' set to {'Enabled' if new_value else 'Disabled'}.", ephemeral=True)
            finally:
                db.close()

async def setup(bot):
    await bot.add_cog(AdminCog(bot))