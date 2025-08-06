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
        view = discord.ui.View(timeout=180) # Set a timeout for the view

        # Keep track of how many components are on each row
        # We initialize this to zeros and it will be updated as we add items.
        # The index represents the row number (0-4).
        rows_item_count = [0] * 5

        def add_component_to_view(component: discord.ui.Item):
            """
            Helper function to add a component to the view.
            It tries to place the component on the first available row (0-4).
            If a row is full (5 items), it tries the next row.
            """
            # Check if component already has a row assigned and if that row has space
            if component.row is not None and component.row < 5 and rows_item_count[component.row] < 5:
                view.add_item(component)
                rows_item_count[component.row] += 1
                return True
            else:
                # If no row assigned, or current row is full, find the next available row
                for r in range(5): # Iterate through rows 0 to 4
                    if rows_item_count[r] < 5:
                        component.row = r # Assign the component to this row
                        view.add_item(component)
                        rows_item_count[r] += 1
                        return True
                print(f"WARNING: Could not add component {getattr(component, 'label', 'unknown')} to view - all rows are full (5 components per row).")
                return False

        # --- Creation des options et mapping ---
        def create_options_and_mapping(items, item_type):
            options = []
            id_mapping = {}
            if guild:
                try:
                    if item_type == "role":
                        sorted_items = sorted(items, key=lambda x: x.position, reverse=True)
                    elif item_type == "channel":
                        sorted_items = sorted(items, key=lambda x: (getattr(x, 'category_id', float('inf')), x.position))
                    else:
                        sorted_items = items
                except Exception as e:
                    print(f"Error sorting {item_type}s: {e}")
                    sorted_items = items

                for item in sorted_items:
                    item_id = str(item.id)
                    item_name = item.name
                    if item_id is None or not isinstance(item_name, str) or not item_name: continue
                    label = item_name[:self.MAX_OPTION_LENGTH]
                    if not label: label = item_id[:self.MAX_OPTION_LENGTH]
                    if not label: continue
                    hashed_id = hashlib.sha256(item_id.encode()).hexdigest()
                    value = hashed_id[:self.MAX_OPTION_LENGTH]
                    if not value: continue
                    if not (self.MIN_OPTION_LENGTH <= len(label) <= self.MAX_OPTION_LENGTH and self.MIN_OPTION_LENGTH <= len(value) <= self.MAX_OPTION_LENGTH): continue
                    options.append(discord.SelectOption(label=label, value=value, description=f"ID: {item_id}"))
                    id_mapping[value] = item_id
                if not options: options.append(discord.SelectOption(label="Aucun trouvé", value="no_items", default=True))
            else:
                options.append(discord.SelectOption(label="Erreur serveur", value="error_guild", default=True))
            return options, id_mapping

        all_roles = guild.roles if guild else []
        role_options, role_id_mapping = create_options_and_mapping(all_roles, "role")

        text_channels = [ch for ch in guild.channels if isinstance(ch, discord.TextChannel)] if guild else []
        all_channel_options, channel_id_mapping = create_options_and_mapping(text_channels, "channel")

        # --- Création des composants ---

        # Select pour le Rôle Admin
        # We initialize with row=0, but the helper will assign the final row.
        role_select_admin = self.RoleSelect(
            guild_id=guild_id,
            select_type="admin_role",
            row=0, # Initial row value, will be potentially updated by add_component_to_view
            options=role_options[:self.MAX_OPTION_LENGTH],
            id_mapping=role_id_mapping,
            cog=self
        )
        add_component_to_view(role_select_admin)

        # Select pour le Rôle de Notification
        role_select_notif = self.RoleSelect(
            guild_id=guild_id,
            select_type="notification_role",
            row=0, # Initial row value
            options=role_options[:self.MAX_OPTION_LENGTH],
            id_mapping=role_id_mapping,
            cog=self
        )
        add_component_to_view(role_select_notif)

        # --- Logique de pagination pour les salons ---
        channel_pagination_manager = self.ChannelPaginationManager(
            guild_id=guild_id,
            all_options=all_channel_options,
            id_mapping=channel_id_mapping,
            cog=self
        )

        # Add the channel select menu
        add_component_to_view(channel_pagination_manager.channel_select)

        # Add pagination buttons if needed
        if len(all_channel_options) > MAX_OPTIONS_PER_PAGE:
            add_component_to_view(channel_pagination_manager.prev_button)
            add_component_to_view(channel_pagination_manager.next_button)

        # Bouton de retour
        back_button = self.BackButton(
            "⬅ Retour Paramètres Jeu",
            guild_id,
            discord.ButtonStyle.secondary,
            cog=self
            # row will be assigned by add_component_to_view
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
    class ChannelPaginationManager(ui.View):
        def __init__(self, guild_id: str, all_options: list[discord.SelectOption], id_mapping: dict, initial_page: int = 0, cog: 'AdminCog'=None):
            super().__init__(timeout=180) # Définir un timeout pour la vue
            self.guild_id = guild_id
            self.all_options = all_options
            self.id_mapping = id_mapping
            self.current_page = initial_page
            self.cog = cog # Stocker l'instance du cog

            # Créer le SelectMenu pour la page initiale.
            # Le row sera géré lorsque ce SelectMenu est ajouté à la vue principale.
            self.channel_select = AdminCog.ChannelSelect( # Utilisation de AdminCog.ChannelSelect
                guild_id=self.guild_id,
                select_type="game_channel",
                row=0, # Ce row sera écrasé par la vue principale qui l'ajoute
                options=self.all_options,
                id_mapping=self.id_mapping,
                page=self.current_page,
                cog=self.cog # Passer self.cog
            )
            
            # Créer les boutons de navigation. Les custom_ids sont statiques pour être trouvés par les listeners.
            self.prev_button = ui.Button(
                label="⬅ Précédent",
                style=discord.ButtonStyle.secondary,
                custom_id=f"channel_prev_page_{self.guild_id}", # Static custom_id pour la navigation
                disabled=self.current_page == 0, # Désactiver si c'est la première page
                row=1 # Les boutons seront placés sur la ligne 1
            )
            self.next_button = ui.Button(
                label="Suivant ➡",
                style=discord.ButtonStyle.secondary,
                custom_id=f"channel_next_page_{self.guild_id}", # Static custom_id pour la navigation
                disabled=(self.current_page + 1) * MAX_OPTIONS_PER_PAGE >= len(self.all_options), # Désactiver si c'est la dernière page
                row=1 # Les boutons seront placés sur la ligne 1
            )
            
            # Attacher manuellement les callbacks aux boutons. Ceci est une alternative à l'utilisation de @ui.button
            # pour les vues qui gèrent elles-mêmes la logique de mise à jour.
            self.prev_button.callback = self.handle_prev_page
            self.next_button.callback = self.handle_next_page

        # Méthode pour mettre à jour les composants de la vue (Select et Boutons)
        def update_components(self, interaction: discord.Interaction):
            # Pour mettre à jour la vue, nous devons la modifier.
            # On retire l'ancien SelectMenu et on ajoute le nouveau.
            self.remove_item(self.channel_select) # Retirer l'ancien Select

            # Créer le nouveau SelectMenu pour la page mise à jour.
            self.channel_select = AdminCog.ChannelSelect( # Utilisation de AdminCog.ChannelSelect
                guild_id=self.guild_id,
                select_type="game_channel",
                row=0, # Le row est important car le SelectMenu est ajouté dans la vue principale.
                       # On le remet à 0 ici pour qu'il s'insère correctement.
                options=self.all_options,
                id_mapping=self.id_mapping,
                page=self.current_page,
                cog=self.cog # Passer self.cog
            )
            self.add_item(self.channel_select) # Ajouter le nouveau Select

            # Mettre à jour l'état désactivé des boutons de pagination.
            self.prev_button.disabled = self.current_page == 0
            self.next_button.disabled = (self.current_page + 1) * MAX_OPTIONS_PER_PAGE >= len(self.all_options)

        # Callback pour le bouton "Précédent"
        async def handle_prev_page(self, interaction: discord.Interaction):
            # On vérifie si l'utilisateur qui clique est bien celui qui a ouvert la config.
            # Ou, si vous voulez une sécurité plus stricte, vérifiez s'il est admin.
            # Pour l'instant, on suppose que tout utilisateur interagissant avec la vue peut naviguer.
            # Si vous voulez restreindre, ajoutez une vérification ici. Par exemple:
            # if interaction.user.id != self.interaction_user_id: # Nécessite de stocker l'ID de l'utilisateur initial
            #     await interaction.response.send_message("Vous n'êtes pas autorisé à naviguer.", ephemeral=True)
            #     return

            if self.current_page > 0:
                self.current_page -= 1
                self.update_components(interaction) # Mettre à jour les composants (Select et boutons)
                # Éditer le message avec la vue mise à jour.
                await interaction.response.edit_message(view=self)
            else:
                await interaction.response.send_message("C'est la première page.", ephemeral=True)

        # Callback pour le bouton "Suivant"
        async def handle_next_page(self, interaction: discord.Interaction):
            # Similaire à handle_prev_page pour les vérifications d'utilisateur.
            if (self.current_page + 1) * MAX_OPTIONS_PER_PAGE < len(self.all_options):
                self.current_page += 1
                self.update_components(interaction) # Mettre à jour les composants (Select et boutons)
                # Éditer le message avec la vue mise à jour.
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