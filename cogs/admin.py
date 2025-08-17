# --- cogs/admin.py (CORRECTED & REFACTORED) ---

import discord
from discord.ext import commands
from discord.errors import Forbidden, NotFound
from discord import app_commands, ui
import hashlib
import datetime
import math
from typing import List, Tuple, Dict, Literal, Union, Optional, cast
import os
import traceback
from sqlalchemy.orm import Session

# --- Centralized Imports ---
from db.database import SessionLocal
from db.models import ServerState, PlayerProfile
from utils.logger import get_logger
from utils.embed_builder import create_styled_embed
from cogs.main_embed import DashboardView
from utils.time_manager import (
    get_utc_now, to_localized, prepare_for_db,
    is_work_time as is_wt, is_lunch_break as is_lb
)

# --- Setup Logger for this Cog ---
logger = get_logger(__name__)

# --- Constants ---
MAX_OPTIONS_PER_PAGE = 25
PAGINATED_SELECT_ITEMS_PER_PAGE = 24

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO_OWNER = os.getenv("GITHUB_REPO_OWNER")
GITHUB_REPO_NAME = os.getenv("GITHUB_REPO_NAME")

# --- Debug Commands Group ---
class AdminDebugCommands(commands.GroupCog, name="debug"):
    def __init__(self, bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(name="unlock_all", description="[DEBUG] Débloque tous les achievements et le smoke shop")
    @app_commands.default_permissions(administrator=True)
    async def unlock_all(self, interaction: discord.Interaction):
        db = SessionLocal()
        try:
            # Get player profile
            player = db.query(PlayerProfile).filter_by(guild_id=str(interaction.guild_id)).first()
            if not player:
                await interaction.response.send_message("❌ Profil joueur non trouvé", ephemeral=True)
                return

            # Unlock smoke shop by setting high addiction levels
            player.substance_addiction_level = 100.0
            player.craving_nicotine = 100.0
            player.craving_alcohol = 100.0
            player.craving_cannabis = 100.0
            
            # Give money for testing
            player.money = 1000

            db.commit()
            await interaction.response.send_message("✅ Smoke shop débloqué et argent ajouté !", ephemeral=True)
        except Exception as e:
            db.rollback()
            logger.error(f"Erreur lors du déblocage: {e}")
            await interaction.response.send_message("❌ Une erreur est survenue", ephemeral=True)
        finally:
            db.close()

    @app_commands.command(name="fast_time", description="[DEBUG] Accélère le temps de jeu (x10)")
    @app_commands.default_permissions(administrator=True)
    async def fast_time(self, interaction: discord.Interaction):
        db = SessionLocal()
        try:
            server = db.query(ServerState).filter_by(guild_id=str(interaction.guild_id)).first()
            if not server:
                await interaction.response.send_message("❌ Configuration serveur non trouvée", ephemeral=True)
                return

            # Enable test mode which makes time pass faster
            server.is_test_mode = True
            server.game_tick_interval_minutes = 1  # Update every minute instead of every 30 minutes
            
            db.commit()
            await interaction.response.send_message("✅ Mode accéléré activé ! (1 minute réelle = 2 heures en jeu)", ephemeral=True)
        except Exception as e:
            db.rollback()
            logger.error(f"Erreur lors de l'activation du mode accéléré: {e}")
            await interaction.response.send_message("❌ Une erreur est survenue", ephemeral=True)
        finally:
            db.close()

    @app_commands.command(name="normal_time", description="[DEBUG] Remet la vitesse du temps normale")
    @app_commands.default_permissions(administrator=True)
    async def normal_time(self, interaction: discord.Interaction):
        db = SessionLocal()
        try:
            server = db.query(ServerState).filter_by(guild_id=str(interaction.guild_id)).first()
            if not server:
                await interaction.response.send_message("❌ Configuration serveur non trouvée", ephemeral=True)
                return

            # Disable test mode
            server.is_test_mode = False
            server.game_tick_interval_minutes = 30  # Back to normal update interval
            
            db.commit()
            await interaction.response.send_message("✅ Mode normal réactivé", ephemeral=True)
        except Exception as e:
            db.rollback()
            logger.error(f"Erreur lors de la désactivation du mode accéléré: {e}")
            await interaction.response.send_message("❌ Une erreur est survenue", ephemeral=True)
        finally:
            db.close()

    @app_commands.command(name="reset_cooldowns", description="[DEBUG] Réinitialise tous les cooldowns d'actions")
    @app_commands.default_permissions(administrator=True)
    async def reset_cooldowns(self, interaction: discord.Interaction):
        db = SessionLocal()
        try:
            player = db.query(PlayerProfile).filter_by(guild_id=str(interaction.guild_id)).first()
            if not player:
                await interaction.response.send_message("❌ Profil joueur non trouvé", ephemeral=True)
                return

            # Reset all action timestamps
            player.last_drink = None
            player.last_eat = None
            player.last_sleep = None
            player.last_smoke = None
            player.last_pee = None
            player.last_shower = None
            
            db.commit()
            await interaction.response.send_message("✅ Cooldowns réinitialisés !", ephemeral=True)
        except Exception as e:
            db.rollback()
            logger.error(f"Erreur lors de la réinitialisation des cooldowns: {e}")
            await interaction.response.send_message("❌ Une erreur est survenue", ephemeral=True)
        finally:
            db.close()

    @app_commands.command(name="refill_stats", description="[DEBUG] Remplit toutes les statistiques à 100%")
    @app_commands.default_permissions(administrator=True)
    async def refill_stats(self, interaction: discord.Interaction):
        db = SessionLocal()
        try:
            player = db.query(PlayerProfile).filter_by(guild_id=str(interaction.guild_id)).first()
            if not player:
                await interaction.response.send_message("❌ Profil joueur non trouvé", ephemeral=True)
                return

            # Reset all stats to max
            player.health = 100.0
            player.energy = 100.0
            player.sanity = 100.0
            player.hunger = 0.0
            player.thirst = 0.0
            player.bladder = 0.0
            player.fatigue = 0.0
            player.stress = 0.0
            player.boredom = 0.0
            player.hygiene = 100.0
            player.job_performance = 100.0
            
            db.commit()
            await interaction.response.send_message("✅ Stats remplies à 100% !", ephemeral=True)
        except Exception as e:
            db.rollback()
            logger.error(f"Erreur lors du remplissage des stats: {e}")
            await interaction.response.send_message("❌ Une erreur est survenue", ephemeral=True)
        finally:
            db.close()


class RoleSelect(ui.Select):
    """Menu pour sélectionner un rôle spécifique pour un paramètre de notification."""
    def __init__(self, guild_id: str, setting_key: str, id_mapping: dict, cog: 'AdminCog'):
        self.guild_id = guild_id
        self.setting_key = setting_key
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
            # REFACTOR: Pass interaction.guild to generate the new view with the updated select menu
            new_view = self.cog.generate_notifications_config_view(self.guild_id, interaction.guild)
            await interaction.edit_original_response(embed=new_embed, view=new_view, content=None)
        except Exception as e:
            db.rollback()
            logger.error(f"Erreur de mise à jour du rôle: {e}", exc_info=True)
        finally:
            db.close()

class SetAllNotificationsRoleSelect(ui.Select):
    """
    NOUVEAU: Menu déroulant pour sélectionner un rôle unique qui sera appliqué
    à TOUTES les configurations de notification, remplaçant l'ancien bouton vert.
    """
    def __init__(self, guild_id: str, cog: 'AdminCog', roles: list[discord.Role]):
        self.guild_id = guild_id
        self.cog = cog
        options, self.id_mapping = self.cog.create_options_and_mapping(roles, "role", None)

        super().__init__(
            placeholder="Définir un rôle unique pour toutes les notifications...",
            options=options[:25], # Un Select ne peut avoir que 25 options max
            row=1 # Mis sur la deuxième ligne
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        selected_hash = self.values[0]
        selected_id = self.id_mapping.get(selected_hash)

        if not selected_id:
            await interaction.followup.send("Erreur : Rôle introuvable.", ephemeral=True)
            return

        db = SessionLocal()
        try:
            state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()
            if not state:
                await interaction.followup.send("Erreur : Configuration du serveur introuvable.", ephemeral=True)
                return

            notification_role_fields = [
                "notification_role_id", "notify_vital_low_role_id", "notify_critical_role_id",
                "notify_craving_role_id", "notify_friend_message_role_id", "notify_shop_promo_role_id"
            ]
            for field in notification_role_fields:
                setattr(state, field, selected_id)

            db.commit()
            db.refresh(state)

            await interaction.followup.send(f"✅ Tous les rôles de notification ont été définis sur <@&{selected_id}> !", ephemeral=True)
            
            new_embed = self.cog.generate_notifications_config_embed(state)
            new_view = self.cog.generate_notifications_config_view(self.guild_id, interaction.guild)
            await interaction.edit_original_response(embed=new_embed, view=new_view)
        except Exception as e:
            db.rollback()
            logger.error(f"Erreur lors de la définition du rôle de notif unique: {e}", exc_info=True)
        finally:
            db.close()


class PaginatedViewManager(ui.View):
    """Gère un menu déroulant paginé avec des boutons Précédent/Suivant."""
    def __init__(self, guild_id: str, all_options: list[discord.SelectOption], id_mapping: dict, select_type: Literal['admin_role', 'notification_role', 'game_channel'], cog: 'AdminCog'):
        super().__init__(timeout=180)
        self.guild_id = guild_id; self.all_options = all_options; self.id_mapping = id_mapping
        self.select_type = select_type; self.cog = cog; self.current_page = 0
        self.total_pages = max(1, math.ceil(len(self.all_options) / PAGINATED_SELECT_ITEMS_PER_PAGE))
        self.update_components()

    def update_components(self):
        self.clear_items()
        start = self.current_page * PAGINATED_SELECT_ITEMS_PER_PAGE
        end = start + PAGINATED_SELECT_ITEMS_PER_PAGE
        page_options = self.all_options[start:end] or [discord.SelectOption(label="Aucun item sur cette page", value="no_items")]

        class ItemSelect(ui.Select):
            def __init__(inner_self, guild_id: str, select_type: str, id_mapping: dict, cog: 'AdminCog', options: list, placeholder: str):
                inner_self.guild_id = guild_id; inner_self.select_type = select_type
                inner_self.id_mapping = id_mapping; inner_self.cog = cog
                super().__init__(placeholder=placeholder, row=0, options=options)
            
            async def callback(inner_self, interaction: discord.Interaction):
                await interaction.response.defer()
                selected_id = inner_self.id_mapping.get(inner_self.values[0])
                if not selected_id:
                    await interaction.followup.send("Erreur: Item introuvable.", ephemeral=True); return
                db = SessionLocal()
                try:
                    state = db.query(ServerState).filter_by(guild_id=inner_self.guild_id).first()
                    db_field_map = {'admin_role': 'admin_role_id', 'game_channel': 'game_channel_id'}
                    setattr(state, db_field_map[inner_self.select_type], selected_id)
                    db.commit(); db.refresh(state)
                    await interaction.followup.send("✅ Paramètre mis à jour !", ephemeral=True)
                    new_embed = inner_self.cog.generate_role_and_channel_config_embed(state)
                    new_view = inner_self.cog.generate_general_config_view(inner_self.guild_id, interaction.guild)
                    await interaction.edit_original_response(embed=new_embed, view=new_view)
                finally:
                    db.close()
        
        placeholder = f"Sélectionnez... (Page {self.current_page + 1}/{self.total_pages})"
        self.add_item(ItemSelect(self.guild_id, self.select_type, self.id_mapping, self.cog, page_options, placeholder))
        
        self.prev_button = ui.Button(label="Précédent", emoji="◀️", style=discord.ButtonStyle.secondary, row=1, disabled=(self.current_page == 0))
        self.page_indicator = ui.Button(label=f"{self.current_page + 1}/{self.total_pages}", style=discord.ButtonStyle.grey, disabled=True, row=1)
        self.next_button = ui.Button(label="Suivant", emoji="▶️", style=discord.ButtonStyle.secondary, row=1, disabled=(self.current_page >= self.total_pages - 1))
        
        self.prev_button.callback = self.prev_page; self.next_button.callback = self.next_page
        self.add_item(self.prev_button); self.add_item(self.page_indicator); self.add_item(self.next_button)
        self.add_item(self.cog.BackButton("Retour", self.guild_id, discord.ButtonStyle.red, 2, self.cog))

    async def prev_page(self, interaction: discord.Interaction):
        self.current_page -= 1; self.update_components()
        await interaction.response.edit_message(view=self)

    async def next_page(self, interaction: discord.Interaction):
        self.current_page += 1; self.update_components()
        await interaction.response.edit_message(view=self)

# --- Le reste des classes reste similaire... ---
class StopGameConfirmationModal(ui.Modal, title="Confirm Game Stop"):
    # ... (code inchangé)
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
    def __init__(self, bot): self.bot = bot
    BASE_DAILY_RATES = {"hunger": 150, "thirst": 200, "bladder": 120, "stress": 40, "boredom": 200, "hygiene": 100}
    DIFFICULTY_MULTIPLIERS = {"peaceful": 0.75, "medium": 1.0, "hard": 1.5}
    DURATION_SETTINGS = {
        "test": {"minutes_per_day": 12, "label": "Test (1 semaine en 84 mins)"},
        "real_time": {"minutes_per_day": 1440, "label": "Temps Réel (1:1)"},
    }
    def _update_game_parameters(self, state: ServerState):
        difficulty = state.game_mode or "medium"; duration_key = state.duration_key or "real_time"
        multiplier = self.DIFFICULTY_MULTIPLIERS.get(difficulty, 1.0)
        duration_setting = self.DURATION_SETTINGS.get(duration_key, self.DURATION_SETTINGS["real_time"])
        for rate, value in self.BASE_DAILY_RATES.items(): setattr(state, f"degradation_rate_{rate}", value * multiplier)
        state.game_minutes_per_day = duration_setting["minutes_per_day"]

    @app_commands.command(name="config", description="Configure les paramètres du bot et du jeu pour le serveur.")
    @app_commands.default_permissions(administrator=True)
    async def config(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message(
                "Cette commande doit être utilisée dans un serveur.",
                ephemeral=True
            )
            return
            
        # Réponse immédiate
        db = SessionLocal()
        try:
            state = db.query(ServerState).filter_by(guild_id=str(interaction.guild.id)).first()
            if not state:
                state = ServerState(guild_id=str(interaction.guild.id))
                self._update_game_parameters(state)
                db.add(state)
                db.commit()
                db.refresh(state)
            
            embed = self.generate_config_menu_embed(state)
            view = self.generate_config_menu_view(str(interaction.guild.id), interaction.guild, state)
            
            await interaction.response.send_message(
                embed=embed,
                view=view,
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error in config command: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "Une erreur s'est produite lors de la configuration.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "Une erreur s'est produite lors de la configuration.",
                    ephemeral=True
                )
        finally:
            db.close()

    def create_options_and_mapping(self, items: List[Union[discord.Role, discord.TextChannel]], item_type: str, guild: discord.Guild | None) -> Tuple[List[discord.SelectOption], Dict[str, str]]:
        options: List[discord.SelectOption] = []
        id_mapping: Dict[str, str] = {}
        
        sorted_items = sorted(items, key=lambda x: x.position, reverse=(item_type == "role"))
        
        for item in sorted_items:
            if item_type == "role" and isinstance(item, discord.Role) and item.is_default():
                continue
                
            item_id = str(item.id)
            item_name = str(item.name)
            label = f"🔹 {item_name}" if item_type == "role" else f"#{item_name}"
            
            hashed_id = hashlib.sha256(item_id.encode()).hexdigest()[:25]
            options.append(discord.SelectOption(
                label=label[:100],
                value=hashed_id,
                description=f"ID: {item_id}"
            ))
            id_mapping[hashed_id] = item_id
            
        if not options:
            options.append(discord.SelectOption(label="Aucun item trouvé", value="no_items"))
            
        return options, id_mapping

    def generate_notifications_config_embed(self, state: ServerState) -> discord.Embed:
        embed = discord.Embed(title="🔔 Configuration des Rôles de Notification", color=discord.Color.gold())
        roles = {"Général": state.notification_role_id, "Vitals Faibles": state.notify_vital_low_role_id, "Événement Critique": state.notify_critical_role_id, "Manque / Envies": state.notify_craving_role_id, "Message Ami": state.notify_friend_message_role_id, "Promotion Boutique": state.notify_shop_promo_role_id}
        value = "\n".join([f"**{name}:** {f'<@&{role_id}>' if role_id else 'Non défini'}" for name, role_id in roles.items()])
        embed.add_field(name="Rôles Actuels", value=value); embed.set_footer(text="Utilisez les menus pour configurer les rôles.")
        return embed

    class NotificationRoleTypeSelect(ui.Select):
        def __init__(self, guild_id: str, cog: 'AdminCog'):
            self.guild_id, self.cog = guild_id, cog
            options = [discord.SelectOption(label="Rôle de notification général", value="notification_role_id"), discord.SelectOption(label="Rôle pour Vitals Faibles", value="notify_vital_low_role_id"), discord.SelectOption(label="Rôle pour Événement Critique", value="notify_critical_role_id"), discord.SelectOption(label="Rôle pour Manque / Envies", value="notify_craving_role_id"), discord.SelectOption(label="Rôle pour Message Ami", value="notify_friend_message_role_id"), discord.SelectOption(label="Rôle pour Promotion Boutique", value="notify_shop_promo_role_id")]
            self.options_map = {opt.value: opt.label for opt in options}
            super().__init__(placeholder="Choisir le type de notification à configurer...", options=options, row=0)
        async def callback(self, interaction: discord.Interaction):
            setting_key = self.values[0]; all_roles = interaction.guild.roles
            options, id_mapping = self.cog.create_options_and_mapping(all_roles, "role", interaction.guild)
            view = ui.View(); select_menu = RoleSelect(self.guild_id, setting_key, id_mapping, self.cog)
            select_menu.options = options[:25]; view.add_item(select_menu)
            view.add_item(self.cog.BackButton("Retour", self.guild_id, discord.ButtonStyle.secondary, 1, self.cog, target_menu="notifications_config"))
            await interaction.response.edit_message(content=f"Sélectionnez le rôle pour : **{self.options_map[setting_key]}**", embed=None, view=view)

    def generate_notifications_config_view(self, guild_id: str, guild: discord.Guild) -> ui.View:
        view = ui.View(timeout=180); view.add_item(self.NotificationRoleTypeSelect(guild_id, self))
        view.add_item(SetAllNotificationsRoleSelect(guild_id, self, guild.roles))
        view.add_item(self.BackButton("Retour au menu principal", guild_id, discord.ButtonStyle.red, 2, self))
        return view

    class ModeAndDurationButton(ui.Button):
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle, row: int, cog: 'AdminCog', disabled: bool = False):
            super().__init__(label=label, style=style, row=row, disabled=disabled, emoji="🕹️"); self.guild_id = guild_id; self.cog = cog
        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            try:
                state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()
                await interaction.response.edit_message(embed=self.cog.generate_mode_duration_embed(state), view=self.cog.generate_mode_duration_view(self.guild_id, state))
            finally: db.close()

    def generate_mode_duration_embed(self, state: ServerState) -> discord.Embed:
        embed = discord.Embed(title="🎮 Difficulté & Durée", color=discord.Color.teal())
        difficulty = state.game_mode or "medium"; duration_key = state.duration_key or "real_time"
        embed.add_field(name="Difficulté Actuelle", value=f"`{difficulty.capitalize()}` (Multiplicateur: x{self.DIFFICULTY_MULTIPLIERS.get(difficulty, 1.0)})", inline=False)
        embed.add_field(name="Durée Actuelle", value=f"`{self.DURATION_SETTINGS.get(duration_key, {}).get('label')}`", inline=False)
        return embed

    def generate_mode_duration_view(self, guild_id: str, state: ServerState) -> ui.View:
        view = ui.View(timeout=180); view.add_item(self.GameDifficultySelect(guild_id, self, state.game_mode))
        view.add_item(self.GameDurationSelect(guild_id, self, state.duration_key))
        view.add_item(self.BackButton("Retour", guild_id, discord.ButtonStyle.secondary, 2, self))
        return view

    class GameDifficultySelect(ui.Select):
        def __init__(self, guild_id: str, cog: 'AdminCog', current_difficulty: str):
            options = [discord.SelectOption(label=key.capitalize(), value=key, default=(key == current_difficulty)) for key in cog.DIFFICULTY_MULTIPLIERS.keys()]
            super().__init__(placeholder="Choisissez une difficulté...", options=options, row=0); self.guild_id, self.cog = guild_id, cog
        async def callback(self, interaction: discord.Interaction):
            await interaction.response.defer(); db = SessionLocal()
            try:
                state = db.query(ServerState).filter_by(guild_id=self.guild_id).first(); state.game_mode = self.values[0]
                self.cog._update_game_parameters(state); db.commit(); db.refresh(state)
                await interaction.edit_original_response(embed=self.cog.generate_mode_duration_embed(state), view=self.cog.generate_mode_duration_view(self.guild_id, state))
            finally: db.close()

    class GameDurationSelect(ui.Select):
        def __init__(self, guild_id: str, cog: 'AdminCog', current_duration: str):
            options = [discord.SelectOption(label=data["label"], value=key, default=(key == current_duration)) for key, data in cog.DURATION_SETTINGS.items()]
            super().__init__(placeholder="Choisissez une durée...", options=options, row=1); self.guild_id, self.cog = guild_id, cog
        async def callback(self, interaction: discord.Interaction):
            await interaction.response.defer(); db = SessionLocal()
            try:
                state = db.query(ServerState).filter_by(guild_id=self.guild_id).first(); state.duration_key = self.values[0]
                self.cog._update_game_parameters(state); db.commit(); db.refresh(state)
                await interaction.edit_original_response(embed=self.cog.generate_mode_duration_embed(state), view=self.cog.generate_mode_duration_view(self.guild_id, state))
            finally: db.close()

    class GeneralConfigButton(ui.Button):
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle, row: int, cog: 'AdminCog', disabled: bool = False):
            super().__init__(label=label, style=style, row=row, disabled=disabled, emoji="⚙️"); self.guild_id, self.cog = guild_id, cog
        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            try:
                state = db.query(ServerState).filter_by(guild_id=self.guild_id).one()
                await interaction.response.edit_message(embed=self.cog.generate_role_and_channel_config_embed(state), view=self.cog.generate_general_config_view(self.guild_id, interaction.guild))
            finally: db.close()

    def generate_role_and_channel_config_embed(self, state: ServerState) -> discord.Embed:
        embed = discord.Embed(title="⚙️ Rôles & Salons", color=discord.Color.purple())
        admin_role = f"<@&{state.admin_role_id}>" if state.admin_role_id else "Non défini"
        game_channel = f"<#{state.game_channel_id}>" if state.game_channel_id else "Non défini"
        embed.add_field(name="👑 Rôle Admin", value=f"Actuel: {admin_role}", inline=False)
        embed.add_field(name="🎮 Salon de Jeu", value=f"Actuel: {game_channel}", inline=False)
        return embed

    def generate_general_config_view(self, guild_id: str, guild: discord.Guild) -> ui.View:
        view = ui.View(timeout=180); view.add_item(self.OpenPaginatorButton("Définir Rôle Admin", guild_id, "admin_role", 0, self))
        view.add_item(self.OpenPaginatorButton("Définir Salon de Jeu", guild_id, "game_channel", 1, self))
        view.add_item(self.BackButton("Retour", guild_id, discord.ButtonStyle.secondary, 2, self))
        return view

    class OpenPaginatorButton(ui.Button):
        def __init__(self, label: str, guild_id: str, select_type: Literal['admin_role', 'game_channel'], row: int, cog: 'AdminCog'):
            super().__init__(label=label, style=discord.ButtonStyle.primary, row=row); self.guild_id, self.select_type, self.cog = guild_id, select_type, cog
        async def callback(self, interaction: discord.Interaction):
            item_list = interaction.guild.roles if self.select_type == "admin_role" else [ch for ch in interaction.guild.channels if isinstance(ch, discord.TextChannel)]
            item_type_str = "role" if self.select_type == "admin_role" else "channel"
            options, id_mapping = self.cog.create_options_and_mapping(item_list, item_type_str, interaction.guild)
            await interaction.response.edit_message(embed=discord.Embed(title=f"Configuration: {self.label}"), view=PaginatedViewManager(self.guild_id, options, id_mapping, self.select_type, self.cog))

    def generate_config_menu_embed(self, state: ServerState) -> discord.Embed:
        embed = discord.Embed(title="⚙️ Configuration du Bot", color=discord.Color.blue())
        difficulty = state.game_mode or "medium"; duration_key = state.duration_key or "real_time"
        mode_str = f"`{difficulty.capitalize()}`"; duration_str = f"`{self.DURATION_SETTINGS.get(duration_key, {}).get('label')}`"
        embed.add_field(name="▶️ Statut", value=f"**Jeu:** `{'En cours' if state.game_started else 'Non démarré'}`", inline=False)
        embed.add_field(name="🕹️ Paramètres", value=f"**Difficulté:** {mode_str}\n**Échelle de Temps:** {duration_str}", inline=False)
        admin_role = f"<@&{state.admin_role_id}>" if state.admin_role_id else 'Non défini'
        game_channel = f"<#{state.game_channel_id}>" if state.game_channel_id else 'Non défini'
        embed.add_field(name="📍 Serveur", value=f"**Rôle Admin:** {admin_role}\n**Salon de Jeu:** {game_channel}", inline=False)
        embed.set_footer(text="Les changements de difficulté/durée sont bloqués pendant une partie.")
        return embed

    def generate_config_menu_view(self, guild_id: str, guild: discord.Guild, state: ServerState) -> ui.View:
        view = ui.View(timeout=None); is_game_running = state.game_started
        start_label, start_emoji, start_style = ("Arrêter", "⏹️", discord.ButtonStyle.danger) if is_game_running else ("Démarrer", "▶️", discord.ButtonStyle.success)
        view.add_item(self.ModeAndDurationButton("Difficulté & Durée", guild_id, discord.ButtonStyle.primary, 0, self, disabled=is_game_running))
        view.add_item(self.ConfigButton(start_label, start_emoji, guild_id, start_style, 0, self))
        view.add_item(self.GeneralConfigButton("Rôles & Salons", guild_id, discord.ButtonStyle.primary, 0, self, disabled=is_game_running))
        view.add_item(self.ConfigButton("Notifications", "🔔", guild_id, discord.ButtonStyle.primary, 1, self))
        return view

    class BackButton(ui.Button):
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle, row: int, cog: 'AdminCog', target_menu: str = "main"):
            super().__init__(label=label, style=style, row=row, emoji="⬅️"); self.guild_id, self.cog, self.target_menu = guild_id, cog, target_menu
        async def callback(self, interaction: discord.Interaction):
            await interaction.response.defer(); db = SessionLocal()
            try:
                state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()
                if self.target_menu == "notifications_config":
                    embed, view = self.cog.generate_notifications_config_embed(state), self.cog.generate_notifications_config_view(self.guild_id, interaction.guild)
                else:
                    embed, view = self.cog.generate_config_menu_embed(state), self.cog.generate_config_menu_view(self.guild_id, interaction.guild, state)
                await interaction.edit_original_response(embed=embed, view=view, content=None)
            finally: db.close()

    class ConfigButton(ui.Button):
        def __init__(self, label: str, emoji: str, guild_id: str, style: discord.ButtonStyle, row: int, cog: 'AdminCog'):
            super().__init__(label=label, emoji=emoji, style=style, row=row)
            self.guild_id = guild_id
            self.cog = cog
            self._view = None

        @property
        def view(self) -> Optional[ui.View]:
            return self._view

        @view.setter
        def view(self, value: Optional[ui.View]):
            self._view = value

        async def callback(self, interaction: discord.Interaction):
            if not interaction.guild:
                await interaction.response.send_message("Cette action doit être effectuée dans un serveur.", ephemeral=True)
                return

            label = self.label or ""
            
            if "Arrêter" in label:
                await interaction.response.send_modal(StopGameConfirmationModal(self.guild_id, self.cog))
                return
            
            await interaction.response.defer()
            db = SessionLocal()
            try:
                state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()
                if not state:
                    await interaction.followup.send("État du serveur introuvable.", ephemeral=True)
                    return
                    
                followup_message = None

                label = self.label or ""
                if "Démarrer" in label:
                    if not state.game_channel_id:
                        followup_message = ("❌ Erreur: Veuillez configurer un salon de jeu avant de démarrer.", True)
                    else:
                        logger.info(f"Starting new game in guild {self.guild_id}")
                        main_embed_cog = self.cog.bot.get_cog("MainEmbed")
                        cooker_brain = self.cog.bot.get_cog("CookerBrain")
                        player = db.query(PlayerProfile).filter_by(guild_id=self.guild_id).first()
                        utc_now = get_utc_now()
                        
                        # Initialize new player if needed
                        if not player:
                            logger.info(f"Creating new player profile for guild {self.guild_id}")
                            player = PlayerProfile(
                                guild_id=self.guild_id,
                                last_update=utc_now,

                                # === SECTION 1: PHYSICAL HEALTH CORE ===
                                health=100.0,
                                energy=100.0,
                                stamina=100.0,
                                pain=0.0,
                                immune_system=100.0,
                                toxicity=0.0,
                                body_temperature=37.0,
                                blood_pressure=120.0,
                                heart_rate=70.0,

                                # === SECTION 2: IMMEDIATE NEEDS ===
                                hunger=0.0,
                                thirst=0.0,
                                bladder=0.0,
                                fatigue=0.0,
                                bowels=0.0,
                                comfort=100.0,
                                temperature_comfort=100.0,
                                sleep_quality=100.0,

                                # === SECTION 3: MENTAL & EMOTIONAL STATE ===
                                # Core Mood Components
                                emotional_stability=70.0,
                                contentment=65.0,
                                mood_volatility=30.0,
                                emotional_resilience=75.0,
                                
                                # Emotional States
                                happiness=70.0,
                                joy=65.0,
                                satisfaction=60.0,
                                enthusiasm=75.0,
                                serenity=55.0,
                                anxiety=20.0,
                                depression=10.0,
                                stress=25.0,
                                anger=5.0,
                                fear=15.0,
                                frustration=20.0,
                                irritability=15.0,

                                # Cognitive States
                                mental_clarity=100.0,
                                concentration=100.0,
                                memory_function=100.0,
                                decision_making=100.0,
                                creativity=50.0,
                                cognitive_load=0.0,

                                # Social States
                                social_anxiety=20.0,
                                social_energy=100.0,
                                environmental_stress=0.0,
                                sensory_overload=0.0,
                                loneliness=0.0,

                                # === SECTION 4: SYMPTOMS ===
                                nausea=0.0,
                                dizziness=0.0,
                                headache=0.0,
                                muscle_tension=0.0,
                                joint_pain=0.0,
                                back_pain=0.0,
                                dry_mouth=0.0,
                                sore_throat=0.0,
                                chest_tightness=0.0,
                                breathing_difficulty=0.0,
                                tremors=0.0,
                                cold_sweats=0.0,
                                stomachache=0.0,
                                nausea_intensity=0.0,
                                appetite=100.0,
                                digestion=100.0,

                                # === SECTION 5: ADDICTION ===
                                nicotine_addiction=0.0,
                                alcohol_addiction=0.0,
                                cannabis_addiction=0.0,
                                caffeine_addiction=0.0,
                                substance_tolerance=0.0,
                                withdrawal_severity=0.0,
                                physical_dependence=0.0,
                                psychological_dependence=0.0,
                                recovery_progress=0.0,
                                relapse_risk=0.0,
                                trigger_sensitivity=50.0,
                                stress_trigger_level=0.0,
                                social_trigger_level=0.0,
                                craving_nicotine=0.0,
                                craving_alcohol=0.0,
                                craving_cannabis=0.0,
                                guilt=0.0,
                                shame=0.0,
                                hopelessness=0.0,
                                determination=100.0,
                                
                                # Game-specific stats
                                willpower=85.0,
                                hygiene=100.0,
                                job_performance=100.0
                            )
                            db.add(player)

                        # Auto-initialize cook's state based on time with high willpower
                        # The initial state is based on the real-world time.
                        localized_now = to_localized(utc_now)
                        logger.info(f"Initializing game state at {localized_now.strftime('%H:%M')} localized time.")

                        if is_wt(localized_now):
                            player.is_working = True
                            player.last_action = "working"
                            player.last_worked_at = utc_now
                            player.willpower = 80  # High initial willpower
                            message = "Le cuisinier démarre en pleine journée de travail."
                            logger.info("Player initialized at work")
                        elif is_lb(localized_now):
                            player.is_working = False
                            player.last_action = "neutral"
                            player.willpower = 80  # High initial willpower
                            message = "Le cuisinier démarre pendant sa pause déjeuner."
                            logger.info("Player initialized during lunch break")
                        else:
                            player.is_working = False
                            player.last_action = "neutral"
                            player.willpower = 80  # High initial willpower
                            message = "Le cuisinier démarre à son domicile."
                            logger.info("Player initialized at home")

                        state.game_started = True
                        state.game_start_time = prepare_for_db(utc_now)  # Store as naive UTC
                        state.is_test_mode = (state.duration_key == 'test')
                        
                        db.commit()
                        db.refresh(player)
                        db.refresh(state)
                        
                        game_channel = await self.cog.bot.fetch_channel(state.game_channel_id)
                        game_message = await game_channel.send(
                            embed=main_embed_cog.generate_dashboard_embed(player, state, interaction.guild),
                            view=DashboardView(player)
                        )
                        state.game_message_id = game_message.id
                        db.commit()
                        
                        followup_message = (f"✅ {message} Le jeu démarre dans {game_channel.mention} !", True)

                elif "Notifications" in (self.label or ""):
                    db.refresh(state) # Assurer que l'état est à jour avant de changer de vue
                    embed = self.cog.generate_notifications_config_embed(state)
                    view = self.cog.generate_notifications_config_view(self.guild_id, interaction.guild)
                    await interaction.edit_original_response(embed=embed, view=view)
                    return # Pas de refresh général à la fin

                # --- MISE À JOUR FINALE ET UNIVERSELLE DE L'INTERFACE ---
                db.refresh(state)
                embed = self.cog.generate_config_menu_embed(state)
                view = self.cog.generate_config_menu_view(self.guild_id, interaction.guild, state)
                await interaction.edit_original_response(embed=embed, view=view)

                if followup_message:
                    await interaction.followup.send(followup_message[0], ephemeral=followup_message[1])

            except Exception as e:
                logger.error(f"Erreur dans ConfigButton callback: {e}", exc_info=True)
                if not interaction.is_expired():
                    await interaction.followup.send("Une erreur critique est survenue.", ephemeral=True)
                db.rollback()
            finally:
                db.close()

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
    await bot.add_cog(AdminDebugCommands(bot))