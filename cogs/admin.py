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
            embed=self.generate_config_menu_embed(state),
            view=self.generate_config_menu_view(guild_id_str),
            ephemeral=True # Rendre le message visible seulement pour l'utilisateur qui lance la commande
        )
        db.close()

    # --- Méthodes pour Générer les Embeds et Vues de Configuration ---
    
    def generate_config_menu_embed(self, state: ServerState) -> discord.Embed:
        """Génère l'embed principal affichant l'état actuel des configurations."""
        embed = discord.Embed(
            title="⚙️ Configuration du Bot et du Jeu",
            description="Sélectionnez une section à configurer ci-dessous.",
            color=discord.Color.blue()
        )

        # Informations sur la configuration du Bot
        admin_role_mention = f"<@&{state.admin_role_id}>" if state.admin_role_id else "Non défini"
        game_channel_mention = f"<#{state.game_channel_id}>" if state.game_channel_id else "Non défini"
        game_status = "En cours" if state.game_started else "Non lancée"

        embed.add_field(name="👑 Rôle Admin", value=admin_role_mention, inline=False)
        embed.add_field(name="🎮 Salon de Jeu Principal", value=game_channel_mention, inline=False)
        embed.add_field(name="▶️ Statut du Jeu", value=game_status, inline=False)
        
        # Informations sur la configuration du Jeu (mode et durée)
        # Utilisez des valeurs par défaut si state ou les attributs spécifiques ne sont pas définis.
        mode_label = state.game_mode.capitalize() if state.game_mode else "Medium (Standard)"
        duration_label = self.GAME_DURATIONS.get(state.duration_key, {}).get("label", "Moyen (31 jours)") if state.duration_key else "Moyen (31 jours)"

        embed.add_field(name="✨ Mode de Difficulté", value=mode_label, inline=True)
        embed.add_field(name="⏱️ Durée de Partie", value=duration_label, inline=True)
        
        embed.add_field(name="⏰ Intervalle Tick (min)", value=f"{state.game_tick_interval_minutes}" if state.game_tick_interval_minutes is not None else "30 (Défaut)", inline=False)
        embed.add_field(name="⬇️ Dégrad. Faim/Tick", value=f"{state.degradation_rate_hunger:.1f}", inline=True)
        embed.add_field(name="⬇️ Dégrad. Soif/Tick", value=f"{state.degradation_rate_thirst:.1f}", inline=True)
        embed.add_field(name="⬇️ Dégrad. Vessie/Tick", value=f"{state.degradation_rate_bladder:.1f}", inline=False)
        embed.add_field(name="⬇️ Dégrad. Énergie/Tick", value=f"{state.degradation_rate_energy:.1f}", inline=True)
        embed.add_field(name="⬆️ Dégrad. Stress/Tick", value=f"{state.degradation_rate_stress:.1f}", inline=True)
        embed.add_field(name="⬆️ Dégrad. Ennui/Tick", value=f"{state.degradation_rate_boredom:.1f}", inline=True)
        
        embed.set_footer(text="Utilisez les boutons ci-dessous pour ajuster les paramètres.")
        return embed

    def generate_config_menu_view(self, guild_id: str) -> discord.ui.View:
        """Génère la vue des boutons pour le menu principal de configuration."""
        view = discord.ui.View(timeout=None) # Laisser la vue persistante
        
        # Bouton pour lancer la sélection du mode et de la durée
        # Utilisation de AdminCog.SetupGameModeButton pour référencer la classe imbriquée correctement
        view.add_item(AdminCog.SetupGameModeButton("🕹️ Mode & Durée", guild_id, discord.ButtonStyle.primary))
        
        # Boutons pour les autres configurations (Lancer, Sauvegarder, Statistiques, etc.)
        # Utilisation de AdminCog.ConfigButton, AdminCog.BackButton etc. pour référencer correctement les classes imbriquées
        view.add_item(AdminCog.ConfigButton("🎮 Lancer/Reinitialiser Partie", guild_id, discord.ButtonStyle.success, row=0))
        view.add_item(AdminCog.ConfigButton("💾 Sauvegarder l'État", guild_id, discord.ButtonStyle.blurple, row=0))
        view.add_item(AdminCog.ConfigButton("📊 Voir Statistiques", guild_id, discord.ButtonStyle.gray, row=1))
        # NOTE: Les boutons Notifications et Options Avancées utilisent `self.ConfigButton` au lieu de `AdminCog.ConfigButton`.
        # Pour que cela fonctionne, la classe ConfigButton doit être définie avant ces appels ou être une classe imbriquée.
        # Comme ConfigButton est définie après, il faut utiliser le nom de la classe imbriquée `AdminCog.ConfigButton`.
        view.add_item(AdminCog.ConfigButton("🔔 Notifications", guild_id, discord.ButtonStyle.green, row=1))
        view.add_item(AdminCog.ConfigButton("🛠 Options Avancées", guild_id, discord.ButtonStyle.secondary, row=2))
        
        # Bouton retour à la configuration principale
        view.add_item(AdminCog.BackButton("⬅ Retour", guild_id, discord.ButtonStyle.red, row=3))
        
        return view

    # --- Bouton pour lancer la sous-vue de sélection du Mode et Durée ---
    class SetupGameModeButton(ui.Button):
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle):
            super().__init__(label=label, style=style, row=0) # Ligne 0 pour les premiers boutons
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
        # Utiliser AdminCog.GameModeSelect pour référencer la classe imbriquée
        mode_select = AdminCog.GameModeSelect(guild_id, "mode")
        view.add_item(mode_select)

        # Menu déroulant pour la durée
        duration_select = AdminCog.GameDurationSelect(guild_id, "duration")
        view.add_item(duration_select)

        # Bouton pour retourner à la vue des paramètres de jeu généraux
        view.add_item(AdminCog.BackButton("⬅ Retour Paramètres Jeu", guild_id, discord.ButtonStyle.secondary, row=2))
        
        return view

    # --- Classe de Menu: Mode de Difficulté (Peaceful, Medium, Hard) ---
    class GameModeSelect(ui.Select):
        def __init__(self, guild_id: str, select_type: str):
            options = [
                discord.SelectOption(label="Peaceful", description="Taux de dégradation bas.", value="peaceful"),
                discord.SelectOption(label="Medium (Standard)", description="Taux de dégradation standard.", value="medium"),
                discord.SelectOption(label="Hard", description="Taux de dégradation élevés. Plus difficile.", value="hard")
            ]
            # L'argument 'row' est utilisé pour contrôler la position du menu dans la vue.
            super().__init__(placeholder="Choisissez le mode de difficulté...", options=options, custom_id=f"select_gamemode_{guild_id}", row=0)
            self.guild_id = guild_id

        async def callback(self, interaction: discord.Interaction):
            selected_mode = self.values[0]
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()

            if state:
                cog = interaction.client.get_cog("AdminCog") # Accéder au cog Admin pour utiliser ses méthodes
                mode_data = cog.GAME_MODES.get(selected_mode) # Récupérer les données du mode

                if mode_data: # Si le mode choisi existe bien dans GAME_MODES
                    state.game_mode = selected_mode
                    state.game_tick_interval_minutes = mode_data["tick_interval_minutes"]
                    # Mettre à jour tous les taux de dégradation associés au mode
                    for key, value in mode_data["rates"].items():
                        setattr(state, f"degradation_rate_{key}", value) # Met à jour les attributs correspondants
                
                    db.commit() # Sauvegarder les changements en base de données
                    
                    # Mettre à jour le message pour montrer le choix effectué
                    embed = cog.generate_setup_game_mode_embed()
                    embed.description = f"✅ Mode de difficulté défini sur **{selected_mode.capitalize()}**.\n" + embed.description
                    
                    await interaction.response.edit_message(embed=embed, view=cog.generate_setup_game_mode_view(self.guild_id))
            
            db.close()

    # --- Classe de Menu: Durée de Partie (Short, Medium, Long) ---
    class GameDurationSelect(ui.Select):
        def __init__(self, guild_id: str, select_type: str):
            # On doit passer le cog pour accéder à GAME_DURATIONS
            # On le fera dans le callback pour être sûr qu'il est chargé.
            
            options = [
                discord.SelectOption(label=duration["label"], description=f"Partie de {duration['days']} jours", value=key)
                for key, duration in AdminCog.GAME_DURATIONS.items()
            ]

            # Custom_id unique est bonne pratique pour Discord's UI handling
            super().__init__(placeholder="Choisissez la durée de la partie...", options=options, custom_id=f"select_gameduration_{guild_id}", row=1)
            self.guild_id = guild_id

        async def callback(self, interaction: discord.Interaction):
            selected_duration_key = self.values[0] # La clé choisie (ex: "short")
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()

            if state:
                cog = interaction.client.get_cog("AdminCog")
                if not cog:
                    await interaction.response.send_message("Erreur: Le cog Admin n'est pas chargé.", ephemeral=True)
                    db.close()
                    return
                    
                duration_data = cog.GAME_DURATIONS.get(selected_duration_key) # Récupérer les données de durée
                
                if duration_data:
                    # Sauvegarder la clé de durée choisie dans le state du serveur.
                    # Le nombre de jours (`duration_data["days"]`) peut être utilisé par le scheduler ou le logic de jeu.
                    state.duration_key = selected_duration_key 

                    db.commit() # Sauvegarder le changement
                    
                    # Mettre à jour le message pour refléter la sélection
                    embed = cog.generate_setup_game_mode_embed()
                    embed.description = f"✅ Durée de la partie définie sur **{duration_data['label']}**.\n" + embed.description
                    await interaction.response.edit_message(embed=embed, view=cog.generate_setup_game_mode_view(self.guild_id))

            db.close()
            
    # --- Bouton de retour vers le Menu Principal des Paramètres (général, pas juste mode/durée) ---
    class BackButton(ui.Button): 
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle, row: int = 0): # Le paramètre row est géré ici
            super().__init__(label=label, style=style, row=row)
            self.guild_id = guild_id
            
        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=str(self.guild_id)).first()
            cog = interaction.client.get_cog("AdminCog") # Accéder au cog Admin pour utiliser ses méthodes

            if not cog:
                await interaction.response.send_message("Erreur: Le cog Admin n'est pas chargé.", ephemeral=True)
                db.close()
                return
            
            # Retourner à la VUE GENERALE DES SETTINGS (celle avec les boutons principaux)
            # Il faut utiliser la méthode qui génère l'embed principal, qui est "generate_config_menu_embed"
            # La méthode `generate_server_config_embed` n'existe pas dans votre code, il faut utiliser `generate_config_menu_embed`.
            await interaction.response.edit_message(
                embed=cog.generate_config_menu_embed(state), # L'embed principal
                view=cog.generate_config_menu_view(self.guild_id)      # La vue principale
            )
            db.close()

    # --- Classe générique pour les boutons de configuration ---
    # Cette classe est utilisée pour les boutons comme Lancer/Réinitialiser, Sauvegarder, etc.
    class ConfigButton(ui.Button):
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle, row: int):
            super().__init__(label=label, style=style, row=row)
            self.guild_id = guild_id
            self.label = label # Stocker le label pour identifier l'action

        async def callback(self, interaction: discord.Interaction):
            cog = interaction.client.get_cog("AdminCog")
            if not cog:
                await interaction.response.send_message("Erreur: Le cog Admin n'est pas chargé.", ephemeral=True)
                return

            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=str(self.guild_id)).first()

            if self.label == "🎮 Lancer/Reinitialiser Partie":
                # Logique pour lancer ou réinitialiser la partie
                if state:
                    state.game_started = not state.game_started # Toggle le statut
                    state.game_start_time = datetime.datetime.utcnow() if state.game_started else None
                    # Potentiellement réinitialiser les états des joueurs ici aussi
                    db.commit()
                    
                    await interaction.response.edit_message(
                        embed=cog.generate_config_menu_embed(state),
                        view=cog.generate_config_menu_view(self.guild_id)
                    )
                    await interaction.followup.send(f"La partie a été {'lancée' if state.game_started else 'arrêtée/réinitialisée'}.", ephemeral=True)
                else:
                    await interaction.response.send_message("Erreur: Impossible de trouver l'état du serveur.", ephemeral=True)

            elif self.label == "💾 Sauvegarder l'État":
                # Logique pour sauvegarder l'état (qui est déjà fait automatiquement via les commits)
                # On peut juste envoyer un message de confirmation.
                await interaction.response.edit_message(
                    embed=cog.generate_config_menu_embed(state),
                    view=cog.generate_config_menu_view(self.guild_id)
                )
                await interaction.followup.send("L'état actuel a été sauvegardé.", ephemeral=True)

            elif self.label == "📊 Voir Statistiques":
                # Logique pour afficher les statistiques (qui devrait être une autre méthode/embed)
                await interaction.response.edit_message(
                    embed=cog.generate_stats_embed(self.guild_id), # Supposons qu'une telle méthode existe
                    view=cog.generate_stats_view(self.guild_id)     # Et une vue associée
                )
                await interaction.followup.send("Affichage des statistiques...", ephemeral=True)

            elif self.label == "🔔 Notifications":
                # Logique pour configurer les notifications
                await interaction.response.edit_message(
                    embed=cog.generate_notifications_embed(self.guild_id), # Supposons qu'une telle méthode existe
                    view=cog.generate_notifications_view(self.guild_id)    # Et une vue associée
                )
                await interaction.followup.send("Configuration des notifications...", ephemeral=True)

            elif self.label == "🛠️ Options Avancées":
                # Logique pour les options avancées
                await interaction.response.edit_message(
                    embed=cog.generate_advanced_options_embed(self.guild_id), # Supposons qu'une telle méthode existe
                    view=cog.generate_advanced_options_view(self.guild_id)    # Et une vue associée
                )
                await interaction.followup.send("Accès aux options avancées...", ephemeral=True)

            db.close()

    # Placeholder pour les méthodes de génération d'embeds/vues pour les autres sections
    def generate_stats_embed(self, guild_id: str) -> discord.Embed:
        # Implémentation à venir
        embed = discord.Embed(title="📊 Statistiques du Serveur", description="Fonctionnalité en développement.", color=discord.Color.purple())
        return embed
    
    def generate_stats_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        view.add_item(self.BackButton("⬅ Retour", guild_id, discord.ButtonStyle.secondary, row=3))
        return view

    def generate_notifications_embed(self, guild_id: str) -> discord.Embed:
        # Implémentation à venir
        embed = discord.Embed(title="🔔 Paramètres de Notifications", description="Fonctionnalité en développement.", color=discord.Color.green())
        return embed
    
    def generate_notifications_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        view.add_item(self.BackButton("⬅ Retour", guild_id, discord.ButtonStyle.secondary, row=3))
        return view

    def generate_advanced_options_embed(self, guild_id: str) -> discord.Embed:
        # Implémentation à venir
        embed = discord.Embed(title="🛠️ Options Avancées", description="Fonctionnalité en développement.", color=discord.Color.grey())
        return embed
    
    def generate_advanced_options_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        view.add_item(self.BackButton("⬅ Retour", guild_id, discord.ButtonStyle.secondary, row=3))
        return view


async def setup(bot):
    await bot.add_cog(AdminCog(bot))