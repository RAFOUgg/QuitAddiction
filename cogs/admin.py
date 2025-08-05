# --- cogs/admin.py ---

import discord
from discord.ext import commands
from discord import app_commands, ui
from db.database import SessionLocal
from db.models import ServerState, PlayerProfile

import datetime
import math

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
            view=self.generate_config_menu_view(guild_id_str),
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

        # Section Statut Général
        embed.add_field(
            name="▶️ **Statut Général**",
            value=f"**Jeu :** `{'En cours' if state.game_started else 'Non lancée'}`\n"
                  f"**Mode :** `{state.game_mode.capitalize() if state.game_mode else 'Medium (Standard)'}`\n"
                  f"**Durée :** `{self.GAME_DURATIONS.get(state.duration_key, {}).get('label', 'Moyen (31 jours)') if state.duration_key else 'Moyen (31 jours)'}`",
            inline=False
        )

        # Section Configuration du Serveur
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

        # Section Paramètres du Jeu
        tick_interval = state.game_tick_interval_minutes if state.game_tick_interval_minutes is not None else 30 # Valeur par défaut pour l'affichage
        embed.add_field(
            name="⏱️ **Paramètres du Jeu**",
            value=f"**Intervalle Tick (min) :** `{tick_interval}`",
            inline=False
        )
        
        # Section Dégradations par Tick (plus structurée)
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
            # Mise à jour du message pour montrer la vue de sélection de mode/durée
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

    # Vue pour la sélection des rôles et du salon
    def generate_general_config_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        view.add_item(self.RoleSelect(guild_id, "admin_role", row=0))
        view.add_item(self.RoleSelect(guild_id, "notification_role", row=1))
        view.add_item(self.ChannelSelect(guild_id, "game_channel", row=2))
        view.add_item(self.BackButton("⬅ Retour Paramètres Jeu", guild_id, discord.ButtonStyle.secondary, row=3))
        return view

    # Classe de Menu: Sélection de Rôle
    class RoleSelect(ui.Select):
        def __init__(self, guild_id: str, select_type: str, row: int):
            placeholder = f"Sélectionnez le rôle pour {'l\'administration' if select_type == 'admin_role' else 'les notifications'}..."
            super().__init__(placeholder=placeholder, options=[], custom_id=f"select_role_{select_type}_{guild_id}", row=row)
            self.guild_id = guild_id
            self.select_type = select_type

        # On charge les options dans on_ready ou quand le cog est chargé, mais ici pour simplifier, on les charge à la volée.
        # Dans un vrai bot, il serait mieux de les charger une fois.
        async def load_options(self, interaction: discord.Interaction):
            guild = interaction.guild
            if guild:
                roles = sorted(guild.roles, key=lambda r: r.position, reverse=True)
                self.options = [
                    discord.SelectOption(label=role.name, value=str(role.id))
                    for role in roles if role.name != "@everyone"
                ]
            else:
                self.options = [discord.SelectOption(label="Serveur introuvable", value="error")]

        async def callback(self, interaction: discord.Interaction):
            if not self.options: # Charger les rôles si ce n'est pas déjà fait
                await self.load_options(interaction)

            if self.values[0] == "error":
                await interaction.response.send_message("Erreur lors du chargement des rôles.", ephemeral=True)
                return

            selected_role_id = self.values[0]
            
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()

            if state:
                if self.select_type == "admin_role":
                    state.admin_role_id = selected_role_id
                elif self.select_type == "notification_role":
                    if hasattr(state, 'notification_role_id'):
                        state.notification_role_id = selected_role_id
                    else:
                        await interaction.response.send_message("Erreur: L'attribut 'notification_role_id' n'est pas défini.", ephemeral=True)
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
        def __init__(self, guild_id: str, select_type: str, row: int):
            placeholder = f"Sélectionnez le salon pour le jeu..."
            super().__init__(placeholder=placeholder, options=[], custom_id=f"select_channel_{select_type}_{guild_id}", row=row) 
            self.guild_id = guild_id
            self.select_type = select_type

        async def load_options(self, interaction: discord.Interaction):
            guild = interaction.guild
            if guild:
                channels = sorted(guild.text_channels, key=lambda c: c.position)
                self.options = [
                    discord.SelectOption(label=channel.name, value=str(channel.id))
                    for channel in channels
                ]
            else:
                self.options = [discord.SelectOption(label="Serveur introuvable", value="error")]

        async def callback(self, interaction: discord.Interaction):
            if not self.options:
                await self.load_options(interaction)

            if self.values[0] == "error":
                await interaction.response.send_message("Erreur lors du chargement des salons.", ephemeral=True)
                return

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

    # Remplacement de l'ancienne méthode generate_config_menu_view pour intégrer les nouveaux boutons
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


async def setup(bot):
    await bot.add_cog(AdminCog(bot))