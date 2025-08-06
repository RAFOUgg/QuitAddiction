import discord
from discord.ext import commands
from discord import app_commands, ui
from db.database import SessionLocal
from db.models import ServerState, PlayerProfile
import hashlib
import datetime
import math

# --- Constantes pour la gestion des menus ---
MAX_OPTIONS_PER_SELECT = 25
MAX_LABEL_LENGTH = 100 # Limite pour le placeholder d'un Select
MAX_SELECT_OPTION_LABEL_LENGTH = 25 # Limite Discord pour le label d'une option
MAX_SELECT_OPTION_VALUE_LENGTH = 25 # Limite Discord pour la value d'une option

class AdminCog(commands.Cog):
    """Gestion des configurations du bot et du jeu pour le serveur."""
    def __init__(self, bot):
        self.bot = bot
        self.MAX_OPTION_LENGTH = MAX_SELECT_OPTION_LABEL_LENGTH # On utilise cette constante ici aussi

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

    # --- Méthodes pour les configurations spécifiques (Rôle Admin, Salon, Rôle Notif) ---
    
    def generate_role_and_channel_config_embed(self, state: ServerState) -> discord.Embed:
        embed = discord.Embed(
            title="⚙️ Configuration Générale (Rôles & Salons)",
            description="Utilisez les menus déroulants ci-dessous pour sélectionner les rôles et salons appropriés.",
            color=discord.Color.purple()
        )
        current_admin_role = f"<@&{state.admin_role_id}>" if state.admin_role_id else "Non défini"
        current_notif_role = f"<@&{state.notification_role_id}>" if hasattr(state, 'notification_role_id') and state.notification_role_id else "Non défini"
        current_game_channel = f"<#{state.game_channel_id}>" if state.game_channel_id else "Non défini"

        embed.add_field(name="👑 Rôle Admin", value=current_admin_role, inline=False)
        embed.add_field(name="🔔 Rôle de Notification", value=current_notif_role, inline=False)
        embed.add_field(name="🎮 Salon de Jeu", value=current_game_channel, inline=False)
        return embed

    # Vue pour la sélection des rôles et du salon
    def generate_general_config_view(self, guild_id: str, guild: discord.Guild) -> discord.ui.View:
        view = discord.ui.View(timeout=None)

        # Helper function to create options and a mapping
        def create_options_and_mapping(items, item_type):
            all_options = []
            id_mapping = {} 

            if guild:
                sorted_items = sorted(items, key=lambda x: getattr(x, 'position', x.id))

                for item in sorted_items:
                    item_id = str(item.id)
                    item_name = item.name

                    if item_id is None or not isinstance(item_name, str) or not item_name:
                        print(f"DEBUG: Ignoré item (type: {item_type}) car ID nul ou nom invalide: ID={item_id}, Nom={item_name}")
                        continue

                    # Préparer le label
                    label = item_name[:MAX_SELECT_OPTION_LABEL_LENGTH]
                    if not label:
                        label = item_id[:MAX_SELECT_OPTION_LABEL_LENGTH]
                        if not label:
                           print(f"DEBUG: Ignoré item (type: {item_type}) car aucun label valide généré: ID={item_id}, Nom='{item_name}'")
                           continue

                    # Préparer la value
                    hashed_id = hashlib.sha256(item_id.encode()).hexdigest()
                    value = hashed_id[:MAX_SELECT_OPTION_VALUE_LENGTH]
                    if not value:
                        print(f"DEBUG: Ignoré item (type: {item_type}) car aucune value valide générée: ID={item_id}, Nom='{item_name}'")
                        continue

                    # Vérification finale des longueurs avant d'ajouter
                    if not (1 <= len(label) <= MAX_SELECT_OPTION_LABEL_LENGTH and 1 <= len(value) <= MAX_SELECT_OPTION_VALUE_LENGTH):
                        print(f"DEBUG: ERREUR DE LONGUEUR - Ignoré item (type: {item_type})")
                        print(f"  -> Item original: ID='{item_id}', Nom='{item_name}'")
                        print(f"  -> Label généré : '{label}' (longueur: {len(label)})")
                        print(f"  -> Value générée: '{value}' (longueur: {len(value)})")
                        continue

                    print(f"DEBUG: Ajout option (type: {item_type}) - Label='{label}', Value='{value}', Desc='ID: {item_id}'")
                    
                    all_options.append(discord.SelectOption(label=label, value=value, description=f"ID: {item_id}"))
                    id_mapping[value] = item_id
                
                if not all_options:
                    all_options.append(discord.SelectOption(label="Aucun trouvé", value="no_items", description="Aucun item trouvé.", default=True))
            else:
                all_options.append(discord.SelectOption(label="Erreur serveur", value="error_guild", description="Serveur non trouvé.", default=True))
            
            return all_options, id_mapping

        # --- Génération des menus ---
        role_options, role_id_mapping = create_options_and_mapping(guild.roles if guild else [], "role")
        channel_options, channel_id_mapping = create_options_and_mapping(guild.text_channels if guild else [], "channel")

        # Créer des menus déroulants par lots de MAX_OPTIONS_PER_SELECT
        
        # Menus pour les rôles
        num_role_menus = math.ceil(len(role_options) / MAX_OPTIONS_PER_SELECT)
        for i in range(num_role_menus):
            start_index = i * MAX_OPTIONS_PER_SELECT
            end_index = start_index + MAX_OPTIONS_PER_SELECT
            current_role_options = role_options[start_index:end_index]
            
            # Créer un mapping réduit pour ce menu spécifique
            current_role_id_mapping = {opt.value: role_id_mapping[opt.value] for opt in current_role_options if opt.value in role_id_mapping}

            if current_role_options:
                placeholder = f"Sélectionnez le rôle admin (partie {i+1}/{num_role_menus})..."[:MAX_LABEL_LENGTH]
                role_select_admin = self.RoleSelect(guild_id, "admin_role", row=i, options=current_role_options, id_mapping=current_role_id_mapping, menu_index=i, total_menus=num_role_menus)
                view.add_item(role_select_admin)

        # Menus pour les canaux
        num_channel_menus = math.ceil(len(channel_options) / MAX_OPTIONS_PER_SELECT)
        for i in range(num_channel_menus):
            start_index = i * MAX_OPTIONS_PER_SELECT
            end_index = start_index + MAX_OPTIONS_PER_SELECT
            current_channel_options = channel_options[start_index:end_index]

            # Créer un mapping réduit pour ce menu spécifique
            current_channel_id_mapping = {opt.value: channel_id_mapping[opt.value] for opt in current_channel_options if opt.value in channel_id_mapping}

            if current_channel_options:
                placeholder = f"Sélectionnez le salon jeu (partie {i+1}/{num_channel_menus})..."[:MAX_LABEL_LENGTH]
                channel_select_game = self.ChannelSelect(guild_id, "game_channel", row=num_role_menus + i, options=current_channel_options, id_mapping=current_channel_id_mapping, menu_index=i, total_menus=num_channel_menus)
                view.add_item(channel_select_game)
        
        # Ajoutez un bouton de retour qui reste toujours visible
        view.add_item(self.BackButton("⬅ Retour Paramètres Jeu", guild_id, discord.ButtonStyle.secondary, row=num_role_menus + num_channel_menus))
        return view

    # Modifiez les classes RoleSelect et ChannelSelect pour accepter menu_index et total_menus
    class RoleSelect(ui.Select):
        def __init__(self, guild_id: str, select_type: str, row: int, options: list[discord.SelectOption], id_mapping: dict, menu_index: int, total_menus: int):
            placeholder = f"Sélectionnez le rôle pour {'l\'admin' if select_type == 'admin_role' else 'les notifications'} (partie {menu_index+1}/{total_menus})..."
            placeholder = placeholder[:MAX_LABEL_LENGTH]
            super().__init__(placeholder=placeholder, options=options, custom_id=f"select_role_{select_type}_{guild_id}_{menu_index}", row=row)
            self.guild_id = guild_id
            self.select_type = select_type
            self.id_mapping = id_mapping
            self.menu_index = menu_index
            self.total_menus = total_menus

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
                # Enregistrer la sélection pour cet index de menu
                if self.select_type == "admin_role":
                    # Si c'est le premier menu, on met à jour l'ID direct. Sinon, on ne fait rien pour l'instant
                    # La logique pour combiner les sélections multiples pour un même type est plus complexe
                    # Pour l'instant, on suppose que le premier menu est le principal pour l'admin/notif
                    if self.menu_index == 0:
                        state.admin_role_id = selected_role_id
                    else:
                        # Vous pourriez stocker les IDs dans une liste si un type peut avoir plusieurs menus
                        # ou simplement ignorer les sélections des menus suivants pour ce type
                        pass 
                elif self.select_type == "notification_role":
                    if self.menu_index == 0:
                        state.notification_role_id = selected_role_id
                    else:
                        pass # Ignorer les menus suivants pour notification_role pour l'instant

                try:
                    db.commit()
                    db.refresh(state) 

                    cog = interaction.client.get_cog("AdminCog")
                    # IMPORTANT: Pour gérer la logique multi-menus correctement lors d'une réponse,
                    # il faudrait rafraîchir la vue avec les bons menus.
                    # Pour l'instant, on se contente de rééditer le message avec l'embed et une vue qui pourrait être réinitialisée.
                    # Une gestion plus robuste impliquerait de sauvegarder les sélections intermédiaires.
                    await interaction.response.edit_message(
                        embed=cog.generate_role_and_channel_config_embed(state),
                        view=cog.generate_general_config_view(self.guild_id, interaction.guild) # Re-génère TOUS les menus
                    )
                    await interaction.followup.send(f"Rôle pour {'l\'administration' if self.select_type == 'admin_role' else 'les notifications'} mis à jour.", ephemeral=True)
                except Exception as e:
                    db.rollback()
                    await interaction.response.send_message(f"Erreur lors de la sauvegarde : {e}", ephemeral=True)
            else:
                await interaction.response.send_message("Erreur: Impossible de trouver l'état du serveur pour sauvegarder la configuration.", ephemeral=True)
            
            db.close()

    class ChannelSelect(ui.Select):
        def __init__(self, guild_id: str, select_type: str, row: int, options: list[discord.SelectOption], id_mapping: dict, menu_index: int, total_menus: int):
            placeholder = f"Sélectionnez le salon pour le jeu (partie {menu_index+1}/{total_menus})..."[:MAX_LABEL_LENGTH]
            super().__init__(placeholder=placeholder, options=options, custom_id=f"select_channel_{select_type}_{guild_id}_{menu_index}", row=row)
            self.guild_id = guild_id
            self.select_type = select_type
            self.id_mapping = id_mapping
            self.menu_index = menu_index
            self.total_menus = total_menus

        async def callback(self, interaction: discord.Interaction):
            if not interaction.guild:
                await interaction.response.send_message("Erreur: Impossible de trouver le serveur courant pour cette action.", ephemeral=True)
                return

            if not self.values or self.values[0] in ["no_items", "error_guild"]:
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
                # Enregistrer la sélection pour cet index de menu
                if self.select_type == "game_channel":
                    if self.menu_index == 0:
                        state.game_channel_id = selected_channel_id
                    else:
                        pass # Ignorer les menus suivants pour game_channel pour l'instant

                try:
                    db.commit()
                    db.refresh(state)

                    cog = interaction.client.get_cog("AdminCog")
                    await interaction.response.edit_message(
                        embed=cog.generate_role_and_channel_config_embed(state),
                        view=cog.generate_general_config_view(self.guild_id, interaction.guild) # Re-génère TOUS les menus
                    )
                    await interaction.followup.send(f"Salon de jeu mis à jour.", ephemeral=True)
                except Exception as e:
                    db.rollback()
                    await interaction.response.send_message(f"Erreur lors de la sauvegarde : {e}", ephemeral=True)
            else:
                await interaction.response.send_message("Erreur: Impossible de trouver l'état du serveur pour sauvegarder la configuration.", ephemeral=True)
            
            db.close()

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
    def generate_config_menu_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        
        # Ligne 0 : Mode & Durée, Lancer/Reinitialiser, Sauvegarder
        view.add_item(self.SetupGameModeButton("🕹️ Mode & Durée", guild_id, discord.ButtonStyle.primary, row=0))
        view.add_item(self.ConfigButton("🎮 Lancer/Reinitialiser Partie", guild_id, discord.ButtonStyle.success, row=0))
        view.add_item(self.ConfigButton("💾 Sauvegarder l'État", guild_id, discord.ButtonStyle.blurple, row=0))
        
        # Ligne 1 : Rôles & Salons, Statistiques
        view.add_item(self.GeneralConfigButton("⚙️ Rôles & Salons", guild_id, discord.ButtonStyle.grey, row=1)) 
        view.add_item(self.ConfigButton("📊 Voir Statistiques", guild_id, discord.ButtonStyle.gray, row=1))
        
        # Ligne 2 : Notifications, Options Avancées
        view.add_item(self.ConfigButton("🔔 Notifications", guild_id, discord.ButtonStyle.green, row=2))
        view.add_item(self.ConfigButton("🛠 Options Avancées", guild_id, discord.ButtonStyle.secondary, row=2))
        
        # Ligne 3 : Bouton retour final
        view.add_item(self.BackButton("⬅ Retour", guild_id, discord.ButtonStyle.red, row=3))
        
        return view

    # --- Boutons pour les différentes sections de configuration ---

    # Bouton pour lancer la sous-vue de sélection du Mode et Durée
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

    # Embed pour la sélection du Mode de Jeu et Durée
    def generate_setup_game_mode_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🎮 Configuration du Mode et de la Durée",
            description="Sélectionnez un mode de difficulté et une durée pour la partie.",
            color=discord.Color.teal()
        )
        return embed

    # View pour la sélection du Mode de Jeu et Durée
    def generate_setup_game_mode_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        view.add_item(self.GameModeSelect(guild_id, "mode", row=0)) 
        view.add_item(self.GameDurationSelect(guild_id, "duration", row=1)) 
        view.add_item(self.BackButton("⬅ Retour Paramètres Jeu", guild_id, discord.ButtonStyle.secondary, row=2))
        return view

    # Classe de Menu: Mode de Difficulté (Peaceful, Medium, Hard)
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

    # Classe de Menu: Durée de Partie (Short, Medium, Long)
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
            
    # Bouton de retour vers le Menu Principal des Paramètres
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
                view=cog.generate_config_menu_view(self.guild_id)      
            )
            db.close()

    # Classe générique pour les boutons de configuration
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
                        view=cog.generate_config_menu_view(self.guild_id)
                    )
                    await interaction.followup.send(f"La partie a été {'lancée' if state.game_started else 'arrêtée/réinitialisée'}.", ephemeral=True)
                else:
                    await interaction.response.send_message("Erreur: Impossible de trouver l'état du serveur.", ephemeral=True)

            elif self.label == "💾 Sauvegarder l'État":
                await interaction.response.edit_message(
                    embed=cog.generate_config_menu_embed(state),
                    view=cog.generate_config_menu_view(self.guild_id)
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

    # Bouton qui va ouvrir la configuration des rôles et salons
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

            await interaction.response.edit_message(
                embed=cog.generate_role_and_channel_config_embed(state),
                view=cog.generate_general_config_view(self.guild_id, interaction.guild) 
            )
            db.close()

    # --- Classes pour les menus déroulants (RoleSelect et ChannelSelect) ---
    class RoleSelect(ui.Select):
        def __init__(self, guild_id: str, select_type: str, row: int, options: list[discord.SelectOption], id_mapping: dict, menu_index: int, total_menus: int):
            placeholder = f"Sélectionnez le rôle pour {'l\'admin' if select_type == 'admin_role' else 'les notifications'} (partie {menu_index+1}/{total_menus})..."
            placeholder = placeholder[:MAX_LABEL_LENGTH]
            # IMPORTANT : custom_id doit être unique pour chaque menu déroulant
            super().__init__(placeholder=placeholder, options=options, custom_id=f"select_role_{select_type}_{guild_id}_{menu_index}", row=row)
            self.guild_id = guild_id
            self.select_type = select_type
            self.id_mapping = id_mapping 
            self.menu_index = menu_index
            self.total_menus = total_menus

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
                # Logique pour enregistrer la sélection.
                # Pour simplifier, on va juste prendre la sélection du premier menu si plusieurs menus sont utilisés pour le même type.
                # Une approche plus complète impliquerait de stocker toutes les sélections de manière persistante.
                if self.menu_index == 0: # On ne prend en compte que la sélection du premier menu pour l'instant
                    if self.select_type == "admin_role":
                        state.admin_role_id = selected_role_id
                    elif self.select_type == "notification_role":
                        state.notification_role_id = selected_role_id
                
                try:
                    db.commit()
                    db.refresh(state) 

                    cog = interaction.client.get_cog("AdminCog")
                    # Re-générer la vue pour mettre à jour l'affichage et potentiellement passer à l'étape suivante si on avait une navigation plus complexe
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

    class ChannelSelect(ui.Select):
        def __init__(self, guild_id: str, select_type: str, row: int, options: list[discord.SelectOption], id_mapping: dict, menu_index: int, total_menus: int):
            placeholder = f"Sélectionnez le salon pour le jeu (partie {menu_index+1}/{total_menus})..."[:MAX_LABEL_LENGTH]
            super().__init__(placeholder=placeholder, options=options, custom_id=f"select_channel_{select_type}_{guild_id}_{menu_index}", row=row)
            self.guild_id = guild_id
            self.select_type = select_type
            self.id_mapping = id_mapping
            self.menu_index = menu_index
            self.total_menus = total_menus

        async def callback(self, interaction: discord.Interaction):
            if not interaction.guild:
                await interaction.response.send_message("Erreur: Impossible de trouver le serveur courant pour cette action.", ephemeral=True)
                return

            if not self.values or self.values[0] in ["no_items", "error_guild"]:
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
                # Logique pour enregistrer la sélection. Similairement aux rôles, on prend la sélection du premier menu.
                if self.menu_index == 0:
                    if self.select_type == "game_channel":
                        state.game_channel_id = selected_channel_id
                
                try:
                    db.commit()
                    db.refresh(state)

                    cog = interaction.client.get_cog("AdminCog")
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


async def setup(bot):
    await bot.add_cog(AdminCog(bot))