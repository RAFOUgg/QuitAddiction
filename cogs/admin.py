# cogs/admin.py

from discord.ext import commands
import discord
from discord import app_commands

# Assurez-vous que vos modèles et SessionLocal sont bien accessibles
# Le chemin exact dépendra de la structure de votre dossier db
# Si database.py est dans db/, et SessionLocal est importé là, vous pouvez faire:
from db.database import SessionLocal, Base
from db.models import ServerState # On a besoin de ServerState pour gérer le salon du jeu

# Les autres imports nécessaires
from sqlalchemy import Column, String, Integer, Float, DateTime # Pour le modèle ServerState

# Il est possible que vous deviez définir les modèles SQLAlchemy ici aussi si ils ne sont pas automatiquement rechargés.
# Mais le plus propre est de les avoir dans db/models.py et de les importer.

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.admin_role_id = {} # Dictionnaire pour stocker l'ID du rôle admin par guild_id

    # --- Commandes Slash pour l'administration ---

    @app_commands.command(name="config", description="Configure les paramètres du bot pour le serveur.")
    @app_commands.describe(
        admin_role="Le rôle qui aura les permissions d'administrer le bot.",
        game_channel="Le salon où le jeu sera affiché et les interactions principales auront lieu."
    )
    @app_commands.default_permissions(administrator=True) # Seuls les administrateurs Discord peuvent utiliser cette commande
    async def config(self, interaction: discord.Interaction, admin_role: discord.Role = None, game_channel: discord.TextChannel = None):
        """
        Permet aux administrateurs de configurer le bot pour le serveur.
        """
        guild_id = str(interaction.guild.id)
        db = SessionLocal()
        state = db.query(ServerState).filter_by(guild_id=guild_id).first()

        if not state:
            state = ServerState(guild_id=guild_id)
            db.add(state)
            # Ne pas commiter immédiatement, on va ajouter les autres config

        # Mettre à jour le rôle administrateur
        if admin_role:
            self.admin_role_id[guild_id] = admin_role.id # Stocker l'ID pour référence interne au cog
            state.admin_role_id = str(admin_role.id) # Stocker l'ID dans la DB
            await interaction.response.send_message(f"✅ Le rôle administrateur pour le bot est maintenant : {admin_role.mention}.", ephemeral=True)
        else:
            # Si on veut pouvoir retirer le rôle admin via la commande, il faudrait gérer ça.
            # Pour l'instant, on ne fait rien si admin_role n'est pas spécifié.
            pass

        # Mettre à jour le salon du jeu
        if game_channel:
            state.game_channel_id = str(game_channel.id) # Stocker l'ID du salon dans la DB
            await interaction.response.send_message(f"✅ Le salon principal du jeu est maintenant : {game_channel.mention}.", ephemeral=True)
        else:
            # Si on veut pouvoir retirer le salon via la commande, il faudrait gérer ça.
            pass

        # Sauvegarder les changements dans la base de données
        db.commit()
        db.close()

        # Si aucune modification n'a été faite, prévenir l'utilisateur
        if not admin_role and not game_channel:
            await interaction.response.send_message("Veuillez spécifier un rôle admin ou un salon de jeu pour configurer.", ephemeral=True)
        else:
            # Si au moins une modification a été faite, un message d'éphemère a déjà été envoyé.
            # On peut ajouter un message général pour confirmer.
            await interaction.followup.send(f"Configuration mise à jour pour le serveur **{interaction.guild.name}**.", ephemeral=True)


    @app_commands.command(name="startgame", description="Lance la partie pour le serveur.")
    @app_commands.default_permissions(administrator=True)
    async def startgame(self, interaction: discord.Interaction):
        """
        Lance la partie dans le salon configuré.
        """
        guild_id = str(interaction.guild.id)
        db = SessionLocal()
        state = db.query(ServerState).filter_by(guild_id=guild_id).first()

        if not state:
            await interaction.response.send_message("Le bot n'est pas configuré pour ce serveur. Utilisez `/config` d'abord.", ephemeral=True)
            db.close()
            return
        
        if not state.admin_role_id or not state.game_channel_id:
            await interaction.response.send_message("La configuration du bot est incomplète. Veuillez définir un rôle admin ET un salon de jeu avec `/config`.", ephemeral=True)
            db.close()
            return

        # Récupérer le salon de jeu configuré
        game_channel_id = int(state.game_channel_id)
        game_channel = interaction.guild.get_channel(game_channel_id)

        if not game_channel:
            await interaction.response.send_message(f"Le salon de jeu configuré (ID: {state.game_channel_id}) n'a pas été trouvé. Veuillez le reconfigurer avec `/config`.", ephemeral=True)
            db.close()
            return

        # Générer l'embed et la vue du menu principal
        # Vous aurez besoin d'importer le cog MainEmbed pour réutiliser ses méthodes,
        # ou bien de les rendre disponibles d'une autre manière.
        # Pour simplifier ici, je vais les réutiliser directement, mais ce n'est pas la meilleure pratique.
        # Idéalement, le cog MainEmbed serait accessible depuis le bot instance.

        # Récupérer l'instance du cog MainEmbed
        main_embed_cog = interaction.client.get_cog("MainEmbed")
        if not main_embed_cog:
            await interaction.response.send_message("Erreur interne : Le cog MainEmbed n'a pas été trouvé.", ephemeral=True)
            db.close()
            return

        # Vérifier si le jeu est déjà lancé
        # Une façon de faire serait de stocker un état "game_started" dans ServerState
        if state.game_started: # Supposons que vous ajoutez un booléen game_started dans ServerState
            await interaction.response.send_message("Une partie est déjà en cours sur ce serveur.", ephemeral=True)
            db.close()
            return

        # Marquer le jeu comme lancé
        state.game_started = True
        db.commit()

        embed = main_embed_cog.generate_menu_embed(state)
        view = main_embed_cog.generate_main_menu(guild_id)

        # Envoyer le message dans le salon configuré
        await game_channel.send(f"La partie commence ! Bienvenue aux joueurs. Utilisez les commandes slash ou les boutons pour interagir.", embed=embed, view=view)
        
        # Répondre à l'interaction slash
        await interaction.response.send_message(f"La partie a été lancée dans {game_channel.mention} !", ephemeral=True)
        db.close()


# --- Setup function ---
async def setup(bot):
    await bot.add_cog(AdminCog(bot))