from discord import app_commands
import discord.ui as ui
from discord.ext import commands
from db.database import SessionLocal
from db.models import ServerState

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.server_channels = {}

    GAME_MODES = {
        "peaceful": {
            "tick_interval_minutes": 60,
            "rates": {
                "hunger": 5.0,
                "thirst": 4.0,
                "bladder": 5.0,
                "energy": 3.0,
                "stress": 1.0,
                "boredom": 2.0,
                "addiction_base": 0.05,
                "toxins_base": 0.1,
            }
        },
        "medium": {
            "tick_interval_minutes": 30,
            "rates": {
                "hunger": 10.0,
                "thirst": 8.0,
                "bladder": 15.0,
                "energy": 5.0,
                "stress": 3.0,
                "boredom": 7.0,
                "addiction_base": 0.1,
                "toxins_base": 0.5,
            }
        },
        "hard": {
            "tick_interval_minutes": 15,
            "rates": {
                "hunger": 20.0,
                "thirst": 16.0,
                "bladder": 30.0,
                "energy": 10.0,
                "stress": 6.0,
                "boredom": 14.0,
                "addiction_base": 0.2,
                "toxins_base": 1.0,
            }
        }
    }
    
    # Préréglages de la durée totale de la partie (en jours)
    GAME_DURATIONS = {
        "short": {"days": 14, "label": "Court (14 jours)"},
        "medium": {"days": 31, "label": "Moyen (31 jours)"},
        "long": {"days": 72, "label": "Long (72 jours)"},
    }

    # -------------------
    # Commandes Admin
    # -------------------
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setchannel(self, ctx, channel: discord.TextChannel):
        """Définit le salon principal pour les interactions du bot et sauvegarde en DB"""
        db = SessionLocal()
        state = db.query(ServerState).filter_by(guild_id=str(ctx.guild.id)).first()
        if not state:
            state = ServerState(guild_id=str(ctx.guild.id), main_channel_id=str(channel.id))
            db.add(state)
        else:
            state.main_channel_id = str(channel.id)
        db.commit()
        db.close()

        self.server_channels[ctx.guild.id] = channel.id
        await ctx.send(f"✅ Salon principal défini et sauvegardé : {channel.mention}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def settings(self, ctx):
        """Affiche le menu principal des paramètres de la partie"""
        guild_id = ctx.guild.id
        embed = self.generate_server_config_embed(ctx.guild.id)
        view = self.generate_game_settings_view(guild_id)
        await ctx.send(embed=embed, view=view)

    # -------------------
    # Embeds et Vues
    # -------------------

    # --- Classe Bouton pour lancer la sélection du mode ---
    class SetupGameModeButton(ui.Button):
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle):
            super().__init__(label=label, style=style, row=0)
            self.guild_id = guild_id

        async def callback(self, interaction: discord.Interaction):
            cog = interaction.client.get_cog("AdminCog")
            # Envoi d'un nouvel embed et de vues avec les menus déroulants
            await interaction.response.edit_message(
                embed=cog.generate_setup_game_mode_embed(),
                view=cog.generate_setup_game_mode_view(self.guild_id)
            )

    # --- Embed et View pour la Sélection du Mode de Jeu et Durée ---
    def generate_setup_game_mode_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🎮 Configuration du Mode de Jeu et de la Durée",
            description="Sélectionnez un mode de difficulté et une durée pour la partie. Ces paramètres sont appliqués lorsque vous lancez la partie.",
            color=discord.Color.teal()
        )
        return embed

    def generate_setup_game_mode_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        
        # Menu déroulant pour le mode de difficulté (Peaceful, Medium, Hard)
        mode_select = self.GameModeSelect(guild_id, "mode")
        view.add_item(mode_select)

        # Menu déroulant pour la durée (14, 31, 72 jours)
        duration_select = self.GameDurationSelect(guild_id, "duration")
        view.add_item(duration_select)

        # Bouton Retour (vers les paramètres de jeu, pas le menu principal complet)
        view.add_item(self.BackButton("⬅ Retour aux Paramètres de Jeu", guild_id, discord.ButtonStyle.secondary))
        
        return view

    # --- Classe de Menu de Sélection de Mode (Peaceful, Medium, Hard) ---
    class GameModeSelect(ui.Select):
        def __init__(self, guild_id: str, select_type: str):
            options = [
                discord.SelectOption(label="Peaceful", description="Taux de dégradation bas.", value="peaceful"),
                discord.SelectOption(label="Medium (Standard)", description="Taux de dégradation standard.", value="medium"),
                discord.SelectOption(label="Hard", description="Taux de dégradation élevés. Plus difficile.", value="hard")
            ]
            super().__init__(placeholder="Choisissez le mode de difficulté...", options=options, custom_id=f"select_gamemode_{guild_id}", row=0)
            self.guild_id = guild_id

        async def callback(self, interaction: discord.Interaction):
            selected_mode = self.values[0]
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()

            if state:
                cog = interaction.client.get_cog("AdminCog")
                mode_data = cog.GAME_MODES.get(selected_mode)

                # Mise à jour des taux de dégradation dans ServerState
                if mode_data:
                    state.game_mode = selected_mode
                    state.game_tick_interval_minutes = mode_data["tick_interval_minutes"]
                    # Parcourir et mettre à jour tous les taux dans ServerState
                    for key, value in mode_data["rates"].items():
                        setattr(state, f"degradation_rate_{key}", value)
                
                    db.commit()
                    
                    # Répondre à l'interaction en mettant à jour le message
                    embed = cog.generate_setup_game_mode_embed()
                    embed.description += f"\n✅ Mode de difficulté défini sur **{selected_mode.capitalize()}**."
                    
                    await interaction.response.edit_message(embed=embed, view=cog.generate_setup_game_mode_view(self.guild_id))
            
            db.close()

    # --- Classe de Menu de Sélection de Durée (14, 31, 72 jours) ---
    class GameDurationSelect(ui.Select):
        def __init__(self, guild_id: str, select_type: str):
            cog = commands.bot.Bot.get_cog("AdminCog") # Pour accéder à GAME_DURATIONS
            if not cog: return # Sécurité
            
            options = []
            for key, data in cog.GAME_DURATIONS.items():
                options.append(discord.SelectOption(label=data["label"], value=key, description=f"Durée totale estimée de la partie : {data['days']} jours"))
                
            super().__init__(placeholder="Choisissez la durée de la partie...", options=options, custom_id=f"select_gameduration_{guild_id}", row=1)
            self.guild_id = guild_id

        async def callback(self, interaction: discord.Interaction):
            selected_duration_key = self.values[0]
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()

            if state:
                cog = interaction.client.get_cog("AdminCog")
                duration_data = cog.GAME_DURATIONS.get(selected_duration_key)
                
                if duration_data:
                    # IMPORTANT: On doit définir où ces données seront sauvegardées
                    # Si 'game_mode' n'est qu'un string (medium, peaceful, hard) et qu'il faut en garder une trace de la durée
                    # Ajoutons une variable `game_duration_days` à ServerState.
                    # N'oubliez pas d'ajouter game_duration_days dans db/models.py pour ServerState!
                    # state.game_duration_days = duration_data["days"]
                    
                    # POUR LE MOMENT : on utilise un champ 'duration_key' dans ServerState pour les tests.
                    state.duration_key = selected_duration_key # Assurez-vous d'ajouter ce champ dans models.py

                    db.commit()
                    
                    embed = cog.generate_setup_game_mode_embed()
                    embed.description += f"\n✅ Durée de la partie définie sur **{duration_data['days']} jours**."
                    await interaction.response.edit_message(embed=embed, view=cog.generate_setup_game_mode_view(self.guild_id))

            db.close()
            
    # Ajoutez un BackButton personnalisé pour retourner aux Game Settings, au lieu du main config menu
    class GameSettingsBackButton(ui.Button):
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle):
            super().__init__(label=label, style=style, row=4)
            self.guild_id = guild_id
            
        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=str(self.guild_id)).first()
            cog = interaction.client.get_cog("AdminCog")
            # Retourner à la vue principale des paramètres du jeu
            await interaction.response.edit_message(
                embed=cog.generate_game_settings_embed(state),
                view=cog.generate_game_settings_view(self.guild_id)
            )
            db.close()

    def generate_server_config_embed(self, guild_id: int) -> discord.Embed:
        db = SessionLocal()
        state = db.query(ServerState).filter_by(guild_id=str(guild_id)).first()
        db.close()

        if not state:
            desc = "Aucune partie n'est encore initialisée pour ce serveur. Configurez les paramètres pour démarrer."
            embed = discord.Embed(title="⚙️ Paramètres du Serveur", description=desc, color=0x44ff44)
            return embed

        embed = discord.Embed(title=f"⚙️ Paramètres du serveur {guild_id}", color=0x44ff44)
        embed.add_field(name="Salon Principal", value=f"<#{state.main_channel_id}>" if state.main_channel_id else "Non défini", inline=False)
        embed.add_field(name="Portefeuille", value=f"{state.wallet}", inline=True)
        embed.add_field(name="Addiction", value=f"{state.addiction}%", inline=True)
        embed.add_field(name="Santé Physique", value=f"{state.phys}%", inline=True)
        embed.add_field(name="Santé Mentale", value=f"{state.ment}%", inline=True)
        embed.add_field(name="Faim", value=f"{state.food}%", inline=True)
        embed.add_field(name="Hydratation", value=f"{state.water}%", inline=True)
        return embed

    def generate_game_settings_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        view.add_item(self.SetupGameModeButton("🕹️ Choisir le mode de jeu", guild_id, discord.ButtonStyle.primary))
        view.add_item(self.ConfigButton("🎮 Lancer/Reinitialiser Partie", guild_id, discord.ButtonStyle.green, row=0))
        view.add_item(self.ConfigButton("💾 Sauvegarder l'État", guild_id, discord.ButtonStyle.blurple, row=0))
        view.add_item(self.ConfigButton("📊 Voir Statistiques", guild_id, discord.ButtonStyle.gray, row=1))
        view.add_item(self.ConfigButton("🔔 Notifications", guild_id, discord.ButtonStyle.green, row=1))
        view.add_item(self.ConfigButton("🛠 Options Avancées", guild_id, discord.ButtonStyle.secondary, row=2))
        view.add_item(self.BackButton("⬅ Retour au Menu Principal", guild_id, discord.ButtonStyle.red, row=3))
        return view

    # -------------------
    # Boutons Paramètres
    # -------------------
    class ConfigButton(discord.ui.Button):
        def __init__(self, label: str, guild_id: int, style: discord.ButtonStyle, row: int = 0):
            super().__init__(label=label, style=style, row=row)
            self.guild_id = guild_id

        async def callback(self, interaction: discord.Interaction):
            cog = interaction.client.get_cog("AdminCog")
            await interaction.response.edit_message(
                embed=cog.generate_server_config_embed(self.guild_id),
                view=cog.generate_game_settings_view(self.guild_id)
            )

    class BackButton(discord.ui.Button):
        def __init__(self, label: str, guild_id: int, style: discord.ButtonStyle, row: int = 0): # <-- CE CONSTRUCTEUR ATTEND DÉJÀ row
            super().__init__(label=label, style=style, row=row) # et ici il l'utilise pour super()
            self.guild_id = guild_id

        async def callback(self, interaction: discord.Interaction):
            main_embed = interaction.client.get_cog("MainEmbed")
            state = None
            try:
                db_session = SessionLocal()
                state = db_session.query(ServerState).filter_by(guild_id=str(self.guild_id)).first()
                db_session.close()
            except Exception:
                pass

            await interaction.response.edit_message(
                embed=main_embed.generate_menu_embed(state),
                view=main_embed.generate_main_menu(self.guild_id)
            )

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
