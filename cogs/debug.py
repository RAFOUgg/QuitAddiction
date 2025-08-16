import discord
from discord.ext import commands
from discord import app_commands
from db.database import SessionLocal
from db.models import ServerState, PlayerProfile
from utils.logger import get_logger

logger = get_logger(__name__)

class AdminDebugCommands(commands.GroupCog, name="debug"):
    def __init__(self, bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(name="unlock_all", description="[DEBUG] Débloque tous les achievements et le smoke shop")
    @app_commands.default_permissions(administrator=True)
    async def unlock_all(self, interaction: discord.Interaction):
        db = SessionLocal()
        try:
            # Get player profile
            player = db.query(PlayerProfile).filter_by(guild_id=str(interaction.guild_id)).first()
            if not player:
                await interaction.response.send_message("❌ Profil joueur non trouvé", ephemeral=True)
                return

            # Unlock smoke shop by setting high addiction levels
            player.substance_addiction_level = 100.0
            player.craving_nicotine = 100.0
            player.craving_alcohol = 100.0
            player.craving_cannabis = 100.0
            
            # Give money for testing
            player.money = 1000

            db.commit()
            await interaction.response.send_message("✅ Smoke shop débloqué et argent ajouté !", ephemeral=True)
        except Exception as e:
            db.rollback()
            logger.error(f"Erreur lors du déblocage: {e}")
            await interaction.response.send_message("❌ Une erreur est survenue", ephemeral=True)
        finally:
            db.close()

    @app_commands.command(name="fast_time", description="[DEBUG] Accélère le temps de jeu (x10)")
    @app_commands.default_permissions(administrator=True)
    async def fast_time(self, interaction: discord.Interaction):
        db = SessionLocal()
        try:
            server = db.query(ServerState).filter_by(guild_id=str(interaction.guild_id)).first()
            if not server:
                await interaction.response.send_message("❌ Configuration serveur non trouvée", ephemeral=True)
                return

            # Enable test mode which makes time pass faster
            server.is_test_mode = True
            server.game_tick_interval_minutes = 1  # Update every minute instead of every 30 minutes
            
            db.commit()
            await interaction.response.send_message("✅ Mode accéléré activé ! (1 minute réelle = 2 heures en jeu)", ephemeral=True)
        except Exception as e:
            db.rollback()
            logger.error(f"Erreur lors de l'activation du mode accéléré: {e}")
            await interaction.response.send_message("❌ Une erreur est survenue", ephemeral=True)
        finally:
            db.close()

    @app_commands.command(name="normal_time", description="[DEBUG] Remet la vitesse du temps normale")
    @app_commands.default_permissions(administrator=True)
    async def normal_time(self, interaction: discord.Interaction):
        db = SessionLocal()
        try:
            server = db.query(ServerState).filter_by(guild_id=str(interaction.guild_id)).first()
            if not server:
                await interaction.response.send_message("❌ Configuration serveur non trouvée", ephemeral=True)
                return

            # Disable test mode
            server.is_test_mode = False
            server.game_tick_interval_minutes = 30  # Back to normal update interval
            
            db.commit()
            await interaction.response.send_message("✅ Mode normal réactivé", ephemeral=True)
        except Exception as e:
            db.rollback()
            logger.error(f"Erreur lors de la désactivation du mode accéléré: {e}")
            await interaction.response.send_message("❌ Une erreur est survenue", ephemeral=True)
        finally:
            db.close()

    @app_commands.command(name="reset_cooldowns", description="[DEBUG] Réinitialise tous les cooldowns d'actions")
    @app_commands.default_permissions(administrator=True)
    async def reset_cooldowns(self, interaction: discord.Interaction):
        db = SessionLocal()
        try:
            player = db.query(PlayerProfile).filter_by(guild_id=str(interaction.guild_id)).first()
            if not player:
                await interaction.response.send_message("❌ Profil joueur non trouvé", ephemeral=True)
                return

            # Reset all action timestamps
            player.last_drink = None
            player.last_eat = None
            player.last_sleep = None
            player.last_smoke = None
            player.last_pee = None
            player.last_shower = None
            
            db.commit()
            await interaction.response.send_message("✅ Cooldowns réinitialisés !", ephemeral=True)
        except Exception as e:
            db.rollback()
            logger.error(f"Erreur lors de la réinitialisation des cooldowns: {e}")
            await interaction.response.send_message("❌ Une erreur est survenue", ephemeral=True)
        finally:
            db.close()

    @app_commands.command(name="refill_stats", description="[DEBUG] Remplit toutes les statistiques à 100%")
    @app_commands.default_permissions(administrator=True)
    async def refill_stats(self, interaction: discord.Interaction):
        db = SessionLocal()
        try:
            player = db.query(PlayerProfile).filter_by(guild_id=str(interaction.guild_id)).first()
            if not player:
                await interaction.response.send_message("❌ Profil joueur non trouvé", ephemeral=True)
                return

            # Reset all stats to max
            player.health = 100.0
            player.energy = 100.0
            player.sanity = 100.0
            player.hunger = 0.0
            player.thirst = 0.0
            player.bladder = 0.0
            player.fatigue = 0.0
            player.stress = 0.0
            player.boredom = 0.0
            player.hygiene = 100.0
            player.job_performance = 100.0
            
            db.commit()
            await interaction.response.send_message("✅ Stats remplies à 100% !", ephemeral=True)
        except Exception as e:
            db.rollback()
            logger.error(f"Erreur lors du remplissage des stats: {e}")
            await interaction.response.send_message("❌ Une erreur est survenue", ephemeral=True)
        finally:
            db.close()

async def setup(bot):
    await bot.add_cog(AdminDebugCommands(bot))
