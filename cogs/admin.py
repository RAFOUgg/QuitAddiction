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
MAX_OPTIONS_PER_PAGE = 25

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
        """Génère l'embed principal affichant l'état actuel des configurations."""
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
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle, row: int):
            super().__init__(label=label, style=style, row=row) 
            self.guild_id = guild_id

        async def callback(self, interaction: discord.Interaction):
            cog = interaction.client.get_cog("AdminCog")
            if not cog:
                await interaction.response.send_message("Erreur: Le cog Admin n'est pas chargé.", ephemeral=True)
                return
            await interaction.response.edit_message(
                embed=cog.generate_setup_game_mode_embed(),
                view=cog.generate_setup_game_mode_view(self.guild_id)
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
        view.add_item(self.GameModeSelect(guild_id, "mode", row=0)) 
        view.add_item(self.GameDurationSelect(guild_id, "duration", row=1)) 
        view.add_item(self.BackButton("⬅ Retour Paramètres Jeu", guild_id, discord.ButtonStyle.secondary, row=2))
        return view

    # --- Classe de Menu: Mode de Difficulté (Peaceful, Medium, Hard) ---
    class GameModeSelect(ui.Select):
        def __init__(self, guild_id: str, select_type: str, row: int):
            options = [
                discord.SelectOption(label="Peaceful", description="Taux de dégradation bas.", value="peaceful"),
                discord.SelectOption(label="Medium (Standard)", description="Taux de dégradation standard.", value="medium"),
                discord.SelectOption(label="Hard", description="Taux de dégradation élevés. Plus difficile.", value="hard")
            ]
            super().__init__(placeholder="Choisissez le mode de difficulté...", options=options, custom_id=f"select_gamemode_{guild_id}", row=row)
            self.guild_id = guild_id

        async def callback(self, interaction: discord.Interaction):
            selected_mode = self.values[0]
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()

            if state:
                cog = interaction.client.get_cog("AdminCog")
                mode_data = cog.GAME_MODES.get(selected_mode)

                if mode_data:
                    state.game_mode = selected_mode
                    state.game_tick_interval_minutes = mode_data["tick_interval_minutes"]
                    for key, value in mode_data["rates"].items():
                        setattr(state, f"degradation_rate_{key}", value)
                
                    db.commit()
                    
                    embed = cog.generate_setup_game_mode_embed()
                    embed.description = f"✅ Mode de difficulté défini sur **{selected_mode.capitalize()}**.\n" + embed.description
                    
                    await interaction.response.edit_message(embed=embed, view=cog.generate_setup_game_mode_view(self.guild_id))
            
            db.close()

    # --- Classe de Menu: Durée de Partie (Short, Medium, Long) ---
    class GameDurationSelect(ui.Select):
        def __init__(self, guild_id: str, select_type: str, row: int):
            options = [
                discord.SelectOption(label=data["label"], value=key)
                for key, data in AdminCog.GAME_DURATIONS.items()
            ]
            super().__init__(placeholder="Choisissez la durée de la partie...", options=options, custom_id=f"select_gameduration_{guild_id}", row=row)
            self.guild_id = guild_id

        async def callback(self, interaction: discord.Interaction):
            selected_duration_key = self.values[0]
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()

            if state:
                cog = interaction.client.get_cog("AdminCog")
                if not cog:
                    await interaction.response.send_message("Erreur: Le cog Admin n'est pas chargé.", ephemeral=True)
                    db.close()
                    return
                    
                duration_data = cog.GAME_DURATIONS.get(selected_duration_key)
                
                if duration_data:
                    state.duration_key = selected_duration_key 
                    db.commit()
                    
                    embed = cog.generate_setup_game_mode_embed()
                    embed.description = f"✅ Durée de la partie définie sur **{duration_data['label']}**.\n" + embed.description
                    await interaction.response.edit_message(embed=embed, view=cog.generate_setup_game_mode_view(self.guild_id))

            db.close()
            
    # --- Bouton de retour vers le Menu Principal des Paramètres ---
    class BackButton(ui.Button): 
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle, row: int = 0):
            super().__init__(label=label, style=style, row=row)
            self.guild_id = guild_id
            
        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=str(self.guild_id)).first()
            cog = interaction.client.get_cog("AdminCog")

            if not cog:
                await interaction.response.send_message("Erreur: Le cog Admin n'est pas chargé.", ephemeral=True)
                db.close()
                return
            
            await interaction.response.edit_message(
                embed=cog.generate_config_menu_embed(state),
                view=cog.generate_config_menu_view(self.guild_id, interaction.guild) # Passer le guild ici aussi
            )
            db.close()

    # --- Classe générique pour les boutons de configuration ---
    class ConfigButton(ui.Button):
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle, row: int):
            super().__init__(label=label, style=style, row=row)
            self.guild_id = guild_id
            self.label = label

        async def callback(self, interaction: discord.Interaction):
            cog = interaction.client.get_cog("AdminCog")
            if not cog:
                await interaction.response.send_message("Erreur: Le cog Admin n'est pas chargé.", ephemeral=True)
                return

            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=str(self.guild_id)).first()

            if self.label == "🎮 Lancer/Reinitialiser Partie":
                if state:
                    state.game_started = not state.game_started
                    state.game_start_time = datetime.datetime.utcnow() if state.game_started else None
                    db.commit()
                    
                    await interaction.response.edit_message(
                        embed=cog.generate_config_menu_embed(state),
                        view=cog.generate_config_menu_view(self.guild_id, interaction.guild)
                    )
                    await interaction.followup.send(f"La partie a été {'lancée' if state.game_started else 'arrêtée/réinitialisée'}.", ephemeral=True)
                else:
                    await interaction.response.send_message("Erreur: Impossible de trouver l'état du serveur.", ephemeral=True)

            elif self.label == "💾 Sauvegarder l'État":
                await interaction.response.edit_message(
                    embed=cog.generate_config_menu_embed(state),
                    view=cog.generate_config_menu_view(self.guild_id, interaction.guild)
                )
                await interaction.followup.send("L'état actuel a été sauvegardé.", ephemeral=True)

            elif self.label == "📊 Voir Statistiques":
                await interaction.response.edit_message(
                    embed=cog.generate_stats_embed(self.guild_id),
                    view=cog.generate_stats_view(self.guild_id)
                )
                await interaction.followup.send("Affichage des statistiques...", ephemeral=True)

            elif self.label == "🔔 Notifications":
                await interaction.response.edit_message(
                    embed=cog.generate_notifications_embed(self.guild_id),
                    view=cog.generate_notifications_view(self.guild_id)
                )
                await interaction.followup.send("Configuration des notifications...", ephemeral=True)

            elif self.label == "🛠️ Options Avancées":
                await interaction.response.edit_message(
                    embed=cog.generate_advanced_options_embed(self.guild_id),
                    view=cog.generate_advanced_options_view(self.guild_id)
                )
                await interaction.followup.send("Accès aux options avancées...", ephemeral=True)

            db.close()

    # --- Bouton qui va ouvrir la configuration des rôles et salons ---
    class GeneralConfigButton(ui.Button):
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle, row: int):
            super().__init__(label=label, style=style, row=row) 
            self.guild_id = guild_id

        async def callback(self, interaction: discord.Interaction):
            cog = interaction.client.get_cog("AdminCog")
            if not cog:
                await interaction.response.send_message("Erreur: Le cog Admin n'est pas chargé.", ephemeral=True)
                return
            
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()

            # On passe le guild à la méthode de génération pour qu'elle puisse accéder aux rôles/canaux
            await interaction.response.edit_message(
                embed=cog.generate_role_and_channel_config_embed(state),
                # Ici, on appelle la méthode generate_general_config_view qui contient la logique de pagination
                view=cog.generate_general_config_view(self.guild_id, interaction.guild) 
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
        view = discord.ui.View(timeout=None)

        # Helper function to create options and a mapping
        def create_options_and_mapping(items, item_type):
            options = []
            id_mapping = {}

            if guild:
                sorted_items = sorted(items, key=lambda x: getattr(x, 'position', x.id))

                for item in sorted_items:
                    item_id = str(item.id)
                    item_name = item.name

                    if item_id is None or not isinstance(item_name, str) or not item_name:
                        print(f"DEBUG: Ignoré item (type: {item_type}) car ID nul ou nom invalide: ID={item_id}, Nom={item_name}")
                        continue

                    # Générer le label
                    label = item_name[:self.MAX_OPTION_LENGTH]
                    if not label:
                        label = item_id[:self.MAX_OPTION_LENGTH]
                        if not label:
                            print(f"DEBUG: Ignoré item (type: {item_type}) car aucun label valide généré: ID={item_id}, Nom='{item_name}'")
                            continue

                    # Générer la value
                    hashed_id = hashlib.sha256(item_id.encode()).hexdigest()
                    value = hashed_id[:self.MAX_OPTION_LENGTH]
                    if not value:
                        print(f"DEBUG: Ignoré item (type: {item_type}) car aucune value valide générée: ID={item_id}, Nom='{item_name}'")
                        continue

                    # Vérification finale des longueurs avant d'ajouter
                    if not (1 <= len(label) <= 25 and 1 <= len(value) <= 25):
                        print(f"DEBUG: ERREUR DE LONGUEUR - Ignoré item (type: {item_type})")
                        print(f"  -> Item original: ID='{item_id}', Nom='{item_name}'")
                        print(f"  -> Label généré : '{label}' (longueur: {len(label)})")
                        print(f"  -> Value générée: '{value}' (longueur: {len(value)})")
                        continue # Ignorer si les longueurs ne sont pas bonnes malgré tout

                    options.append(discord.SelectOption(label=label, value=value, description=f"ID: {item_id}"))
                    id_mapping[value] = item_id

                if not options:
                    options.append(discord.SelectOption(label="Aucun trouvé", value="no_items", description="Aucun item trouvé.", default=True))
            else:
                options.append(discord.SelectOption(label="Erreur serveur", value="error_guild", description="Serveur non trouvé.", default=True))
            
            return options, id_mapping

        # Générer les options et le mapping pour les rôles
        role_options, role_id_mapping = create_options_and_mapping(guild.roles if guild else [], "role")

        # Générer les options et le mapping pour les canaux textuels
        text_channels = [ch for ch in guild.channels if isinstance(ch, discord.TextChannel)] if guild else []
        channel_options_all, channel_id_mapping = create_options_and_mapping(text_channels, "channel")

        # Créer les instances de Select pour les rôles
        role_select_admin = self.RoleSelect(guild_id, "admin_role", row=0, options=role_options, id_mapping=role_id_mapping)
        view.add_item(role_select_admin)

        role_select_notif = self.RoleSelect(guild_id, "notification_role", row=1, options=role_options, id_mapping=role_id_mapping)
        view.add_item(role_select_notif)

        # --- Logique de pagination pour les salons ---
        # On crée ici la vue qui contiendra le select pour la page actuelle et les boutons de navigation
        # Correction: Utiliser self.ChannelSelectView pour faire référence à la classe imbriquée
        channel_select_view_container = self.ChannelSelectView(guild_id, channel_options_all, channel_id_mapping)
        view.add_item(channel_select_view_container) # Ajouter la sous-vue au menu principal

        view.add_item(self.BackButton("⬅ Retour Paramètres Jeu", guild_id, discord.ButtonStyle.secondary, row=3))
        return view

    # --- Classe de Menu pour la sélection des Rôles ---
    class RoleSelect(ui.Select):
        def __init__(self, guild_id: str, select_type: str, row: int, options: list[discord.SelectOption], id_mapping: dict):
            placeholder = f"Sélectionnez le rôle pour {'l\'admin' if select_type == 'admin_role' else 'les notifications'}..."
            placeholder = placeholder[:100] 
            super().__init__(placeholder=placeholder, options=options, custom_id=f"select_role_{select_type}_{guild_id}", row=row)
            self.guild_id = guild_id
            self.select_type = select_type
            self.id_mapping = id_mapping 

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

                    cog = interaction.client.get_cog("AdminCog")
                    await interaction.response.edit_message(
                        embed=cog.generate_role_and_channel_config_embed(state),
                        view=cog.generate_general_config_view(self.guild_id, interaction.guild)
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
        def __init__(self, guild_id: str, select_type: str, row: int, options: list[discord.SelectOption], id_mapping: dict, page: int = 0):
            self.guild_id = guild_id
            self.select_type = select_type
            self.id_mapping = id_mapping
            self.page = page

            # Filtrer les options pour la page actuelle
            start_index = page * MAX_OPTIONS_PER_PAGE
            end_index = start_index + MAX_OPTIONS_PER_PAGE
            current_page_options = options[start_index:end_index]

            if not current_page_options:
                current_page_options.append(discord.SelectOption(label="Aucun salon sur cette page", value="no_channels", default=True))

            placeholder = f"Sélectionnez le salon pour le jeu (Page {page + 1})..."
            placeholder = placeholder[:100]
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

                    cog = interaction.client.get_cog("AdminCog")
                    # On doit recharger la vue entière pour qu'elle soit mise à jour
                    await interaction.response.edit_message(
                        embed=cog.generate_role_and_channel_config_embed(state),
                        view=cog.generate_general_config_view(self.guild_id, interaction.guild)
                    )
                    await interaction.followup.send(f"Salon de jeu mis à jour.", ephemeral=True)
                except Exception as e:
                    db.rollback()
                    await interaction.response.send_message(f"Erreur lors de la sauvegarde : {e}", ephemeral=True)
            else:
                await interaction.response.send_message("Erreur: Impossible de trouver l'état du serveur pour sauvegarder la configuration.", ephemeral=True)
            
            db.close()

    # --- Classe pour gérer la vue paginée des salons ---
    # Important: Définir cette classe AVANT de l'utiliser dans generate_general_config_view
    class ChannelSelectView(ui.View):
        def __init__(self, guild_id: str, all_options: list[discord.SelectOption], id_mapping: dict, initial_page: int = 0):
            super().__init__(timeout=None)
            self.guild_id = guild_id
            self.all_options = all_options
            self.id_mapping = id_mapping
            self.current_page = initial_page
            self.update_view() # Appeler update_view() lors de l'initialisation

        def update_view(self):
            # Vider les items actuels avant de les redessiner
            self.clear_items()
            
            # Créer le select pour la page actuelle
            channel_select = AdminCog.ChannelSelect( # Correction ici: AdminCog.ChannelSelect
                guild_id=self.guild_id,
                select_type="game_channel",
                row=0, # Le select sera la première ligne dans cette vue
                options=self.all_options,
                id_mapping=self.id_mapping,
                page=self.current_page
            )
            self.add_item(channel_select)

            # Boutons de navigation
            if len(self.all_options) > MAX_OPTIONS_PER_PAGE:
                # Bouton précédent
                prev_button = ui.Button(
                    label="⬅ Précédent",
                    style=discord.ButtonStyle.secondary,
                    custom_id=f"channel_prev_page_{self.guild_id}_{self.current_page}", # Custom ID unique
                    disabled=self.current_page == 0
                )
                self.add_item(prev_button)

                # Bouton suivant
                next_button = ui.Button(
                    label="Suivant ➡",
                    style=discord.ButtonStyle.secondary,
                    custom_id=f"channel_next_page_{self.guild_id}_{self.current_page}", # Custom ID unique
                    disabled=(self.current_page + 1) * MAX_OPTIONS_PER_PAGE >= len(self.all_options)
                )
                self.add_item(next_button)

        # Les callbacks des boutons doivent maintenant être définis comme des méthodes de cette classe
        # et utiliser les décorateurs @ui.button
        
        # Note: Les custom_id dans les décorateurs doivent être uniques pour chaque instance si vous ne les passez pas explicitement
        # Ici, j'ai choisi de passer des custom_id dynamiques dans __init__ pour une meilleure gestion.
        # Si vous utilisez directement les noms des méthodes ici, assurez-vous que les custom_id sont cohérents.
        
        # Pour que cela fonctionne avec les custom_id que nous avons passés, il faut redéfinir les boutons
        # ou s'assurer que les custom_id ici correspondent à ceux ajoutés dans update_view.
        # Une approche plus simple est de déléguer la création des boutons et leur logique à update_view
        # et de gérer leurs interactions.

        # Dans ce cas, la meilleure pratique est que ChannelSelectView soit une classe qui "contient" les boutons.
        # Les actions sur ces boutons seront gérées par des méthodes qui modifient l'état de la vue.
        # Comme les buttons créés dans update_view ont des custom_id dynamiques, les callbacks (@ui.button) standards ne fonctionneront pas directement.
        # Il faut intercepter les interactions de ces boutons spécifiques.

        # Pour simplifier, je vais modifier update_view pour qu'il ajoute des boutons avec des custom_id
        # et je vais ajouter des callbacks *à ces boutons spécifiques* plutôt qu'utiliser les @ui.button.

        # Alternative: Créer les boutons directement dans __init__ avec leurs callbacks
        # Ce qui est plus propre: je vais modifier update_view pour qu'elle ajoute des `ui.Button`
        # et je vais attacher des callbacks à ces boutons directement.

        # Le problème est que `ui.View` ne maintient pas l'état pour les boutons ajoutés dynamiquement dans `update_view`
        # de manière persistante pour les interactions futures. Les boutons doivent être ajoutés à la vue une seule fois
        # dans `__init__` ou en gérant les `custom_id`.

        # Réajustement : on va plutôt laisser `update_view` définir les boutons, et intercepter les interactions via le `custom_id`
        # dans un callback global de la vue ou par un mécanisme plus avancé.
        # Pour une solution plus simple et directe:
        # Les `custom_id` que j'ai ajoutés dans `update_view` doivent être reconnus par Discord.
        # Les callbacks `@ui.button` recherchent ces `custom_id`. Si les `custom_id` changent dynamiquement,
        # les `@ui.button` ne les trouveront plus.
        # Il faut que les `custom_id` pour les boutons de pagination soient fixes une fois la vue initialisée.

        # Nouvelle approche pour les callbacks :
        # On va utiliser les `custom_id` fixes ici et modifier `update_view` pour les utiliser.

        # La structure actuelle avec `update_view` qui vide et redessine peut être problématique car Discord
        # attend que les `custom_id` soient cohérents entre les rendus de la vue.
        # Si `update_view` réécrit les boutons avec de NOUVEAUX `custom_id` (même s'ils semblent similaires),
        # Discord peut perdre le lien.

        # Solution plus robuste :
        # 1. Définir les boutons de navigation (Précédent, Suivant) dans `__init__` avec des `custom_id` fixes.
        # 2. Les rendre actifs/inactifs dans `update_view`.
        # 3. Les `custom_id` des boutons `ChannelSelect` sont aussi dynamiques, ce qui est une autre source de problème.
        # Les `custom_id` pour les Selects doivent être statiques aussi si on veut les callbacks `@ui.button`

        # Revenons à une approche plus standard :
        # Les `custom_id` doivent être statiques pour les callbacks `@ui.button`.
        # On ne va pas modifier le `Select` lui-même, mais les boutons autour.

        # Pour gérer la pagination, la vue `ChannelSelectView` elle-même va avoir des boutons.
        # `update_view` va modifier l'état (disabled) de ces boutons.

        # On va créer les boutons une fois dans __init__ et les mettre à jour.

    # --- Re-définition de ChannelSelectView pour une gestion statique des custom_id ---
    class ChannelSelectView(ui.View):
        def __init__(self, guild_id: str, all_options: list[discord.SelectOption], id_mapping: dict, initial_page: int = 0):
            super().__init__(timeout=None)
            self.guild_id = guild_id
            self.all_options = all_options
            self.id_mapping = id_mapping
            self.current_page = initial_page

            # Le Select itself will have a static custom_id if it needs to be interactive on its own
            # But here, we want pagination from buttons, so the Select is updated.
            
            # Create the ChannelSelect for the initial page
            self.channel_select = AdminCog.ChannelSelect(
                guild_id=self.guild_id,
                select_type="game_channel",
                row=0,
                options=self.all_options,
                id_mapping=self.id_mapping,
                page=self.current_page
            )
            self.add_item(self.channel_select)

            # Create navigation buttons with static custom_ids
            self.prev_button = ui.Button(
                label="⬅ Précédent",
                style=discord.ButtonStyle.secondary,
                custom_id=f"channel_prev_page_{self.guild_id}", # Static custom_id
                disabled=self.current_page == 0
            )
            self.next_button = ui.Button(
                label="Suivant ➡",
                style=discord.ButtonStyle.secondary,
                custom_id=f"channel_next_page_{self.guild_id}", # Static custom_id
                disabled=(self.current_page + 1) * MAX_OPTIONS_PER_PAGE >= len(self.all_options)
            )

            if len(self.all_options) > MAX_OPTIONS_PER_PAGE:
                self.add_item(self.prev_button)
                self.add_item(self.next_button)
        
        # We need to intercept interactions for the dynamically created ChannelSelect
        # Discord's `ui.View` handles interactions based on `custom_id` registered on the items.
        # Since `ChannelSelect` is created dynamically in `update_view` (in the old version),
        # the `custom_id` would change, breaking the link.
        # The current approach in `generate_general_config_view` adds a `ChannelSelectView` instance.
        # The `ChannelSelectView` now has a `self.channel_select` which needs to be managed.

        # Let's attach the callbacks directly to the items of this View.
        # This means the `self.channel_select` instance needs its callbacks handled,
        # and the buttons `self.prev_button` and `self.next_button` too.

        # Intercepting interactions for the ChannelSelect itself
        @ui.button(custom_id="handle_channel_select_interaction") # Placeholder, actual interaction handled by Discord
        async def handle_select_interaction(self, interaction: discord.Interaction):
            # This method is a placeholder and won't be called directly by discord.py for Selects.
            # Select callbacks are handled by the `callback` method of the `ui.Select` class itself.
            pass

        # Handling interactions for the navigation buttons
        @ui.button(custom_id=f"channel_prev_page_{self.guild_id}") # Matches the static custom_id
        async def prev_button_callback(self, interaction: discord.Interaction):
            if interaction.user.id != interaction.guild.owner_id: 
                await interaction.response.send_message("Vous n'êtes pas autorisé à changer de page.", ephemeral=True)
                return
            
            if self.current_page > 0:
                self.current_page -= 1
                self.update_display(interaction)
            else:
                await interaction.response.send_message("C'est la première page.", ephemeral=True)

        @ui.button(custom_id=f"channel_next_page_{self.guild_id}") # Matches the static custom_id
        async def next_button_callback(self, interaction: discord.Interaction):
            if interaction.user.id != interaction.guild.owner_id:
                await interaction.response.send_message("Vous n'êtes pas autorisé à changer de page.", ephemeral=True)
                return

            if (self.current_page + 1) * MAX_OPTIONS_PER_PAGE < len(self.all_options):
                self.current_page += 1
                self.update_display(interaction)
            else:
                await interaction.response.send_message("C'est la dernière page.", ephemeral=True)

        def update_display(self, interaction: discord.Interaction):
            # Update the ChannelSelect instance with the new page
            self.channel_select.page = self.current_page
            
            # Recalculate options for the new page
            start_index = self.current_page * MAX_OPTIONS_PER_PAGE
            end_index = start_index + MAX_OPTIONS_PER_PAGE
            current_page_options = self.all_options[start_index:end_index]

            if not current_page_options:
                current_page_options.append(discord.SelectOption(label="Aucun salon sur cette page", value="no_channels", default=True))
            
            # Update the select's options and custom_id (if needed, but page is in callback)
            self.channel_select.options = current_page_options
            self.channel_select.placeholder = f"Sélectionnez le salon pour le jeu (Page {self.current_page + 1})..."
            self.channel_select.custom_id = f"select_channel_game_channel_{self.guild_id}_page{self.current_page}" # Ensure custom_id is unique per page

            # Update buttons' disabled state
            self.prev_button.disabled = self.current_page == 0
            self.next_button.disabled = (self.current_page + 1) * MAX_OPTIONS_PER_PAGE >= len(self.all_options)

            # Edit the message to reflect the changes
            # We need to get the cog to regenerate the view if necessary, but here we only update the current view's items.
            # The `interaction.response.edit_message(view=self)` is done by the caller of update_display.
            # However, to re-render the entire view correctly, we should use interaction.message.edit.
            # The `update_display` method should be called within the interaction callback.
            
            # Let's assume the caller (previous/next button callback) will call interaction.response.edit_message(view=self)

            # To make this work, the buttons must be re-added to the view to reflect changes.
            # Or, we can modify the existing `self.channel_select` and `self.prev_button`, `self.next_button` in place.
            # `discord.ui.View` is designed such that items are part of the view state.
            # When `interaction.response.edit_message(view=self)` is called, Discord will use the current state of `self`.
            
            # IMPORTANT: The `ui.Select` itself can have its options updated.
            # The `ui.Button` disabled status can be updated.
            # We need to ensure the `custom_id` of the `Select` is handled correctly.
            
            # The safest way is to re-create the items if significant changes are made,
            # but that can be complex. Let's try updating properties first.
            
            # The `self.channel_select` is an `ui.Select` instance. We modify its properties.
            # The `self.prev_button` and `self.next_button` are `ui.Button` instances. We modify their properties.

            # We DO NOT call `self.clear_items()` and `self.add_item()` here if we are just updating existing items.
            # We need to ensure the `custom_id` for the select is correctly associated.
            # When a `Select` is part of a View, its `callback` is invoked.
            # The `custom_id` of the `Select` is important for Discord to route interactions.
            # If the `custom_id` of the `Select` changes, Discord might not recognize it.

            # Let's refine the logic:
            # The `ChannelSelectView` manages the *state* of the pagination.
            # It has references to the `ChannelSelect` and the navigation `Button`s.
            # `update_display` modifies these references.
            # The `interaction.response.edit_message(view=self)` then tells Discord to re-render the view with the modified items.

            # The `custom_id` for the `ChannelSelect` is generated in its `__init__` and passed to the `Select` constructor.
            # If the `page` changes, the `custom_id` should ideally reflect that.
            # However, `ui.View` doesn't automatically re-register items with new `custom_id`s.

            # Alternative approach: Pass `custom_id` to `ChannelSelect` that already encodes page.
            # This is what `AdminCog.ChannelSelect` does.
            # When `update_display` is called, it needs to update the `custom_id` of `self.channel_select`.
            # This might be the issue.

            # Let's assume for now that updating the `options` and `placeholder` of the `self.channel_select` is enough
            # and that Discord will correctly route interactions to its `callback` based on the `custom_id` it was created with.
            # The `custom_id` for the select is `f"select_channel_{select_type}_{guild_id}_page{page}"`.
            # This means for each page, a new `custom_id` is generated for the select. This is problematic if `ChannelSelectView`
            # doesn't re-add the select item with the new `custom_id` to the view for the next interaction.

            # The `discord.ui.View` internally maps `custom_id` to items.
            # If `self.channel_select` is modified, the view needs to be aware of this.

            # Simpler fix: The `custom_id` for the `ChannelSelect` should not be dynamically generated in `__init__` if we want `custom_id` based callbacks.
            # However, the *page* needs to be known by the callback.
            # The `custom_id` for the `ChannelSelect` in `ChannelSelectView.__init__` IS passed to the `Select` constructor.
            # So, when `self.current_page` changes, the `self.channel_select` needs to be RE-CREATED or its `custom_id` updated and re-registered.

            # Let's re-create the `ChannelSelect` item within the view for each page update.
            # This means `update_display` needs to remove the old `Select` and add the new one.
            # `self.remove_item(self.channel_select)` before adding the new one.

            # Remove the old select
            self.remove_item(self.channel_select)

            # Create the new select for the updated page
            self.channel_select = AdminCog.ChannelSelect(
                guild_id=self.guild_id,
                select_type="game_channel",
                row=0,
                options=self.all_options,
                id_mapping=self.id_mapping,
                page=self.current_page
            )
            self.add_item(self.channel_select) # Add the new select

            # Update buttons' disabled state
            self.prev_button.disabled = self.current_page == 0
            self.next_button.disabled = (self.current_page + 1) * MAX_OPTIONS_PER_PAGE >= len(self.all_options)

            # The edit_message call will happen from the button callbacks.
            # This `update_display` prepares the `self` view object for the edit.


    # --- Méthodes pour les autres configurations (Statistiques, Notifications, Avancées) ---
    def generate_stats_embed(self, guild_id: str) -> discord.Embed:
        embed = discord.Embed(title="📊 Statistiques du Serveur", description="Fonctionnalité en développement.", color=discord.Color.purple())
        return embed
    
    def generate_stats_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        view.add_item(self.BackButton("⬅ Retour Paramètres Jeu", guild_id, discord.ButtonStyle.secondary, row=3))
        return view

    def generate_notifications_embed(self, guild_id: str) -> discord.Embed:
        embed = discord.Embed(title="🔔 Paramètres de Notifications", description="Configurez les rôles pour les notifications du jeu. (Fonctionnalité en développement)", color=discord.Color.green())
        return embed
    
    def generate_notifications_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        view.add_item(self.BackButton("⬅ Retour Paramètres Jeu", guild_id, discord.ButtonStyle.secondary, row=3))
        return view

    def generate_advanced_options_embed(self, guild_id: str) -> discord.Embed:
        embed = discord.Embed(title="🛠️ Options Avancées", description="Fonctionnalité en développement.", color=discord.Color.grey())
        return embed
    
    def generate_advanced_options_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        view.add_item(self.BackButton("⬅ Retour Paramètres Jeu", guild_id, discord.ButtonStyle.secondary, row=3))
        return view

    # Méthode principale pour générer la vue du menu de configuration
    def generate_config_menu_view(self, guild_id: str, guild: discord.Guild) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        
        view.add_item(self.SetupGameModeButton("🕹️ Mode & Durée", guild_id, discord.ButtonStyle.primary, row=0))
        view.add_item(self.ConfigButton("🎮 Lancer/Reinitialiser Partie", guild_id, discord.ButtonStyle.success, row=0))
        view.add_item(self.ConfigButton("💾 Sauvegarder l'État", guild_id, discord.ButtonStyle.blurple, row=0))
        
        view.add_item(self.GeneralConfigButton("⚙️ Rôles & Salons", guild_id, discord.ButtonStyle.grey, row=1)) 
        view.add_item(self.ConfigButton("📊 Voir Statistiques", guild_id, discord.ButtonStyle.gray, row=1))
        
        view.add_item(self.ConfigButton("🔔 Notifications", guild_id, discord.ButtonStyle.green, row=2))
        view.add_item(self.ConfigButton("🛠 Options Avancées", guild_id, discord.ButtonStyle.secondary, row=2))
        
        view.add_item(self.BackButton("⬅ Retour", guild_id, discord.ButtonStyle.red, row=3))
        
        return view

async def setup(bot):
    await bot.add_cog(AdminCog(bot))