# cogs/admin.py
from discord.ext import commands
import discord
from discord import app_commands
from db.database import SessionLocal
from db.models import ServerState # Assurez-vous que ServerState contient admin_role_id, game_channel_id, game_started
import datetime

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Pas besoin de self.admin_role_id et self.server_channels ici car on utilise la DB

    # --- Commandes Slash pour l'administration ---

    @app_commands.command(name="config", description="Configure les paramètres du bot pour le serveur.")
    @app_commands.default_permissions(administrator=True)
    async def config(self, interaction: discord.Interaction):
        """
        Ouvre l'interface de configuration du bot.
        """
        guild_id = str(interaction.guild.id)
        db = SessionLocal()
        state = db.query(ServerState).filter_by(guild_id=guild_id).first()

        if not state:
            state = ServerState(guild_id=guild_id)
            db.add(state)
            db.commit() # Commit pour initialiser l'état avant de configurer

        # Afficher le menu principal de configuration
        await interaction.response.send_message(
            embed=self.generate_config_menu_embed(state),
            view=self.generate_config_menu_view(guild_id),
            ephemeral=True # Pour que seul l'utilisateur qui a tapé la commande voie la réponse
        )
        db.close()

    # --- Méthodes pour générer les embeds et les vues de configuration ---

    def generate_config_menu_embed(self, state: ServerState) -> discord.Embed:
        embed = discord.Embed(
            title="⚙️ Configuration du Bot",
            description="Choisissez une section à configurer.",
            color=discord.Color.blue()
        )
        # Afficher l'état actuel de la configuration
        admin_role_mention = f"<@&{state.admin_role_id}>" if state.admin_role_id else "Non défini"
        game_channel_mention = f"<#{state.game_channel_id}>" if state.game_channel_id else "Non défini"
        
        embed.add_field(name="👑 Rôle Admin", value=admin_role_mention, inline=True)
        embed.add_field(name="🎮 Salon de Jeu", value=game_channel_mention, inline=True)
        
        if state.game_started:
            embed.add_field(name="▶️ Statut du Jeu", value="En cours", inline=False)
        else:
            embed.add_field(name="▶️ Statut du Jeu", value="Non lancé", inline=False)

        embed.set_footer(text="Utilisez les boutons ci-dessous pour naviguer.")
        return embed

    def generate_config_menu_view(self, guild_id: int) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        # Bouton pour configurer le rôle admin
        view.add_item(self.ConfigButton("👑 Rôle Admin", guild_id, "admin_role", discord.ButtonStyle.secondary))
        # Bouton pour configurer le salon de jeu
        view.add_item(self.ConfigButton("🎮 Salon de Jeu", guild_id, "game_channel", discord.ButtonStyle.secondary))
        # Bouton pour lancer la partie (disponible seulement si config complète)
        view.add_item(self.StartGameButton("▶️ Lancer la partie", guild_id, discord.ButtonStyle.success))
        return view

    # --- Classes pour les boutons de configuration ---

    class ConfigButton(discord.ui.Button):
        def __init__(self, label, guild_id, config_type, style):
            super().__init__(label=label, style=style)
            self.guild_id = guild_id
            self.config_type = config_type # "admin_role" ou "game_channel"

        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=str(self.guild_id)).first()
            cog = interaction.client.get_cog("AdminCog")

            if self.config_type == "admin_role":
                # Afficher un embed et un menu déroulant pour choisir le rôle
                await interaction.response.edit_message(
                    embed=cog.generate_admin_role_config_embed(state),
                    view=cog.generate_admin_role_config_view(self.guild_id)
                )
            elif self.config_type == "game_channel":
                # Afficher un embed et un menu déroulant pour choisir le salon
                await interaction.response.edit_message(
                    embed=cog.generate_game_channel_config_embed(state),
                    view=cog.generate_game_channel_config_view(self.guild_id)
                )
            db.close()

    class StartGameButton(discord.ui.Button):
        def __init__(self, label, guild_id, style):
            super().__init__(label=label, style=style)
            self.guild_id = guild_id

        async def callback(self, interaction: discord.Interaction):
            guild_id = str(self.guild_id)
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=guild_id).first()

            if not state or not state.admin_role_id or not state.game_channel_id:
                await interaction.response.send_message("La configuration est incomplète. Veuillez définir un rôle admin ET un salon de jeu.", ephemeral=True)
                db.close()
                return
            
            if state.game_started:
                await interaction.response.send_message("Une partie est déjà en cours.", ephemeral=True)
                db.close()
                return

            # Marquer le jeu comme lancé
            state.game_started = True
            db.commit()

            # Récupérer le cog MainEmbed pour générer les embeds de jeu
            main_embed_cog = interaction.client.get_cog("MainEmbed")
            if not main_embed_cog:
                await interaction.response.send_message("Erreur interne : Le cog MainEmbed n'a pas été trouvé.", ephemeral=True)
                db.close()
                return

            embed = main_embed_cog.generate_menu_embed(state)
            view = main_embed_cog.generate_main_menu(guild_id)

            game_channel_id = int(state.game_channel_id)
            game_channel = interaction.guild.get_channel(game_channel_id)

            if not game_channel:
                await interaction.response.send_message(f"Le salon de jeu configuré (ID: {state.game_channel_id}) n'a pas été trouvé.", ephemeral=True)
                db.close()
                return

            await game_channel.send(f"La partie commence ! Bienvenue aux joueurs. Utilisez les commandes slash ou les boutons pour interagir.", embed=embed, view=view)
            await interaction.response.send_message("La partie a été lancée dans le salon configuré !", ephemeral=True)
            db.close()

    # --- Méthodes pour gérer les embeds et vues des sous-menus de configuration ---

    # --- Section Rôle Admin ---
    def generate_admin_role_config_embed(self, state: ServerState) -> discord.Embed:
        embed = discord.Embed(
            title="👑 Configuration du Rôle Admin",
            description="Sélectionnez le rôle qui aura les permissions d'administrer le bot.",
            color=discord.Color.purple()
        )
        current_role_mention = f"<@&{state.admin_role_id}>" if state.admin_role_id else "Non défini"
        embed.add_field(name="Rôle Admin actuel", value=current_role_mention, inline=False)
        embed.set_footer(text="Sélectionnez un rôle dans le menu déroulant ci-dessous.")
        return embed

    def generate_admin_role_config_view(self, guild_id: int) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        # Ajout du menu déroulant pour choisir le rôle
        view.add_item(self.RoleSelectMenu(guild_id))
        # Bouton pour retourner au menu principal
        view.add_item(self.BackButton("⬅ Retour", guild_id, discord.ButtonStyle.secondary))
        return view

    class RoleSelectMenu(discord.ui.RoleSelect):
        def __init__(self, guild_id):
            super().__init__(placeholder="Sélectionnez un rôle...", min_values=1, max_values=1)
            self.guild_id = guild_id

        async def callback(self, interaction: discord.Interaction):
            selected_role = self.values[0] # Le rôle sélectionné
            guild_id = str(self.guild_id)
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=guild_id).first()

            if not state: # Normalement déjà créé par /config initial, mais sécurité
                state = ServerState(guild_id=guild_id)
                db.add(state)

            state.admin_role_id = str(selected_role.id)
            db.commit()

            cog = interaction.client.get_cog("AdminCog")
            await interaction.response.edit_message(
                embed=cog.generate_admin_role_config_embed(state), # Réaffiche l'embed mis à jour
                view=cog.generate_admin_role_config_view(guild_id)
            )
            db.close()

    # --- Section Salon de Jeu ---
    def generate_game_channel_config_embed(self, state: ServerState) -> discord.Embed:
        embed = discord.Embed(
            title="🎮 Configuration du Salon de Jeu",
            description="Sélectionnez le salon où le jeu sera affiché.",
            color=discord.Color.green()
        )
        current_channel_mention = f"<#{state.game_channel_id}>" if state.game_channel_id else "Non défini"
        embed.add_field(name="Salon de jeu actuel", value=current_channel_mention, inline=False)
        embed.set_footer(text="Sélectionnez un salon dans le menu déroulant ci-dessous.")
        return embed

    def generate_game_channel_config_view(self, guild_id: int) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        # Ajout du menu déroulant pour choisir le salon
        view.add_item(self.ChannelSelectMenu(guild_id))
        # Bouton pour retourner au menu principal
        view.add_item(self.BackButton("⬅ Retour", guild_id, discord.ButtonStyle.secondary))
        return view

    class ChannelSelectMenu(discord.ui.ChannelSelect):
        def __init__(self, guild_id):
            super().__init__(placeholder="Sélectionnez un salon...", channel_types=[discord.ChannelType.text], min_values=1, max_values=1)
            self.guild_id = guild_id

        async def callback(self, interaction: discord.Interaction):
            selected_channel = self.values[0] # Le salon sélectionné
            guild_id = str(self.guild_id)
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=guild_id).first()

            if not state:
                state = ServerState(guild_id=guild_id)
                db.add(state)

            state.game_channel_id = str(selected_channel.id)
            db.commit()

            cog = interaction.client.get_cog("AdminCog")
            await interaction.response.edit_message(
                embed=cog.generate_game_channel_config_embed(state), # Réaffiche l'embed mis à jour
                view=cog.generate_game_channel_config_view(guild_id)
            )
            db.close()

    # --- Bouton Retour (utilisé dans plusieurs vues de configuration) ---
    class BackButton(discord.ui.Button):
        def __init__(self, label, guild_id, style):
            super().__init__(label=label, style=style)
            self.guild_id = guild_id

        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=str(self.guild_id)).first()
            cog = interaction.client.get_cog("AdminCog")
            # Retourner au menu principal de configuration
            await interaction.response.edit_message(
                embed=cog.generate_config_menu_embed(state),
                view=cog.generate_config_menu_view(self.guild_id)
            )
            db.close()

    # --- Section Statistiques du jeu ---
    def generate_game_stats_embed(self, state: ServerState) -> discord.Embed:
        embed = discord.Embed(
            title="📊 Statistiques de la partie en cours",
            description="Voici les informations sur la partie actuelle.",
            color=discord.Color.gold()
        )
        # Calculez la durée de la partie
        if state.game_start_time: # Supposons que vous ajoutez un champ game_start_time dans ServerState
            start_time = state.game_start_time
            now = datetime.datetime.utcnow()
            duration = now - start_time
            
            # Formatage de la durée (jours, heures, minutes)
            days, seconds = divmod(duration.total_seconds(), 86400)
            hours, seconds = divmod(seconds, 3600)
            minutes, seconds = divmod(seconds, 60)
            
            duration_str = ""
            if days > 0: duration_str += f"{int(days)}j "
            if hours > 0: duration_str += f"{int(hours)}h "
            duration_str += f"{int(minutes)}m"

            embed.add_field(name="Durée écoulée", value=duration_str, inline=False)
        else:
            embed.add_field(name="Durée écoulée", value="La partie n'a pas encore de temps de départ enregistré.", inline=False)

        # Ajout d'autres infos sur les stats joueurs (à implémenter)
        # Par exemple, le top contributeur, le dernier joueur actif, etc.
        # Cela nécessiterait de consulter la table PlayerProfile.

        embed.set_footer(text="Ces informations sont une estimation.")
        return embed

    def generate_game_stats_view(self, guild_id: int) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        # Bouton pour retourner au menu principal
        view.add_item(self.BackButton("⬅ Retour", guild_id, discord.ButtonStyle.secondary))
        # Potentiellement un bouton pour arrêter la partie, réservé aux admins
        # view.add_item(self.StopGameButton("⏹️ Arrêter la partie", guild_id, discord.ButtonStyle.danger))
        return view

    # --- Modification du Menu Principal de Configuration ---
    def generate_config_menu_view(self, guild_id: int) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        view.add_item(self.ConfigButton("👑 Rôle Admin", guild_id, "admin_role", discord.ButtonStyle.secondary))
        view.add_item(self.ConfigButton("🎮 Salon de Jeu", guild_id, "game_channel", discord.ButtonStyle.secondary))
        
        # Ajouter le bouton "Statistiques" uniquement si une partie est en cours
        db = SessionLocal()
        state = db.query(ServerState).filter_by(guild_id=str(guild_id)).first()
        db.close()
        
        if state and state.game_started:
            view.add_item(self.StatsButton("📊 Statistiques", guild_id, discord.ButtonStyle.primary))
        
        # Le bouton Lancer la partie doit aussi vérifier si une partie est déjà en cours
        # La logique est déjà dans le callback du StartGameButton, mais on pourrait le griser ou le cacher
        # si game_started est True. Pour simplifier, on le laisse toujours visible, le bouton retournera une erreur si game_started.

        return view

    # --- Nouvelle classe pour le bouton Statistiques ---
    class StatsButton(discord.ui.Button):
        def __init__(self, label, guild_id, style):
            super().__init__(label=label, style=style)
            self.guild_id = guild_id

        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=str(self.guild_id)).first()
            cog = interaction.client.get_cog("AdminCog")

            await interaction.response.edit_message(
                embed=cog.generate_game_stats_embed(state),
                view=cog.generate_game_stats_view(self.guild_id)
            )
            db.close()
            
    # --- Modification du Bouton Lancer la Partie pour vérifier game_started ---
    class StartGameButton(discord.ui.Button):
        def __init__(self, label, guild_id, style):
            super().__init__(label=label, style=style)
            self.guild_id = guild_id

        async def callback(self, interaction: discord.Interaction):
            guild_id = str(self.guild_id)
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=guild_id).first()

            if not state or not state.admin_role_id or not state.game_channel_id:
                await interaction.response.send_message("La configuration est incomplète. Veuillez définir un rôle admin ET un salon de jeu.", ephemeral=True)
                db.close()
                return
            
            if state.game_started: # Vérification importante ici
                await interaction.response.send_message("Une partie est déjà en cours sur ce serveur.", ephemeral=True)
                db.close()
                return

            # Si aucune partie n'est en cours, on peut la lancer
            state.game_start_time = datetime.datetime.utcnow() # Enregistrer le timestamp actuel
            state.game_started = True
            db.commit()

            # ... (reste de la logique pour envoyer l'embed de jeu) ...
            # Ceci est une copie de ce qui est déjà dans votre code :
            main_embed_cog = interaction.client.get_cog("MainEmbed")
            if not main_embed_cog:
                await interaction.response.send_message("Erreur interne : Le cog MainEmbed n'a pas été trouvé.", ephemeral=True)
                db.close()
                return

            embed = main_embed_cog.generate_menu_embed(state)
            view = main_embed_cog.generate_main_menu(guild_id)

            game_channel_id = int(state.game_channel_id)
            game_channel = interaction.guild.get_channel(game_channel_id)

            if not game_channel:
                await interaction.response.send_message(f"Le salon de jeu configuré (ID: {state.game_channel_id}) n'a pas été trouvé.", ephemeral=True)
                db.close()
                return

            await game_channel.send(f"La partie commence ! Bienvenue aux joueurs. Utilisez les commandes slash ou les boutons pour interagir.", embed=embed, view=view)
            await interaction.response.send_message(f"La partie a été lancée dans {game_channel.mention} !", ephemeral=True)
            db.close()

# --- Setup function ---
async def setup(bot):
    await bot.add_cog(AdminCog(bot))