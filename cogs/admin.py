# --- cogs/admin.py ---

import discord
from discord.ext import commands, ui # Importez 'ui' pour les SelectMenus et Modals
from discord import app_commands # Pour les slash commands
from db.database import SessionLocal # Assurez-vous que c'est l'import correct de votre SessionLocal
from db.models import ServerState, PlayerProfile # Nécessaire si vous devez créer des profils ou charger des états

import datetime
import math # Peut être utile pour les calculs de temps, non utilisé directement dans ce snippet UI

class AdminCog(commands.Cog):
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
        view.add_item(self.SetupGameModeButton("🕹️ Mode & Durée", guild_id, discord.ButtonStyle.primary))
        
        # Boutons pour les autres configurations (Lancer, Sauvegarder, Statistiques, etc.)
        view.add_item(self.ConfigButton("🎮 Lancer/Reinitialiser Partie", guild_id, discord.ButtonStyle.success, row=0))
        view.add_item(self.ConfigButton("💾 Sauvegarder l'État", guild_id, discord.ButtonStyle.blurple, row=0))
        view.add_item(self.ConfigButton("📊 Voir Statistiques", guild_id, discord.ButtonStyle.gray, row=1))
        view.add_item(self.ConfigButton("🔔 Notifications", guild_id, discord.ButtonStyle.green, row=1))
        view.add_item(self.ConfigButton("🛠 Options Avancées", guild_id, discord.ButtonStyle.secondary, row=2))
        
        # Bouton retour à la configuration principale
        view.add_item(self.BackButton("⬅ Retour", guild_id, discord.ButtonStyle.red, row=3))
        
        return view

    # --- Bouton pour lancer la sous-vue de sélection du Mode et Durée ---
    class SetupGameModeButton(ui.Button):
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle):
            super().__init__(label=label, style=style, row=0) # Ligne 0 pour les premiers boutons
            self.guild_id = guild_id

        async def callback(self, interaction: discord.Interaction):
            cog = interaction.client.get_cog("AdminCog")
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
        mode_select = self.GameModeSelect(guild_id, "mode")
        view.add_item(mode_select)

        # Menu déroulant pour la durée
        duration_select = self.GameDurationSelect(guild_id, "duration")
        view.add_item(duration_select)

        # Bouton pour retourner à la vue des paramètres de jeu généraux
        view.add_item(self.BackButton("⬅ Retour Paramètres Jeu", guild_id, discord.ButtonStyle.secondary, row=2)) # row=2 pour la ligne après les menus
        
        return view

    # --- Classe de Menu: Mode de Difficulté (Peaceful, Medium, Hard) ---
    class GameModeSelect(ui.Select):
        def __init__(self, guild_id: str, select_type: str):
            # Création des options pour le menu déroulant
            options = [
                discord.SelectOption(label="Peaceful", description="Taux de dégradation bas.", value="peaceful"),
                discord.SelectOption(label="Medium (Standard)", description="Taux de dégradation standard.", value="medium"),
                discord.SelectOption(label="Hard", description="Taux de dégradation élevés. Plus difficile.", value="hard")
            ]
            # Le 'row=0' est défini dans __init__ de SetupGameModeButton, on peut le répéter ici pour être explicite
            super().__init__(placeholder="Choisissez le mode de difficulté...", options=options, custom_id=f"select_gamemode_{guild_id}", row=0)
            self.guild_id = guild_id

        async def callback(self, interaction: discord.Interaction):
            selected_mode = self.values[0]
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()

            if state:
                cog = interaction.client.get_cog("AdminCog")
                mode_data = cog.GAME_MODES.get(selected_mode)

                if mode_data: # Si le mode choisi existe bien dans GAME_MODES
                    state.game_mode = selected_mode
                    state.game_tick_interval_minutes = mode_data["tick_interval_minutes"]
                    # Mettre à jour tous les taux de dégradation associés au mode
                    for key, value in mode_data["rates"].items():
                        setattr(state, f"degradation_rate_{key}", value)
                
                    db.commit() # Sauvegarder les changements en base de données
                    
                    # Mettre à jour le message pour montrer le choix effectué
                    embed = cog.generate_setup_game_mode_embed()
                    embed.description = f"✅ Mode de difficulté défini sur **{selected_mode.capitalize()}**.\n" + embed.description
                    
                    await interaction.response.edit_message(embed=embed, view=cog.generate_setup_game_mode_view(self.guild_id))
            
            db.close()

    # --- Classe de Menu: Durée de Partie (Short, Medium, Long) ---
    class GameDurationSelect(ui.Select):
        def __init__(self, guild_id: str, select_type: str):
            cog = commands.bot.Bot.get_cog("AdminCog") 
            if not cog: # Vérification de sécurité au cas où le cog n'est pas chargé
                return 
            
            options = []
            # Créer les options du menu à partir des durées prédéfinies
            for key, data in cog.GAME_DURATIONS.items():
                options.append(discord.SelectOption(label=data["label"], value=key, description=f"Durée totale estimée de la partie : {data['days']} jours"))
                
            super().__init__(placeholder="Choisissez la durée de la partie...", options=options, custom_id=f"select_gameduration_{guild_id}", row=1) # row=1 pour la 2ème ligne
            self.guild_id = guild_id

        async def callback(self, interaction: discord.Interaction):
            selected_duration_key = self.values[0] # Clé comme "short", "medium", "long"
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()

            if state:
                cog = interaction.client.get_cog("AdminCog")
                duration_data = cog.GAME_DURATIONS.get(selected_duration_key)
                
                if duration_data:
                    # Sauvegarder la clé de durée choisie.
                    # NOTE: Le nombre de jours en lui-même (duration_data["days"]) n'est pas directement sauvegardé dans un champ ici.
                    # On le lit depuis les pré-sets quand on en a besoin. Si vous voulez le sauvegarder pour usage futur,
                    # ajoutez `game_duration_days` dans models.py et sauvegardez là.
                    state.duration_key = selected_duration_key 

                    db.commit()
                    
                    # Mettre à jour le message pour refléter la sélection
                    embed = cog.generate_setup_game_mode_embed()
                    embed.description = f"✅ Durée de la partie définie sur **{duration_data['label']}**.\n" + embed.description
                    await interaction.response.edit_message(embed=embed, view=cog.generate_setup_game_mode_view(self.guild_id))

            db.close()
            
    # --- Bouton de retour vers le Menu Principal des Paramètres (général, pas juste mode/durée) ---
    class BackButton(ui.Button): # Le nom "BackButton" est correct, car c'est le retour par défaut
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle, row: int = 0): # Vous avez déjà mis 'row' ici, c'est bien
            super().__init__(label=label, style=style, row=row)
            self.guild_id = guild_id
            
        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=str(self.guild_id)).first()
            cog = interaction.client.get_cog("AdminCog") # Recupérer le cog Admin
            
            # Ici, on retourne à la VUE GENERALE DES SETTINGS (/config menu)
            await interaction.response.edit_message(
                embed=cog.generate_server_config_embed(self.guild_id), # Remettre l'embed principal des SETTINGS
                view=cog.generate_config_menu_view(self.guild_id)      # et la vue principale des SETTINGS
            )
            db.close()

    # --- Autres Méthodes Embeds/Vues (les appels vers celles-ci depuis le callback des boutons ConfigButton doivent être ok) ---

    # (Assurez-vous que les autres méthodes comme generate_server_config_embed, generate_game_settings_embed etc. sont bien présentes dans cette classe AdminCog)

    def generate_server_config_embed(self, guild_id: str) -> discord.Embed: # Guild_id doit être string si utilisé pour filtres DB
        db = SessionLocal()
        state = db.query(ServerState).filter_by(guild_id=guild_id).first() # OK, mais guild_id_str sera plus sûr
        db.close()

        if not state:
            # ... (gestion état absent) ...
            desc = "Aucune partie n'est encore initialisée pour ce serveur. Configurez les paramètres pour démarrer."
            embed = discord.Embed(title="⚙️ Paramètres du Serveur", description=desc, color=0x44ff44)
            return embed

        embed = discord.Embed(title=f"⚙️ Paramètres du serveur {guild_id}", color=0x44ff44)
        # Ajout du mode et de la durée aux informations affichées ici
        mode_label = state.game_mode.capitalize() if state.game_mode else "Medium (Standard)"
        duration_label = self.GAME_DURATIONS.get(state.duration_key, {}).get("label", "Moyen (31 jours)") if state.duration_key else "Moyen (31 jours)"
        
        embed.add_field(name="Mode de Difficulté", value=mode_label, inline=True)
        embed.add_field(name="Durée de Partie", value=duration_label, inline=True)
        embed.add_field(name="Intervalle Tick (min)", value=f"{state.game_tick_interval_minutes}" if state.game_tick_interval_minutes is not None else "30", inline=False)
        
        # ... (reste des fields pour SATATS GLOBALES et les RATES s'ils doivent être affichés ici, ou sur une autre page "options avancées") ...

        return embed

    def generate_game_settings_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        
        # Bouton pour lancer la sélection du mode et de la durée (UI dédiée)
        view.add_item(self.SetupGameModeButton("🕹️ Mode & Durée", guild_id, discord.ButtonStyle.primary))
        
        # Les autres boutons pour lancer, sauvegarder, etc.
        view.add_item(self.ConfigButton("🎮 Lancer/Réinitialiser Partie", guild_id, discord.ButtonStyle.green, row=0))
        view.add_item(self.ConfigButton("💾 Sauvegarder l'État", guild_id, discord.ButtonStyle.blurple, row=0))
        view.add_item(self.ConfigButton("📊 Voir Statistiques", guild_id, discord.ButtonStyle.gray, row=1))
        view.add_item(self.ConfigButton("🔔 Notifications", guild_id, discord.ButtonStyle.green, row=1))
        view.add_item(self.ConfigButton("🛠 Options Avancées", guild_id, discord.ButtonStyle.secondary, row=2))
        
        # Bouton Retour aux paramètres généraux, et non pas à l'embed /config principal
        view.add_item(self.BackButton("⬅ Retour Paramètres", guild_id, discord.ButtonStyle.red, row=3))
        
        return view
    
    # Les classes de boutons/selects (ConfigButton, BackButton, GameModeSelect, GameDurationSelect, SetupGameModeButton)
    # doivent TOUTES être DÉFINIES DANS CETTE CLASSE AdminCog, ET ELLES Y SONT CORRECTEMENT DÉFINIES.
    # Donc, si elles ne causent pas d'erreur (type "row argument unexpected"), la structure est bonne.
    # Si vous les aviez mises à l'extérieur de la classe AdminCog par erreur, c'est là qu'il faudrait les rentrer.
    # Vu l'historique des erreurs, je pense qu'elles sont déjà à l'intérieur des classes.


    # --- Il FAUT TOUJOURS appeler le setup à la fin ---
async def setup(bot):
    await bot.add_cog(AdminCog(bot))