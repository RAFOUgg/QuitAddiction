# --- cogs/admin.py ---

import discord
from discord.ext import commands # Importez 'ui' pour les SelectMenus et Modals
from discord import app_commands, ui # Pour les slash commands
from db.database import SessionLocal # Assurez-vous que c'est l'import correct de votre SessionLocal
from db.models import ServerState, PlayerProfile # Nécessaire si vous devez créer des profils ou charger des états

import datetime
import math # Peut être utile pour les calculs de temps

class AdminCog(commands.Cog):
    """Gestion des configurations du bot et du jeu pour le serveur."""
    def __init__(self, bot):
        self.bot = bot
        # server_channels n'est pas utilisé directement ici car la DB gère l'état du serveur
        # self.server_channels = {} 

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
            db.commit() # Assurer que l'enregistrement est créé en DB
            # Recharger pour obtenir les valeurs par défaut correctement assignées par SQLAlchemy.
            state = db.query(ServerState).filter_by(guild_id=guild_id_str).first()

        # Envoyer le message interactif principal
        await interaction.response.send_message(
            embed=self.generate_main_config_embed(state),
            view=self.generate_main_config_view(guild_id_str),
            ephemeral=True # Rendre le message visible seulement pour l'utilisateur qui lance la commande
        )
        db.close()

    # --- Méthodes pour Générer les Embeds et Vues de Configuration ---
    
    def generate_main_config_embed(self, state: ServerState) -> discord.Embed:
        """Génère l'embed principal affichant l'état actuel des configurations."""
        embed = discord.Embed(
            title="⚙️ Panneau de Configuration",
            description="Sélectionnez une section à configurer ci-dessous.",
            color=discord.Color.blue()
        )

        # --- Section Configuration Générale du Serveur ---
        embed.add_field(name="🔧 Configuration Serveur", value="\u200b", inline=False) # Titre de section
        embed.add_field(name="▶️ Statut du Jeu", value=f"`{'En cours' if state.game_started else 'Non lancée'}`", inline=False)
        embed.add_field(name="👑 Rôle Admin", value=f"`{'<@&' + str(state.admin_role_id) + '>' if state.admin_role_id else 'Non défini'}`", inline=False)
        embed.add_field(name="🔔 Rôle de Notification", value=f"`{'<@&' + str(state.notification_role_id) + '>' if hasattr(state, 'notification_role_id') and state.notification_role_id else 'Non défini'}`", inline=False)
        embed.add_field(name="🎮 Salon de Jeu Principal", value=f"`{'<#' + str(state.game_channel_id) + '>' if state.game_channel_id else 'Non défini'}`", inline=False)
        
        # Section Configuration de la Partie
        embed.add_field(name="---", value="\u200b", inline=False) # Séparateur visuel
        embed.add_field(name="✨ Mode de Difficulté", value=f"`{state.game_mode.capitalize() if state.game_mode else 'Medium (Standard)'}`", inline=False)
        embed.add_field(name="⏱️ Durée de Partie", value=f"`{self.GAME_DURATIONS.get(state.duration_key, {}).get('label', 'Moyen (31 jours)') if state.duration_key else 'Moyen (31 jours)'}`", inline=False)
        embed.add_field(name="⏰ Intervalle Tick (min)", value=f"`{state.game_tick_interval_minutes}`" if state.game_tick_interval_minutes is not None else "`30 (Défaut)`", inline=False)
        
        # Section Dégradations par Tick (en deux colonnes)
        embed.add_field(name="---", value="\u200b", inline=False) # Séparateur visuel
        embed.add_field(name="📉 Dégradations / Tick", value="", inline=False) # Titre de section
        
        # Colonne 1 des dégradations avec nom, emoji, et valeur formatée
        embed.add_field(name="🍎 Faim", value=f"`{state.degradation_rate_hunger:.1f}`", inline=True) 
        embed.add_field(name="💧 Soif", value=f"`{state.degradation_rate_thirst:.1f}`", inline=True)
        embed.add_field(name=" bladder Vessie", value=f"`{state.degradation_rate_bladder:.1f}`", inline=False) # Force nouvelle ligne
        
        # Colonne 2 des dégradations
        embed.add_field(name="⚡ Énergie", value=f"`{state.degradation_rate_energy:.1f}`", inline=True) 
        embed.add_field(name="😥 Stress", value=f"`{state.degradation_rate_stress:.1f}`", inline=True) 
        embed.add_field(name="😴 Ennui", value=f"`{state.degradation_rate_boredom:.1f}`", inline=True) 
        
        embed.set_footer(text="Utilisez les boutons ci-dessous pour ajuster les paramètres.")
        return embed

    def generate_config_menu_view(self, guild_id: str) -> discord.ui.View:
        """Génère la vue des boutons pour le menu principal de configuration."""
        view = discord.ui.View(timeout=None) # Laisser la vue persistante
        
        # Section Configuration Serveur
        view.add_item(self.GeneralConfigButton("⚙️ Rôles & Salons", guild_id, discord.ButtonStyle.primary, row=0))
        view.add_item(self.ConfigButton("🔔 Notifications", guild_id, discord.ButtonStyle.green, row=0))

        # Section Configuration de la Partie
        view.add_item(self.SetupGameModeButton("🕹️ Mode & Durée", guild_id, discord.ButtonStyle.secondary, row=1))
        view.add_item(self.ConfigButton("🎮 Lancer/Reinitialiser Partie", guild_id, discord.ButtonStyle.success, row=1))
        view.add_item(self.ConfigButton("💾 Sauvegarder l'État", guild_id, discord.ButtonStyle.blurple, row=1))

        # Section Dégradations & Avancées
        view.add_item(self.ConfigButton("📊 Voir Statistiques", guild_id, discord.ButtonStyle.gray, row=2))
        view.add_item(self.ConfigButton("🛠 Options Avancées", guild_id, discord.ButtonStyle.secondary, row=2))
        
        # Bouton retour
        view.add_item(self.BackButton("⬅ Retour", guild_id, discord.ButtonStyle.red, row=3))
        
        return view

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
            # Mise à jour du message pour montrer la vue de sélection de mode/durée
            await interaction.response.edit_message(
                embed=cog.generate_setup_game_mode_embed(),
                view=cog.generate_setup_game_mode_view(self.guild_id)
            )

    # --- Embed pour la sélection du Mode de Jeu et Durée ---
    def generate_setup_game_mode_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🎮 Configuration du Mode de Jeu et de la Durée",
            description="Sélectionnez un mode de difficulté et une durée pour la partie. Ces paramètres seront sauvegardés pour le serveur.",
            color=discord.Color.teal()
        )
        return embed

    # --- View pour la sélection du Mode de Jeu et Durée ---
    def generate_setup_game_mode_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        
        # Menu déroulant pour le mode de difficulté
        view.add_item(self.GameModeSelect(guild_id, "mode", row=0)) 

        # Menu déroulant pour la durée
        view.add_item(self.GameDurationSelect(guild_id, "duration", row=1)) 

        # Bouton pour retourner à la vue des paramètres de jeu généraux
        view.add_item(self.BackButton("⬅ Retour Paramètres Jeu", guild_id, discord.ButtonStyle.secondary, row=2))
        
        return view

    # --- Classe de Menu: Mode de Difficulté (Peaceful, Medium, Hard) ---
    class GameModeSelect(ui.Select):
        def __init__(self, guild_id: str, select_type: str, row: int): # Added row parameter
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
        def __init__(self, guild_id: str, select_type: str, row: int): # Added row parameter
            options = []
            # On doit récupérer le cog pour accéder à GAME_DURATIONS. On le fera dans le callback.
            
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
            
            # Retourner à la VUE GENERALE DES SETTINGS
            await interaction.response.edit_message(
                embed=cog.generate_config_menu_embed(state), # Utiliser l'embed principal
                view=cog.generate_config_menu_view(self.guild_id)      
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
                # Le bouton "Notifications" devrait mener à une vue spécifique pour configurer les rôles de notification.
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

    # --- Classe pour le bouton qui va ouvrir la configuration des rôles et salons ---
    class GeneralConfigButton(ui.Button):
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle, row: int):
            # Le paramètre 'row' est maintenant correctement géré dans l'initialisation
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
                view=cog.generate_general_config_view(self.guild_id)
            )
            db.close()

    # --- Méthodes pour les configurations spécifiques (Rôle Admin, Salon, Rôle Notif) ---
    
    # Méthode pour générer l'embed de configuration du rôle admin et du salon de jeu
    def generate_role_and_channel_config_embed(self, state: ServerState) -> discord.Embed:
        embed = discord.Embed(
            title="⚙️ Configuration Générale",
            description="Utilisez les menus déroulants pour sélectionner les rôles et salons.",
            color=discord.Color.purple()
        )
        current_admin_role = f"<@&{state.admin_role_id}>" if state.admin_role_id else "Non défini"
        current_notif_role = f"<@&{state.notification_role_id}>" if hasattr(state, 'notification_role_id') and state.notification_role_id else "Non défini"
        current_game_channel = f"<#{state.game_channel_id}>" if state.game_channel_id else "Non défini"

        embed.add_field(name="👑 Rôle Admin actuel", value=current_admin_role, inline=False)
        embed.add_field(name="🔔 Rôle de Notification actuel", value=current_notif_role, inline=False)
        embed.add_field(name="🎮 Salon de Jeu actuel", value=current_game_channel, inline=False)
        return embed

    # Vue pour la sélection des rôles et du salon
    def generate_general_config_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        # Les menus déroulants sont sur les lignes 0, 1 et 2 pour éviter les conflits.
        view.add_item(self.RoleSelect(guild_id, "admin_role", row=0))
        view.add_item(self.RoleSelect(guild_id, "notification_role", row=1))
        view.add_item(self.ChannelSelect(guild_id, "game_channel", row=2))
        # Bouton de retour sur la ligne 3.
        view.add_item(self.BackButton("⬅ Retour", guild_id, discord.ButtonStyle.secondary, row=3))
        return view

    # Classe de Menu: Sélection de Rôle
    class RoleSelect(ui.Select):
        def __init__(self, guild_id: str, select_type: str, row: int): # Added row parameter
            placeholder = f"Sélectionnez un rôle pour {'Admin' if select_type == 'admin_role' else 'Notifications' if select_type == 'notification_role' else 'Rôle'}..."
            super().__init__(placeholder=placeholder, options=[], custom_id=f"select_role_{select_type}_{guild_id}", row=row)
            self.guild_id = guild_id
            self.select_type = select_type

        async def callback(self, interaction: discord.Interaction):
            selected_role_id = self.values[0]
            
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()

            if state:
                if self.select_type == "admin_role":
                    state.admin_role_id = selected_role_id
                elif self.select_type == "notification_role":
                    # Assurez-vous que l'attribut notification_role_id existe dans ServerState
                    if hasattr(state, 'notification_role_id'):
                        state.notification_role_id = selected_role_id
                    else:
                        await interaction.response.send_message("Erreur: L'attribut 'notification_role_id' n'est pas défini dans la base de données. Veuillez le rajouter dans models.py.", ephemeral=True)
                        db.close()
                        return
                
                db.commit()

                cog = interaction.client.get_cog("AdminCog")
                await interaction.response.edit_message(
                    embed=cog.generate_role_and_channel_config_embed(state),
                    view=cog.generate_general_config_view(self.guild_id)
                )
                await interaction.followup.send(f"Rôle pour {'l\'administration' if self.select_type == 'admin_role' else 'les notifications'} mis à jour.", ephemeral=True)
            
            db.close()

    # Classe de Menu: Sélection de Salon
    class ChannelSelect(ui.Select):
        def __init__(self, guild_id: str, select_type: str, row: int): # Added row parameter
            placeholder = f"Sélectionnez un salon pour le jeu..."
            super().__init__(placeholder=placeholder, options=[], custom_id=f"select_channel_{select_type}_{guild_id}", row=row) 
            self.guild_id = guild_id
            self.select_type = select_type

        async def callback(self, interaction: discord.Interaction):
            selected_channel_id = self.values[0]
            
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()

            if state:
                if self.select_type == "game_channel":
                    state.game_channel_id = selected_channel_id
                
                db.commit()

                cog = interaction.client.get_cog("AdminCog")
                await interaction.response.edit_message(
                    embed=cog.generate_role_and_channel_config_embed(state),
                    view=cog.generate_general_config_view(self.guild_id)
                )
                await interaction.followup.send(f"Salon de jeu mis à jour.", ephemeral=True)
            
            db.close()

    # --- Méthodes pour les autres configurations (Statistiques, Notifications, Avancées) ---
    def generate_stats_embed(self, guild_id: str) -> discord.Embed:
        embed = discord.Embed(title="📊 Statistiques du Serveur", description="Fonctionnalité en développement.", color=discord.Color.purple())
        return embed
    
    def generate_stats_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        view.add_item(self.BackButton("⬅ Retour", guild_id, discord.ButtonStyle.secondary, row=3))
        return view

    def generate_notifications_embed(self, guild_id: str) -> discord.Embed:
        embed = discord.Embed(title="🔔 Paramètres de Notifications", description="Configurez les rôles pour les notifications du jeu.", color=discord.Color.green())
        # Vous pouvez ajouter des options pour configurer les notifications ici, par exemple :
        # - Quel rôle recevoir les notifications
        # - Quels événements déclenchent les notifications
        return embed
    
    def generate_notifications_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        # Pour l'instant, on ajoute juste un bouton de retour
        view.add_item(self.BackButton("⬅ Retour", guild_id, discord.ButtonStyle.secondary, row=3))
        return view

    def generate_advanced_options_embed(self, guild_id: str) -> discord.Embed:
        embed = discord.Embed(title="🛠️ Options Avancées", description="Fonctionnalité en développement.", color=discord.Color.grey())
        return embed
    
    def generate_advanced_options_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        view.add_item(self.BackButton("⬅ Retour", guild_id, discord.ButtonStyle.secondary, row=3))
        return view

    # Remplacement de l'ancienne méthode generate_config_menu_view pour intégrer les nouveaux boutons
    def generate_config_menu_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        
        # Bouton pour lancer la sélection du mode et de la durée
        view.add_item(self.SetupGameModeButton("🕹️ Mode & Durée", guild_id, discord.ButtonStyle.primary, row=0))
        
        # Boutons pour les autres configurations
        view.add_item(self.ConfigButton("🎮 Lancer/Reinitialiser Partie", guild_id, discord.ButtonStyle.success, row=0))
        view.add_item(self.ConfigButton("💾 Sauvegarder l'État", guild_id, discord.ButtonStyle.blurple, row=0))
        # Ajout du bouton pour configurer les rôles et salons, en spécifiant le row
        view.add_item(self.GeneralConfigButton("⚙️ Rôles & Salons", guild_id, discord.ButtonStyle.grey, row=1)) 
        view.add_item(self.ConfigButton("📊 Voir Statistiques", guild_id, discord.ButtonStyle.gray, row=1))
        view.add_item(self.ConfigButton("🔔 Notifications", guild_id, discord.ButtonStyle.green, row=2))
        view.add_item(self.ConfigButton("🛠 Options Avancées", guild_id, discord.ButtonStyle.secondary, row=2))
        
        # Bouton retour à la configuration principale
        view.add_item(self.BackButton("⬅ Retour", guild_id, discord.ButtonStyle.red, row=3))
        
        return view


async def setup(bot):
    await bot.add_cog(AdminCog(bot))