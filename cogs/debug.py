import discord
from discord.ext import commands
from discord import app_commands
from db.database import SessionLocal
from db.models import ServerState, PlayerProfile
from utils.logger import get_logger
from utils.time_manager import prepare_for_db
import datetime
import pytz

logger = get_logger(__name__)

class DebugCommandsCog(commands.GroupCog, name="dev"):
    def __init__(self, bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(name="dev_unlock", description="[DEBUG] Débloque tous les achievements et le smoke shop")
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

    @app_commands.command(name="dev_fast_time", description="[DEBUG] Accélère le temps de jeu (x10)")
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

    @app_commands.command(name="dev_normal_time", description="[DEBUG] Remet la vitesse du temps normale")
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
            server.duration_key = 'real_time'
            
            db.commit()
            await interaction.response.send_message("✅ Mode normal réactivé (temps réel 1:1)", ephemeral=True)
        except Exception as e:
            db.rollback()
            logger.error(f"Erreur lors de la désactivation du mode accéléré: {e}")
            await interaction.response.send_message("❌ Une erreur est survenue", ephemeral=True)
        finally:
            db.close()

    @app_commands.command(name="dev_set_time", description="[DEBUG] Définit l'heure dans le jeu")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        hour="Heure (0-23)",
        minute="Minute (0-59)",
        speed="Vitesse du temps (1 = temps réel, 2 = x2, etc...)"
    )
    async def set_game_time(
        self, 
        interaction: discord.Interaction, 
        hour: app_commands.Range[int, 0, 23],
        minute: app_commands.Range[int, 0, 59],
        speed: app_commands.Range[int, 1, 60] = 1
    ):
        db = SessionLocal()
        try:
            server = db.query(ServerState).filter_by(guild_id=str(interaction.guild_id)).first()
            if not server:
                await interaction.response.send_message("❌ Configuration serveur non trouvée", ephemeral=True)
                return

            # Calculer la nouvelle heure de début de jeu
            now = datetime.datetime.now(pytz.UTC)
            target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # Configurer la vitesse du temps
            if speed == 1:
                server.duration_key = 'real_time'
            else:
                server.duration_key = 'test'
                server.game_minutes_per_day = 1440 // speed  # 1440 = minutes in a day
            
            # Mettre à jour l'heure de début
            server.game_start_time = prepare_for_db(target_time)
            server.game_tick_interval_minutes = max(1, 30 // speed)  # Ajuster la fréquence des mises à jour
            
            db.commit()
            await interaction.response.send_message(
                f"✅ Heure du jeu réglée sur {hour:02d}:{minute:02d}\n"
                f"Vitesse: x{speed} (1 minute réelle = {speed} minutes en jeu)",
                ephemeral=True
            )
        except Exception as e:
            db.rollback()
            logger.error(f"Erreur lors du réglage de l'heure: {e}")
            await interaction.response.send_message("❌ Une erreur est survenue", ephemeral=True)
        finally:
            db.close()

    @app_commands.command(name="give_items", description="[DEBUG] Donne des objets au joueur")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        item_type="Type d'objet à donner",
        quantity="Quantité à donner"
    )
    @app_commands.choices(item_type=[
        app_commands.Choice(name='Cigarettes', value='cigarettes'),
        app_commands.Choice(name='E-Cigarettes', value='e_cigarettes'),
        app_commands.Choice(name='Joints', value='joints'),
        app_commands.Choice(name='Argent', value='money'),
        app_commands.Choice(name='Sandwichs', value='food_servings'),
        app_commands.Choice(name='Bouteilles d\'eau', value='water_bottles'),
    ])
    async def give_items(
        self, 
        interaction: discord.Interaction, 
        item_type: str,
        quantity: app_commands.Range[int, 1, 100]
    ):
        db = SessionLocal()
        try:
            player = db.query(PlayerProfile).filter_by(guild_id=str(interaction.guild_id)).first()
            if not player:
                await interaction.response.send_message("❌ Profil joueur non trouvé", ephemeral=True)
                return

            # Donner les objets
            current_value = getattr(player, item_type, 0)
            setattr(player, item_type, current_value + quantity)
            
            db.commit()
            await interaction.response.send_message(
                f"✅ Ajouté {quantity} {item_type.replace('_', ' ')} à l'inventaire",
                ephemeral=True
            )
        except Exception as e:
            db.rollback()
            logger.error(f"Erreur lors de l'ajout d'objets: {e}")
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
    await bot.add_cog(DebugCommandsCog(bot))
