# --- cogs/admin.py ---

import discord
from discord.ext import commands
from discord import app_commands, ui
from db.database import SessionLocal
from db.models import ServerState, PlayerProfile
import hashlib
import datetime
import math
from typing import List, Tuple, Dict, Optional

# Constante pour le nombre maximum d'options par page
MAX_OPTIONS_PER_PAGE = 25 # Discord limite à 25 options par SelectMenu

class AdminCog(commands.Cog):
    """Gestion des configurations du bot et du jeu pour le serveur."""
    def __init__(self, bot):
        self.bot = bot

    # --- Préréglages des Modes de Jeu ---
    GAME_MODES = {
        "peaceful": {
            "tick_interval_minutes": 60,
            "rates": {
                "hunger": 5.0, "thirst": 4.0, "bladder": 5.0,
                "energy": 3.0, "stress": 1.0, "boredom": 2.0,
                "addiction_base": 0.05, "toxins_base": 0.1,
            }
        },
        "medium": {
            "tick_interval_minutes": 30,
            "rates": {
                "hunger": 10.0, "thirst": 8.0, "bladder": 15.0,
                "energy": 5.0, "stress": 3.0, "boredom": 7.0,
                "addiction_base": 0.1, "toxins_base": 0.5,
            }
        },
        "hard": {
            "tick_interval_minutes": 15,
            "rates": {
                "hunger": 20.0, "thirst": 16.0, "bladder": 30.0,
                "energy": 10.0, "stress": 6.0, "boredom": 14.0,
                "addiction_base": 0.2, "toxins_base": 1.0,
            }
        }
    }
    
    # --- Préréglages des Durées de Partie ---
    GAME_DURATIONS = {
        "short": {"days": 14, "label": "Court (14 jours)"},
        "medium": {"days": 31, "label": "Moyen (31 jours)"},
        "long": {"days": 72, "label": "Long (72 jours)"},
    }

    # Limites pour les labels et valeurs des options de SelectMenu selon Discord API
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
    
    def create_options_and_mapping(self, items: list, item_type: str, guild: discord.Guild | None) -> Tuple[List[discord.SelectOption], Dict[str, str]]:
        """
        Crée des listes d'options Discord (discord.SelectOption) et un mapping ID pour les menus déroulants.
        Permet de convertir des objets (rôles, canaux) en options sélectionnables.

        Args:
            items (list): Une liste d'objets Discord (ex: discord.Role, discord.TextChannel).
            item_type (str): Le type d'objet pour adapter le tri et la logique ('role' ou 'channel').
            guild (discord.Guild | None): L'objet Guild pour accéder aux propriétés spécifiques comme la position des rôles ou des canaux.

        Returns:
            Tuple[List[discord.SelectOption], Dict[str, str]]: 
            Une paire contenant:
            1. Une liste d'objets discord.SelectOption prêts à être utilisés dans un menu déroulant.
            2. Un dictionnaire mappant les valeurs hachées uniques (short_id) aux IDs originaux des objets (item_id).
        """
        options = []
        id_mapping = {}
        
        # Gestion d'erreur si la guild n'est pas trouvée (ex: dans certains contextes de test ou de réponse différée)
        if not guild:
            return [discord.SelectOption(label="Erreur serveur", value="error_guild", default=True)], {}

        try:
            # Tri des éléments pour une meilleure organisation dans le menu déroulant.
            if item_type == "role":
                # Les rôles sont triés par position, du plus élevé (haut du serveur) au plus bas.
                sorted_items = sorted(items, key=lambda x: x.position, reverse=True)
            elif item_type == "channel":
                # Les canaux sont triés d'abord par catégorie (les canaux sans catégorie en dernier),
                # puis par position au sein de leur catégorie.
                sorted_items = sorted(items, key=lambda x: (getattr(x, 'category_id', float('inf')), x.position))
            else:
                # Pas de tri spécifique pour d'autres types d'éléments.
                sorted_items = items
        except Exception as e:
            # En cas d'erreur lors du tri, log l'erreur et continue avec les éléments non triés.
            print(f"Error sorting {item_type}s: {e}")
            sorted_items = items

        # Limites pour les labels et valeurs des options de SelectMenu selon Discord API
        MAX_OPTION_LENGTH = 25 # Max 25 caractères pour label et value
        MIN_OPTION_LENGTH = 1  # Min 1 caractère

        # Itération sur les éléments triés pour créer les options du menu.
        for item in sorted_items:
            # Ignorer les éléments qui n'ont pas d'ID ou dont le nom n'est pas valide.
            item_id = str(item.id)
            item_name = item.name
            if item_id is None or not isinstance(item_name, str) or not item_name:
                continue

            # Créer le label : on tronque le nom de l'élément à la longueur maximale.
            label = item_name[:MAX_OPTION_LENGTH]
            # Si le label tronqué est vide, utiliser l'ID tronqué (cas très rare).
            if not label:
                label = item_id[:MAX_OPTION_LENGTH]
            if not label: # Si même l'ID tronqué est vide, on ignore cet élément.
                continue

            # Créer une valeur unique et hachée pour l'option.
            # Cela permet de créer une valeur courte et unique pour Discord.
            # Le hachage SHA256 est utilisé pour garantir l'unicité et la sécurité.
            hashed_id = hashlib.sha256(item_id.encode()).hexdigest()
            value = hashed_id[:MAX_OPTION_LENGTH] # Tronquer la valeur hachée.
            if not value: # Si la valeur hachée tronquée est vide, on ignore.
                continue

            # Vérifier que le label et la valeur respectent les contraintes de longueur.
            if not (MIN_OPTION_LENGTH <= len(label) <= MAX_OPTION_LENGTH and MIN_OPTION_LENGTH <= len(value) <= MAX_OPTION_LENGTH):
                continue

            # Ajouter l'option à la liste. Le 'description' inclut l'ID original pour référence.
            options.append(discord.SelectOption(label=label, value=value, description=f"ID: {item_id}"))
            # Mappage de la valeur hachée (value) à l'ID original (item_id).
            id_mapping[value] = item_id

        # Si aucun élément valide n'a été trouvé, ajouter une option indiquant cela.
        if not options:
            options.append(discord.SelectOption(label="Aucun élément trouvé", value="no_items", default=True))

        # Retourner la liste d'options et le mapping d'IDs.
        return options, id_mapping
    
    def generate_config_menu_embed(self, state: ServerState) -> discord.Embed:
        embed = discord.Embed(
            title="⚙️ Configuration du Bot et du Jeu",
            description="Utilisez les boutons ci-dessous pour ajuster les paramètres du serveur.",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="▶️ **Statut Général**",
            value=f"**Jeu :** `{'En cours' if state.game_started else 'Non lancée'}`\n"
                  f"**Mode :** `{state.game_mode.capitalize() if state.game_mode else 'Medium (Standard)'}`\n"
                  f"**Durée :** `{self.GAME_DURATIONS.get(state.duration_key, {}).get('label', 'Moyen (31 jours)') if state.duration_key else 'Moyen (31 jours)'}`",
            inline=False
        )

        admin_role_mention = f"<@&{state.admin_role_id}>" if state.admin_role_id else "Non défini"
        notification_role_mention = f"<@&{state.notification_role_id}>" if hasattr(state, 'notification_role_id') and state.notification_role_id else "Non défini"
        game_channel_mention = f"<#{state.game_channel_id}>" if state.game_channel_id else "Non défini"
        
        embed.add_field(
            name="📍 **Configuration du Serveur**",
            value=f"**Rôle Admin :** {admin_role_mention}\n"
                  f"**Rôle Notification :** {notification_role_mention}\n"
                  f"**Salon de Jeu :** {game_channel_mention}",
            inline=False
        )

        tick_interval = state.game_tick_interval_minutes if state.game_tick_interval_minutes is not None else 30
        
        embed.add_field(
            name="⏱️ **Paramètres du Jeu**",
            value=f"**Intervalle Tick (min) :** `{tick_interval}`",
            inline=False
        )
        
        embed.add_field(
            name="📉 **Taux de Dégradation / Tick**",
            value=f"**Faim :** `{state.degradation_rate_hunger:.1f}` | **Soif :** `{state.degradation_rate_thirst:.1f}` | **Vessie :** `{state.degradation_rate_bladder:.1f}`\n"
                  f"**Énergie :** `{state.degradation_rate_energy:.1f}` | **Stress :** `{state.degradation_rate_stress:.1f}` | **Ennui :** `{state.degradation_rate_boredom:.1f}`",
            inline=False
        )
        
        embed.set_footer(text="Utilisez les boutons ci-dessous pour naviguer et modifier les paramètres.")
        return embed

    # --- Bouton pour lancer la sous-vue de sélection du Mode et Durée ---
    class SetupGameModeButton(ui.Button):
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle, row: int, cog: 'AdminCog'): # Ajout de cog
            super().__init__(label=label, style=style, row=row) 
            self.guild_id = guild_id
            self.cog = cog # Stocker l'instance du cog

        async def callback(self, interaction: discord.Interaction):
            await interaction.response.edit_message(
                embed=self.cog.generate_setup_game_mode_embed(),
                view=self.cog.generate_setup_game_mode_view(self.guild_id)
            )

    # --- Embed pour la sélection du Mode de Jeu et Durée ---
    def generate_setup_game_mode_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🎮 Configuration du Mode et de la Durée",
            description="Sélectionnez un mode de difficulté et une durée pour la partie.",
            color=discord.Color.teal()
        )
        return embed

    # --- View pour la sélection du Mode de Jeu et Durée ---
    def generate_setup_game_mode_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        view.add_item(self.GameModeSelect(guild_id, "mode", row=0, cog=self)) # Passer self
        view.add_item(self.GameDurationSelect(guild_id, "duration", row=1, cog=self)) # Passer self
        view.add_item(self.BackButton("⬅ Retour Paramètres Jeu", guild_id, discord.ButtonStyle.secondary, row=2, cog=self)) # Passer self
        return view

    # --- Classe de Menu: Mode de Difficulté (Peaceful, Medium, Hard) ---
    class GameModeSelect(ui.Select):
        def __init__(self, guild_id: str, select_type: str, row: int, cog: 'AdminCog'): # Ajout de cog
            options = [
                discord.SelectOption(label="Peaceful", description="Taux de dégradation bas.", value="peaceful"),
                discord.SelectOption(label="Medium (Standard)", description="Taux de dégradation standard.", value="medium"),
                discord.SelectOption(label="Hard", description="Taux de dégradation élevés. Plus difficile.", value="hard")
            ]
            super().__init__(placeholder="Choisissez le mode de difficulté...", options=options, custom_id=f"select_gamemode_{guild_id}", row=row)
            self.guild_id = guild_id
            self.cog = cog # Stocker l'instance du cog

        async def callback(self, interaction: discord.Interaction):
            selected_mode = self.values[0] # Assurez-vous que c'est bien self.values[0]
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()

            if state:
                mode_data = self.cog.GAME_MODES.get(selected_mode) # Utiliser self.cog

                if mode_data:
                    state.game_mode = selected_mode
                    state.game_tick_interval_minutes = mode_data["tick_interval_minutes"]
                    for key, value in mode_data["rates"].items():
                        setattr(state, f"degradation_rate_{key}", value)
                
                    db.commit()
                    
                    embed = self.cog.generate_setup_game_mode_embed() # Utiliser self.cog
                    embed.description = f"✅ Mode de difficulté défini sur **{selected_mode.capitalize()}**.\n" + embed.description
                    
                    await interaction.response.edit_message(embed=embed, view=self.cog.generate_setup_game_mode_view(self.guild_id)) # Utiliser self.cog
            
            db.close()

    # --- Classe de Menu: Durée de Partie (Short, Medium, Long) ---
    class GameDurationSelect(ui.Select):
        def __init__(self, guild_id: str, select_type: str, row: int, cog: 'AdminCog'): # Ajout de cog
            options = [
                discord.SelectOption(label=data["label"], value=key)
                for key, data in AdminCog.GAME_DURATIONS.items()
            ]
            super().__init__(placeholder="Choisissez la durée de la partie...", options=options, custom_id=f"select_gameduration_{guild_id}", row=row)
            self.guild_id = guild_id
            self.cog = cog # Stocker l'instance du cog

        async def callback(self, interaction: discord.Interaction):
            selected_duration_key = self.values[0] # Assurez-vous que c'est bien self.values[0]
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()

            if state:
                duration_data = self.cog.GAME_DURATIONS.get(selected_duration_key) # Utiliser self.cog
                
                if duration_data:
                    state.duration_key = selected_duration_key 
                    db.commit()
                    
                    embed = self.cog.generate_setup_game_mode_embed() # Utiliser self.cog
                    embed.description = f"✅ Durée de la partie définie sur **{duration_data['label']}**.\n" + embed.description
                    await interaction.response.edit_message(embed=embed, view=self.cog.generate_setup_game_mode_view(self.guild_id)) # Utiliser self.cog

            db.close()
            
    # --- Bouton de retour vers le Menu Principal des Paramètres ---
    class BackButton(ui.Button): 
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle, row: int = 0, cog: 'AdminCog'=None): # Ajout de cog
            super().__init__(label=label, style=style, row=row)
            self.guild_id = guild_id
            self.cog = cog # Stocker l'instance du cog
            
        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=str(self.guild_id)).first()
            
            await interaction.response.edit_message(
                embed=self.cog.generate_config_menu_embed(state), # Utiliser self.cog
                view=self.cog.generate_config_menu_view(self.guild_id, interaction.guild) # Utiliser self.cog
            )
            db.close()

    # --- Classe générique pour les boutons de configuration ---
    class ConfigButton(ui.Button):
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle, row: int, cog: 'AdminCog'): # Ajout de cog
            super().__init__(label=label, style=style, row=row)
            self.guild_id = guild_id
            self.label = label
            self.cog = cog # Stocker l'instance du cog

        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=str(self.guild_id)).first()

            if self.label == "🎮 Lancer/Reinitialiser Partie":
                if state:
                    state.game_started = not state.game_started
                    state.game_start_time = datetime.datetime.utcnow() if state.game_started else None
                    db.commit()
                    
                    await interaction.response.edit_message(
                        embed=self.cog.generate_config_menu_embed(state), # Utiliser self.cog
                        view=self.cog.generate_config_menu_view(self.guild_id, interaction.guild) # Utiliser self.cog
                    )
                    await interaction.followup.send(f"La partie a été {'lancée' if state.game_started else 'arrêtée/réinitialisée'}.", ephemeral=True)
                else:
                    await interaction.response.send_message("Erreur: Impossible de trouver l'état du serveur.", ephemeral=True)

            elif self.label == "💾 Sauvegarder l'État":
                # Si vous souhaitez que "Sauvegarder l'État" fasse quelque chose de plus,
                # implémentez la logique ici. Actuellement, il ne fait que rafraîchir la vue.
                await interaction.response.edit_message(
                    embed=self.cog.generate_config_menu_embed(state), # Utiliser self.cog
                    view=self.cog.generate_config_menu_view(self.guild_id, interaction.guild) # Utiliser self.cog
                )
                await interaction.followup.send("L'état actuel a été sauvegardé.", ephemeral=True) # Message informatif

            elif self.label == "📊 Voir Statistiques":
                await interaction.response.edit_message(
                    embed=self.cog.generate_stats_embed(self.guild_id), # Utiliser self.cog
                    view=self.cog.generate_stats_view(self.guild_id) # Utiliser self.cog
                )
                await interaction.followup.send("Accès aux statistiques...", ephemeral=True) # Message informatif

            elif self.label == "🔔 Notifications":
                await interaction.response.edit_message(
                    embed=self.cog.generate_notifications_embed(self.guild_id), # Utiliser self.cog
                    view=self.cog.generate_notifications_view(self.guild_id) # Utiliser self.cog
                )
                await interaction.followup.send("Accès à la configuration des notifications...", ephemeral=True) # Message informatif

            elif self.label == "🛠️ Options Avancées":
                await interaction.response.edit_message(
                    embed=self.cog.generate_advanced_options_embed(self.guild_id), # Utiliser self.cog
                    view=self.cog.generate_advanced_options_view(self.guild_id) # Utiliser self.cog
                )
                await interaction.followup.send("Accès aux options avancées...", ephemeral=True) # Message informatif

            db.close()

    # --- Bouton qui va ouvrir la configuration des rôles et salons ---
    class GeneralConfigButton(ui.Button):
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle, row: int, cog: 'AdminCog'): # Ajout de cog
            super().__init__(label=label, style=style, row=row) 
            self.guild_id = guild_id
            self.cog = cog # Stocker l'instance du cog

        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()

            # On passe le guild à la méthode de génération pour qu'elle puisse accéder aux rôles/canaux
            await interaction.response.edit_message(
                embed=self.cog.generate_role_and_channel_config_embed(state), # Utiliser self.cog
                view=self.cog.generate_general_config_view(self.guild_id, interaction.guild) # Utiliser self.cog
            )
            db.close()

    # --- Méthodes pour les configurations spécifiques (Rôle Admin, Salon, Rôle Notif) ---
    
    def generate_role_and_channel_config_embed(self, state: ServerState) -> discord.Embed:
        embed = discord.Embed(
            title="⚙️ Configuration Générale (Rôles & Salons)",
            description="Utilisez les menus déroulants pour sélectionner les rôles et salons.",
            color=discord.Color.purple()
        )
        current_admin_role = f"<@&{state.admin_role_id}>" if state.admin_role_id else "Non défini"
        current_notif_role = f"<@&{state.notification_role_id}>" if hasattr(state, 'notification_role_id') and state.notification_role_id else "Non défini"
        current_game_channel = f"<#{state.game_channel_id}>" if state.game_channel_id else "Non défini"

        embed.add_field(name="👑 Rôle Admin", value=current_admin_role, inline=False)
        embed.add_field(name="🔔 Rôle de Notification", value=current_notif_role, inline=False)
        embed.add_field(name="🎮 Salon de Jeu", value=current_game_channel, inline=False)
        return embed

    # --- Génération de la vue pour Rôles et Salons avec pagination pour les salons ---
    def generate_general_config_view(self, guild_id: str, guild: discord.Guild) -> discord.ui.View:
        view = discord.ui.View(timeout=180)
        rows_item_count = [0] * 5 # Track items per row

        def add_component_to_view(component: discord.ui.Item):
            """Helper to add a component to the view, managing rows up to MAX_COMPONENTS_PER_ROW."""
            if component.row is None or component.row >= 5: # If row is not set or invalid
                # Find the next available row
                for r in range(5):
                    if rows_item_count[r] < MAX_COMPONENTS_PER_ROW:
                        component.row = r # Assign the component to this row
                        break
                else: # No available row found
                    print(f"WARNING: Could not add component {getattr(component, 'label', 'unknown')} to view - all rows full (5 items per row).")
                    return # Don't add the component

            # Now that component.row is guaranteed to be set (0-4) and valid
            if rows_item_count[component.row] < MAX_COMPONENTS_PER_ROW:
                view.add_item(component)
                rows_item_count[component.row] += 1
            else:
                # This should ideally not happen if the above logic correctly assigns rows,
                # but as a fallback: try finding a new row if the intended one is full.
                # For robust row management, we should always try to find a row first.
                # Let's refine this logic.

                # --- Revised Row Assignment Strategy ---
                # We need to find the best row for the component.
                # Priority:
                # 1. If component.row is already set and valid, check if it has space.
                # 2. If not, find the first row with space.
                found_row = -1
                if component.row is not None and component.row < 5 and rows_item_count[component.row] < MAX_COMPONENTS_PER_ROW:
                    found_row = component.row
                else:
                    for r in range(5):
                        if rows_item_count[r] < MAX_COMPONENTS_PER_ROW:
                            found_row = r
                            break
                
                if found_row != -1:
                    component.row = found_row # Assign the found row
                    view.add_item(component)
                    rows_item_count[found_row] += 1
                else:
                    print(f"WARNING: Could not add component {getattr(component, 'label', 'unknown')} to view - all rows full.")


        # --- Prepare Data ---
        all_roles = guild.roles if guild else []
        role_options, role_id_mapping = self.create_options_and_mapping(all_roles, "role", guild)

        text_channels = [ch for ch in guild.channels if isinstance(ch, discord.TextChannel)] if guild else []
        channel_options, channel_id_mapping = self.create_options_and_mapping(text_channels, "channel", guild)

        # --- Create Pagination Managers ---
        # These managers will hold their respective select menus and buttons.
        admin_role_manager = self.PaginatedViewManager(
            guild_id=guild_id, all_options=role_options, id_mapping=role_id_mapping,
            select_type="admin_role", cog=self, initial_page=0
        )
        notification_role_manager = self.PaginatedViewManager(
            guild_id=guild_id, all_options=role_options, id_mapping=role_id_mapping,
            select_type="notification_role", cog=self, initial_page=0
        )
        channel_manager = self.PaginatedViewManager(
            guild_id=guild_id, all_options=channel_options, id_mapping=channel_id_mapping,
            select_type="channel", cog=self, initial_page=0
        )

        # --- Add Components FROM MANAGERS to View using the helper for row management ---
        # Add Admin Role Select Menu and its pagination buttons
        # The select_menu inside each manager already has row=0, and buttons have row=1.
        # The add_component_to_view helper handles placing them correctly in the main view.
        add_component_to_view(admin_role_manager.select_menu)
        if admin_role_manager.total_pages > 1:
            add_component_to_view(admin_role_manager.prev_button)
            add_component_to_view(admin_role_manager.next_button)

        # Add Notification Role Select Menu and its pagination buttons
        add_component_to_view(notification_role_manager.select_menu)
        if notification_role_manager.total_pages > 1:
            add_component_to_view(notification_role_manager.prev_button)
            add_component_to_view(notification_role_manager.next_button)

        # Add Channel Select Menu and its pagination buttons
        add_component_to_view(channel_manager.select_menu)
        if channel_manager.total_pages > 1:
            add_component_to_view(channel_manager.prev_button)
            add_component_to_view(channel_manager.next_button)

        # Back Button
        # Ensure cog=self is passed to BackButton as it's required by its callback.
        back_button = self.BackButton(
            "⬅ Retour Paramètres Jeu", guild_id, discord.ButtonStyle.secondary, cog=self
        )
        add_component_to_view(back_button)

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
    # Add 'select_type' to the __init__ signature
    def __init__(self, guild_id: str, all_options: list[discord.SelectOption], id_mapping: dict, select_type: str, initial_page: int = 0, cog: 'AdminCog'=None):
        super().__init__(timeout=180)
        self.guild_id = guild_id
        self.all_options = all_options
        self.id_mapping = id_mapping
        self.select_type = select_type # Store select_type here
        self.current_page = initial_page
        self.cog = cog

        # Create the appropriate SelectMenu based on select_type
        if self.select_type in ('admin_role', 'notification_role'):
            self.selection_menu = AdminCog.RoleSelect( # Use RoleSelect for roles
                guild_id=self.guild_id,
                select_type=self.select_type, # Pass select_type to RoleSelect
                row=0,
                options=self.all_options,
                id_mapping=self.id_mapping,
                cog=self.cog
            )
        elif self.select_type == 'channel':
            self.selection_menu = AdminCog.ChannelSelect( # Use ChannelSelect for channels
                guild_id=self.guild_id,
                select_type=self.select_type, # Pass select_type to ChannelSelect
                row=0,
                options=self.all_options,
                id_mapping=self.id_mapping,
                page=self.current_page,
                cog=self.cog
            )
        else:
            # Handle unknown select_type, though this shouldn't happen with current usage
            raise ValueError(f"Unknown select_type: {self.select_type}")

        # Buttons are generic, so their definition can remain similar
        self.prev_button = ui.Button(
            label="⬅ Précédent",
            style=discord.ButtonStyle.secondary,
            custom_id=f"pagination_{self.select_type}_prev_{self.guild_id}", # Use select_type in custom_id for better scoping
            disabled=self.current_page == 0,
            row=1
        )
        self.next_button = ui.Button(
            label="Suivant ➡",
            style=discord.ButtonStyle.secondary,
            custom_id=f"pagination_{self.select_type}_next_{self.guild_id}", # Use select_type in custom_id
            disabled=(self.current_page + 1) * MAX_OPTIONS_PER_PAGE >= len(self.all_options),
            row=1
        )
        
        self.prev_button.callback = self.handle_page_change
        self.next_button.callback = self.handle_page_change

    def update_components(self, interaction: discord.Interaction):
        # Remove old menu
        self.remove_item(self.selection_menu)

        # Create new menu for the updated page
        if self.select_type in ('admin_role', 'notification_role'):
            self.selection_menu = AdminCog.RoleSelect(
                guild_id=self.guild_id,
                select_type=self.select_type,
                row=0,
                options=self.all_options,
                id_mapping=self.id_mapping,
                cog=self.cog
            )
        elif self.select_type == 'channel':
            self.selection_menu = AdminCog.ChannelSelect(
                guild_id=self.guild_id,
                select_type=self.select_type,
                row=0,
                options=self.all_options,
                id_mapping=self.id_mapping,
                page=self.current_page,
                cog=self.cog
            )
        else:
            raise ValueError(f"Unknown select_type: {self.select_type}")
        self.add_item(self.selection_menu)

        # Update button states
        self.prev_button.disabled = self.current_page == 0
        self.next_button.disabled = (self.current_page + 1) * MAX_OPTIONS_PER_PAGE >= len(self.all_options)

    async def handle_page_change(self, interaction: discord.Interaction):
        if interaction.data['custom_id'].endswith('_prev'):
            if self.current_page > 0:
                self.current_page -= 1
                self.update_components(interaction)
                await interaction.response.edit_message(view=self)
            else:
                await interaction.response.send_message("C'est la première page.", ephemeral=True)
        else: # next
            if (self.current_page + 1) * MAX_OPTIONS_PER_PAGE < len(self.all_options):
                self.current_page += 1
                self.update_components(interaction)
                await interaction.response.edit_message(view=self)
            else:
                await interaction.response.send_message("C'est la dernière page.", ephemeral=True)

    # --- Méthodes pour les autres configurations (Statistiques, Notifications, Avancées) ---
    def generate_stats_embed(self, guild_id: str) -> discord.Embed:
        embed = discord.Embed(title="📊 Statistiques du Serveur", description="Fonctionnalité en développement.", color=discord.Color.purple())
        return embed
    
    def generate_stats_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        view.add_item(self.BackButton("⬅ Retour Paramètres Jeu", guild_id, discord.ButtonStyle.secondary, row=3, cog=self)) # Passer self
        return view

    def generate_notifications_embed(self, guild_id: str) -> discord.Embed:
        embed = discord.Embed(title="🔔 Paramètres de Notifications", description="Configurez les rôles pour les notifications du jeu. (Fonctionnalité en développement)", color=discord.Color.green())
        return embed
    
    def generate_notifications_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        view.add_item(self.BackButton("⬅ Retour Paramètres Jeu", guild_id, discord.ButtonStyle.secondary, row=3, cog=self)) # Passer self
        return view

    def generate_advanced_options_embed(self, guild_id: str) -> discord.Embed:
        embed = discord.Embed(title="🛠️ Options Avancées", description="Fonctionnalité en développement.", color=discord.Color.grey())
        return embed
    
    def generate_advanced_options_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        view.add_item(self.BackButton("⬅ Retour Paramètres Jeu", guild_id, discord.ButtonStyle.secondary, row=3, cog=self)) # Passer self
        return view

    # Méthode principale pour générer la vue du menu de configuration
    def generate_config_menu_view(self, guild_id: str, guild: discord.Guild) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        
        # Ligne 0 : Mode/Durée, Lancer/Réinitialiser, Sauvegarder
        view.add_item(self.SetupGameModeButton("🕹️ Mode & Durée", guild_id, discord.ButtonStyle.primary, row=0, cog=self)) # Passer self
        view.add_item(self.ConfigButton("🎮 Lancer/Reinitialiser Partie", guild_id, discord.ButtonStyle.success, row=0, cog=self)) # Passer self
        view.add_item(self.ConfigButton("💾 Sauvegarder l'État", guild_id, discord.ButtonStyle.blurple, row=0, cog=self)) # Passer self
        
        # Ligne 1 : Rôles & Salons, Statistiques
        view.add_item(self.GeneralConfigButton("⚙️ Rôles & Salons", guild_id, discord.ButtonStyle.grey, row=1, cog=self)) # Passer self
        view.add_item(self.ConfigButton("📊 Voir Statistiques", guild_id, discord.ButtonStyle.gray, row=1, cog=self)) # Passer self
        
        # Ligne 2 : Notifications, Options Avancées
        view.add_item(self.ConfigButton("🔔 Notifications", guild_id, discord.ButtonStyle.green, row=2, cog=self)) # Passer self
        view.add_item(self.ConfigButton("🛠 Options Avancées", guild_id, discord.ButtonStyle.secondary, row=2, cog=self)) # Passer self
        
        # Ligne 3 : Bouton retour final
        view.add_item(self.BackButton("⬅ Retour", guild_id, discord.ButtonStyle.red, row=3, cog=self)) # Passer self
        
        return view

async def setup(bot):
    await bot.add_cog(AdminCog(bot))