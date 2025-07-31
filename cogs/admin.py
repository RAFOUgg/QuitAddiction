import discord
from discord.ext import commands
from discord import app_commands

# On importe les fonctions de notre API de base de données
from core.database import get_db_session, get_or_create_server_config, update_staff_role, update_main_channel, get_or_create_cook

# --- Décorateur de Vérification Personnalisé ---

def is_bot_staff():
    """
    Un décorateur de vérification pour les commandes slash.
    Vérifie si l'utilisateur qui exécute la commande a le rôle staff
    configuré pour ce serveur dans la base de données.
    """
    async def predicate(interaction: discord.Interaction) -> bool:
        # Ouvre une session avec la base de données
        session = get_db_session()
        try:
            config = get_or_create_server_config(session, interaction.guild.id)
            staff_role_id = config.staff_role_id
        finally:
            # On s'assure de toujours fermer la session
            session.close()

        if not staff_role_id:
            await interaction.response.send_message(
                "❌ Le rôle du staff n'a pas encore été configuré sur ce serveur.\n"
                "Un administrateur doit d'abord utiliser la commande `/config role`.",
                ephemeral=True
            )
            return False

        # Vérifie si l'utilisateur possède le rôle
        staff_role = interaction.guild.get_role(staff_role_id)
        if staff_role is None or staff_role not in interaction.user.roles:
            await interaction.response.send_message(
                "⛔ Vous n'avez pas la permission d'utiliser cette commande. Elle est réservée au staff.",
                ephemeral=True
            )
            return False
            
        return True
    return app_commands.check(predicate)


# --- Cog d'Administration ---

class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    @app_commands.command(name="config", description="[Admin] Configure les rôles du bot.")
    @app_commands.checks.has_permissions(administrator=True) # Seuls les admins du SERVEUR peuvent faire ça
    async def config_role(self, interaction: discord.Interaction, role: discord.Role):
        """Définit le rôle qui aura les permissions staff pour le bot."""
        session = get_db_session()
        try:
            update_staff_role(session, interaction.guild.id, role.id)
            await interaction.response.send_message(
                f"✅ Le rôle staff a bien été configuré sur **{role.name}**.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"Une erreur est survenue: {e}", ephemeral=True)
        finally:
            session.close()

    @app_commands.command(name="mep", description="[Staff] Lance la mise en place du Cuisinier dans un salon.")
    @app_commands.describe(salon="Le salon où le cuisinier doit s'installer.")
    @is_bot_staff() # Utilise notre décorateur personnalisé pour la permission
    async def mise_en_place(self, interaction: discord.Interaction, salon: discord.TextChannel):
        """Installe le bot et son embed principal dans un salon."""
        session = get_db_session()
        try:
            # Met à jour la config et s'assure que le cuisinier existe dans la DB
            update_main_channel(session, interaction.guild.id, salon.id)
            cook = get_or_create_cook(session, interaction.guild.id)

            # Création de l'embed initial
            embed = discord.Embed(
                title="👨‍🍳 Le Cuisinier est dans la place !",
                description="Bonjour ! C'est ici que je vais passer mes journées.\n"
                            "Gardez un œil sur mes stats et aidez-moi à aller bien.",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url="https://i.imgur.com/example.png") # Mettez une image de base pour le cuisinier
            embed.add_field(name="⚡ Énergie", value=f"{cook.energy}%", inline=True)
            embed.add_field(name="💧 Soif", value=f"{cook.thirst}%", inline=True)
            embed.add_field(name="🍔 Faim", value=f"{cook.hunger}%", inline=True)
            embed.add_field(name="😴 Sommeil", value=f"{cook.sleep}%", inline=True)
            embed.add_field(name="🧠 Craving", value=f"{cook.craving}%", inline=True)
            embed.add_field(name="💰 Portefeuille", value=f"{cook.wallet:.2f} $", inline=True)
            embed.set_footer(text="Utilisez les commandes pour interagir avec moi.")

            await salon.send(embed=embed)
            await interaction.response.send_message(
                f"✅ Le cuisinier a été installé avec succès dans {salon.mention} !",
                ephemeral=True
            )

        except Exception as e:
            await interaction.response.send_message(f"Une erreur est survenue lors de l'installation: {e}", ephemeral=True)
        finally:
            session.close()

    @mise_en_place.error
    @config_role.error
    async def on_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Gère les erreurs de permission pour les commandes de ce cog."""
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "⛔ Vous devez être un administrateur du serveur pour utiliser cette commande.",
                ephemeral=True
            )
        else:
            # Gère d'autres erreurs potentielles non capturées
            await interaction.response.send_message(
                "Une erreur inattendue est survenue.", ephemeral=True
            )
            print(f"Erreur non gérée dans le cog Admin: {error}")


async def setup(bot: commands.Bot):
    """Fonction requise pour que le bot charge ce cog."""
    await bot.add_cog(Admin(bot))