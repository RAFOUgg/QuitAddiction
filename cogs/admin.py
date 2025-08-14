# --- cogs/admin.py (CORRECTED & REFACTORED) ---

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

# --- Centralized Imports ---
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
    """Gestion des configurations du bot et du jeu pour le serveur."""
    def __init__(self, bot):
        self.bot = bot
    
    BASE_DAILY_RATES = {"hunger": 150, "thirst": 200, "bladder": 120, "stress": 40, "boredom": 200, "hygiene": 100}
    DIFFICULTY_MULTIPLIERS = {"peaceful": 0.75, "medium": 1.0, "hard": 1.5}
    DURATION_SETTINGS = {
        "test_day": {"minutes_per_day": 24, "label": "Test (Jour = 24 mins)"},
        "day": {"minutes_per_day": 1440, "label": "Jour (Jour = 24h)"},
        "short": {"minutes_per_day": 10080, "label": "Court (Jour = 7 jours)"},
        "medium": {"minutes_per_day": 20160, "label": "Moyen (Jour = 14 jours)"},
        "long": {"minutes_per_day": 43200, "label": "Long (Jour = 30 jours)"},
    }

    def _update_game_parameters(self, state: ServerState):
        difficulty = state.game_mode or "medium"
        duration_key = state.duration_key or "day"
        multiplier = self.DIFFICULTY_MULTIPLIERS.get(difficulty, 1.0)
        duration_setting = self.DURATION_SETTINGS.get(duration_key, self.DURATION_SETTINGS["day"])
        for rate_name, base_value in self.BASE_DAILY_RATES.items():
            setattr(state, f"degradation_rate_{rate_name}", base_value * multiplier)
        state.game_minutes_per_day = duration_setting["minutes_per_day"]
        logger.info(f"Paramètres de jeu mis à jour pour {state.guild_id}: Diff={difficulty}, Durée={duration_key}")

    @app_commands.command(name="config", description="Configure les paramètres du bot et du jeu pour le serveur.")
    @app_commands.default_permissions(administrator=True)
    async def config(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        db = SessionLocal()
        try:
            state = db.query(ServerState).filter_by(guild_id=str(interaction.guild.id)).first()
            if not state:
                state = ServerState(guild_id=str(interaction.guild.id))
                self._update_game_parameters(state)
                db.add(state); db.commit(); db.refresh(state)
            await interaction.followup.send(
                embed=self.generate_config_menu_embed(state),
                view=self.generate_config_menu_view(str(interaction.guild.id), interaction.guild, state),
            )
        finally:
            db.close()
            
    def create_options_and_mapping(self, items: list, item_type: str, guild: discord.Guild | None) -> Tuple[List[discord.SelectOption], Dict[str, str]]:
        options, id_mapping = [], {}
        if item_type == "role": sorted_items = sorted(items, key=lambda x: x.position, reverse=True)
        else: sorted_items = sorted(items, key=lambda x: x.position)
        
        for item in sorted_items:
            if item_type == "role" and item.is_default(): continue
            item_id, item_name = str(item.id), item.name
            label = f"🔹 {item_name}" if item_type == "role" else f"#{item_name}"
            hashed_id = hashlib.sha256(item_id.encode()).hexdigest()[:25]
            options.append(discord.SelectOption(label=label[:100], value=hashed_id, description=f"ID: {item_id}"))
            id_mapping[hashed_id] = item_id
        if not options: options.append(discord.SelectOption(label="Aucun item trouvé", value="no_items"))
        return options, id_mapping

    # --- Section: Configuration des Notifications ---
    def generate_notifications_config_embed(self, state: ServerState) -> discord.Embed:
        embed = discord.Embed(title="🔔 Configuration des Rôles de Notification", color=discord.Color.gold())
        roles = { "Général": state.notification_role_id, "Vitals Faibles": state.notify_vital_low_role_id, "Événement Critique": state.notify_critical_role_id,
                  "Manque / Envies": state.notify_craving_role_id, "Message Ami": state.notify_friend_message_role_id, "Promotion Boutique": state.notify_shop_promo_role_id }
        value = "\n".join([f"**{name}:** {f'<@&{role_id}>' if role_id else 'Non défini'}" for name, role_id in roles.items()])
        embed.add_field(name="Rôles Actuels", value=value)
        embed.set_footer(text="Utilisez les menus pour configurer les rôles.")
        return embed

    class NotificationRoleTypeSelect(ui.Select):
        def __init__(self, guild_id: str, cog: 'AdminCog'):
            self.guild_id, self.cog = guild_id, cog
            options = [ discord.SelectOption(label="Rôle de notification général", value="notification_role_id"),
                        discord.SelectOption(label="Rôle pour Vitals Faibles", value="notify_vital_low_role_id"),
                        discord.SelectOption(label="Rôle pour Événement Critique", value="notify_critical_role_id"),
                        discord.SelectOption(label="Rôle pour Manque / Envies", value="notify_craving_role_id"),
                        discord.SelectOption(label="Rôle pour Message Ami", value="notify_friend_message_role_id"),
                        discord.SelectOption(label="Rôle pour Promotion Boutique", value="notify_shop_promo_role_id")]
            self.options_map = {opt.value: opt.label for opt in options}
            super().__init__(placeholder="Choisir le type de notification à configurer...", options=options, row=0)

        async def callback(self, interaction: discord.Interaction):
            setting_key = self.values[0]
            all_roles = interaction.guild.roles
            options, id_mapping = self.cog.create_options_and_mapping(all_roles, "role", interaction.guild)
            view = ui.View()
            select_menu = RoleSelect(self.guild_id, setting_key, id_mapping, self.cog)
            select_menu.options = options[:25] 
            view.add_item(select_menu)
            view.add_item(self.cog.BackButton("Retour", self.guild_id, discord.ButtonStyle.secondary, 1, self.cog, target_menu="notifications_config"))
            await interaction.response.edit_message(content=f"Sélectionnez le rôle pour : **{self.options_map[setting_key]}**", embed=None, view=view)

    def generate_notifications_config_view(self, guild_id: str, guild: discord.Guild) -> ui.View:
        view = ui.View(timeout=180)
        view.add_item(self.NotificationRoleTypeSelect(guild_id, self))
        # NOUVELLE LOGIQUE: On ajoute le menu déroulant directement, en lui passant la liste des rôles
        view.add_item(SetAllNotificationsRoleSelect(guild_id, self, guild.roles))
        view.add_item(self.BackButton("Retour au menu principal", guild_id, discord.ButtonStyle.red, 2, self))
        return view

    # --- Section: Difficulté et Durée ---
    class ModeAndDurationButton(ui.Button):
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle, row: int, cog: 'AdminCog', disabled: bool = False):
            super().__init__(label=label, style=style, row=row, disabled=disabled, emoji="🕹️")
            self.guild_id = guild_id; self.cog = cog
        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            try:
                state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()
                await interaction.response.edit_message(
                    embed=self.cog.generate_mode_duration_embed(state), 
                    view=self.cog.generate_mode_duration_view(self.guild_id, state)
                )
            finally: db.close()
    
    def generate_mode_duration_embed(self, state: ServerState) -> discord.Embed:
        embed = discord.Embed(title="🎮 Difficulté & Durée", color=discord.Color.teal())
        difficulty = state.game_mode or "medium"; duration_key = state.duration_key or "day"
        embed.add_field(name="Difficulté Actuelle", value=f"`{difficulty.capitalize()}` (Multiplicateur: x{self.DIFFICULTY_MULTIPLIERS.get(difficulty, 1.0)})", inline=False)
        embed.add_field(name="Durée Actuelle", value=f"`{self.DURATION_SETTINGS.get(duration_key, {}).get('label')}`", inline=False)
        return embed

    def generate_mode_duration_view(self, guild_id: str, state: ServerState) -> ui.View:
        view = ui.View(timeout=180)
        view.add_item(self.GameDifficultySelect(guild_id, self, state.game_mode))
        view.add_item(self.GameDurationSelect(guild_id, self, state.duration_key))
        view.add_item(self.BackButton("Retour", guild_id, discord.ButtonStyle.secondary, 2, self))
        return view

    class GameDifficultySelect(ui.Select):
        def __init__(self, guild_id: str, cog: 'AdminCog', current_difficulty: str):
            options = [discord.SelectOption(label=key.capitalize(), value=key, default=(key == current_difficulty)) for key in cog.DIFFICULTY_MULTIPLIERS.keys()]
            super().__init__(placeholder="Choisissez une difficulté...", options=options, row=0)
            self.guild_id, self.cog = guild_id, cog
        async def callback(self, interaction: discord.Interaction):
            await interaction.response.defer()
            db = SessionLocal()
            try:
                state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()
                state.game_mode = self.values[0]
                self.cog._update_game_parameters(state); db.commit(); db.refresh(state)
                await interaction.edit_original_response(embed=self.cog.generate_mode_duration_embed(state), view=self.cog.generate_mode_duration_view(self.guild_id, state))
            finally: db.close()

    class GameDurationSelect(ui.Select):
        def __init__(self, guild_id: str, cog: 'AdminCog', current_duration: str):
            options = [discord.SelectOption(label=data["label"], value=key, default=(key == current_duration)) for key, data in cog.DURATION_SETTINGS.items()]
            super().__init__(placeholder="Choisissez une durée...", options=options, row=1)
            self.guild_id, self.cog = guild_id, cog
        async def callback(self, interaction: discord.Interaction):
            await interaction.response.defer()
            db = SessionLocal()
            try:
                state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()
                state.duration_key = self.values[0]
                self.cog._update_game_parameters(state); db.commit(); db.refresh(state)
                await interaction.edit_original_response(embed=self.cog.generate_mode_duration_embed(state), view=self.cog.generate_mode_duration_view(self.guild_id, state))
            finally: db.close()

    # --- Section: Configuration Générale (Rôles & Salons) ---
    class GeneralConfigButton(ui.Button):
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle, row: int, cog: 'AdminCog', disabled: bool = False):
            super().__init__(label=label, style=style, row=row, disabled=disabled, emoji="⚙️")
            self.guild_id, self.cog = guild_id, cog
        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            try:
                state = db.query(ServerState).filter_by(guild_id=self.guild_id).one()
                await interaction.response.edit_message(embed=self.cog.generate_role_and_channel_config_embed(state),
                                                         view=self.cog.generate_general_config_view(self.guild_id, interaction.guild))
            finally: db.close()

    def generate_role_and_channel_config_embed(self, state: ServerState) -> discord.Embed:
        embed = discord.Embed(title="⚙️ Rôles & Salons", color=discord.Color.purple())
        admin_role = f"<@&{state.admin_role_id}>" if state.admin_role_id else "Non défini"
        game_channel = f"<#{state.game_channel_id}>" if state.game_channel_id else "Non défini"
        embed.add_field(name="👑 Rôle Admin", value=f"Actuel: {admin_role}", inline=False)
        embed.add_field(name="🎮 Salon de Jeu", value=f"Actuel: {game_channel}", inline=False)
        return embed

    def generate_general_config_view(self, guild_id: str, guild: discord.Guild) -> ui.View:
        view = ui.View(timeout=180)
        view.add_item(self.OpenPaginatorButton("Définir Rôle Admin", guild_id, "admin_role", 0, self))
        view.add_item(self.OpenPaginatorButton("Définir Salon de Jeu", guild_id, "game_channel", 1, self))
        view.add_item(self.BackButton("Retour", guild_id, discord.ButtonStyle.secondary, 2, self))
        return view

    class OpenPaginatorButton(ui.Button):
        def __init__(self, label: str, guild_id: str, select_type: Literal['admin_role', 'game_channel'], row: int, cog: 'AdminCog'):
            super().__init__(label=label, style=discord.ButtonStyle.primary, row=row)
            self.guild_id, self.select_type, self.cog = guild_id, select_type, cog
        async def callback(self, interaction: discord.Interaction):
            item_list = interaction.guild.roles if self.select_type == "admin_role" else \
                        [ch for ch in interaction.guild.channels if isinstance(ch, discord.TextChannel)]
            item_type_str = "role" if self.select_type == "admin_role" else "channel"
            options, id_mapping = self.cog.create_options_and_mapping(item_list, item_type_str, interaction.guild)
            await interaction.response.edit_message(
                embed=discord.Embed(title=f"Configuration: {self.label}"),
                view=PaginatedViewManager(self.guild_id, options, id_mapping, self.select_type, self.cog)
            )

    # --- Menu Principal et Boutons ---
    def generate_config_menu_embed(self, state: ServerState) -> discord.Embed:
        embed = discord.Embed(title="⚙️ Configuration du Bot", color=discord.Color.blue())
        difficulty = state.game_mode or "medium"; duration_key = state.duration_key or "day"
        mode_str = f"`{difficulty.capitalize()}`"; duration_str = f"`{self.DURATION_SETTINGS.get(duration_key, {}).get('label')}`"
        embed.add_field(name="▶️ Statut", value=f"**Jeu:** `{'En cours' if state.game_started else 'Non démarré'}`", inline=False)
        embed.add_field(name="🕹️ Paramètres", value=f"**Difficulté:** {mode_str}\n**Échelle de Temps:** {duration_str}", inline=False)
        admin_role = f"<@&{state.admin_role_id}>" if state.admin_role_id else 'Non défini'
        game_channel = f"<#{state.game_channel_id}>" if state.game_channel_id else 'Non défini'
        embed.add_field(name="📍 Serveur", value=f"**Rôle Admin:** {admin_role}\n**Salon de Jeu:** {game_channel}", inline=False)
        embed.set_footer(text="Les changements de difficulté/durée sont bloqués pendant une partie.")
        return embed

    def generate_config_menu_view(self, guild_id: str, guild: discord.Guild, state: ServerState) -> ui.View:
        view = ui.View(timeout=None)
        is_game_running = state.game_started
        start_label, start_emoji, start_style = ("Arrêter", "⏹️", discord.ButtonStyle.danger) if is_game_running else ("Démarrer", "▶️", discord.ButtonStyle.success)
        
        view.add_item(self.ModeAndDurationButton("Difficulté & Durée", guild_id, discord.ButtonStyle.primary, 0, self, disabled=is_game_running))
        view.add_item(self.ConfigButton(start_label, start_emoji, guild_id, start_style, 0, self))
        view.add_item(self.GeneralConfigButton("Rôles & Salons", guild_id, discord.ButtonStyle.primary, 0, self, disabled=is_game_running))
        view.add_item(self.ConfigButton("Notifications", "🔔", guild_id, discord.ButtonStyle.primary, 1, self))
        return view
        
    class BackButton(ui.Button):
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle, row: int, cog: 'AdminCog', target_menu: str = "main"):
            super().__init__(label=label, style=style, row=row, emoji="⬅️")
            self.guild_id, self.cog, self.target_menu = guild_id, cog, target_menu
        async def callback(self, interaction: discord.Interaction):
            await interaction.response.defer()
            db = SessionLocal()
            try:
                state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()
                if self.target_menu == "notifications_config":
                    embed = self.cog.generate_notifications_config_embed(state)
                    view = self.cog.generate_notifications_config_view(self.guild_id, interaction.guild)
                else: # main menu
                    embed = self.cog.generate_config_menu_embed(state)
                    view = self.cog.generate_config_menu_view(self.guild_id, interaction.guild, state)
                await interaction.edit_original_response(embed=embed, view=view, content=None)
            finally: db.close()

    class ConfigButton(ui.Button):
        def __init__(self, label: str, emoji: str, guild_id: str, style: discord.ButtonStyle, row: int, cog: 'AdminCog'):
            super().__init__(label=label, emoji=emoji, style=style, row=row)
            self.guild_id, self.label, self.cog = guild_id, label, cog
        
        async def callback(self, interaction: discord.Interaction):
            if "Arrêter" in self.label:
                await interaction.response.send_modal(StopGameConfirmationModal(self.guild_id, self.cog)); return

            await interaction.response.defer()
            db = SessionLocal()
            try:
                state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()
                if "Démarrer" in self.label:
                    if not state.game_channel_id:
                        await interaction.followup.send("❌ Erreur: Veuillez configurer un salon de jeu.", ephemeral=True); return
                    main_embed_cog = self.cog.bot.get_cog("MainEmbed")
                    player = db.query(PlayerProfile).filter_by(guild_id=self.guild_id).first()
                    now = datetime.datetime.utcnow()
                    if not player:
                        player = PlayerProfile(guild_id=self.guild_id, last_update=now)
                        db.add(player)
                    state.game_started, state.game_start_time = True, now
                    db.commit(); db.refresh(player); db.refresh(state)
                    game_channel = await self.cog.bot.fetch_channel(state.game_channel_id)
                    game_message = await game_channel.send(embed=main_embed_cog.generate_dashboard_embed(player, state, interaction.guild),
                                                           view=DashboardView(player))
                    state.game_message_id = game_message.id; db.commit()
                    await interaction.edit_original_response(embed=self.cog.generate_config_menu_embed(state), view=self.cog.generate_config_menu_view(self.guild_id, interaction.guild, state))
                    await interaction.followup.send(f"✅ Le jeu a démarré dans {game_channel.mention}.", ephemeral=True)
                
                elif "Notifications" in self.label:
                    await interaction.edit_original_response(
                        embed=self.cog.generate_notifications_config_embed(state),
                        view=self.cog.generate_notifications_config_view(self.guild_id, interaction.guild)
                    )
            finally:
                db.close()

async def setup(bot):
    await bot.add_cog(AdminCog(bot))