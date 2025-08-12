import discord
from discord.ext import commands, tasks
from db.database import SessionLocal
from db.models import ServerState, PlayerProfile
import datetime
from utils.calculations import chain_reactions
from utils.helpers import clamp

# --- Constantes pour les seuils de décision ---
HEALTH_CRITICAL_THRESHOLD = 20.0  # En dessous de ça, il DOIT dormir
HUNGER_CRITICAL_THRESHOLD = 85.0  # Au-dessus de ça, il DOIT manger
THIRST_CRITICAL_THRESHOLD = 90.0  # Au-dessus de ça, il DOIT boire

class Scheduler(commands.Cog):
    """Tâches automatiques pour la dégradation ET les actions de survie autonomes."""

    def __init__(self, bot):
        self.bot = bot

    # ... cog_load et cog_unload ne changent pas ...
    async def cog_load(self):
        if not self.tick.is_running():
            self.tick.start()
        print("Scheduler tick started.")

    def cog_unload(self):
        if self.tick.is_running():
            self.tick.cancel()
        print("Scheduler tick cancelled.")

    @tasks.loop(minutes=1)
    async def tick(self):
        main_embed_cog = self.bot.get_cog("MainEmbed")
        cooker_brain = self.bot.get_cog("CookerBrain")
        if not main_embed_cog or not cooker_brain:
            return

        current_time = datetime.datetime.utcnow()
        db = SessionLocal()
        try:
            active_games = db.query(ServerState).filter(ServerState.game_started == True).all()
            
            for server_state in active_games:
                # Récupérer le profil unique du personnage pour ce serveur
                # NOTE: Ce code suppose UN seul personnage/profil par serveur.
                player = db.query(PlayerProfile).filter_by(guild_id=server_state.guild_id).first()
                if not player:
                    continue

                # --- 1. Dégradation des stats (comme avant, mais simplifié) ---
                if not player.last_update: player.last_update = current_time
                time_delta_minutes = (current_time - player.last_update).total_seconds() / 60
                
                # Appliquer la dégradation continue
                # (simplifié pour s'appliquer chaque minute au lieu de par "tick")
                interval = server_state.game_tick_interval_minutes or 30
                player.hunger = self.clamp(player.hunger + (server_state.degradation_rate_hunger / interval) * time_delta_minutes, 0, 100)
                player.thirst = self.clamp(player.thirst + (server_state.degradation_rate_thirst / interval) * time_delta_minutes, 0, 100)
                # ... ajoutez les autres dégradations ici (stress, etc.)

                # --- 2. Cerveau Autonome : Prise de décision ---
                action_log = []
                action_taken = False

                if player.health < HEALTH_CRITICAL_THRESHOLD and not action_taken:
                    log_entry = cooker_brain.perform_sleep(player)
                    action_log.append(f"😴 Se sentant extrêmement faible, il s'est effondré pour dormir. ({log_entry})")
                    action_taken = True

                if player.hunger > HUNGER_CRITICAL_THRESHOLD and not action_taken:
                    log_entry = cooker_brain.perform_eat(player)
                    action_log.append(f"🍔 Tourmenté par la faim, il a dévoré quelque chose. ({log_entry})")
                    action_taken = True

                if player.thirst > THIRST_CRITICAL_THRESHOLD and not action_taken:
                    player.thirst = cooker_brain.perform_drink(player)
                    action_log.append(f"💧 Complètement déshydraté, il a bu une grande quantité d'eau. ({log_entry})")
                    action_taken = True
                
                if player.substance_addiction_level > 20:
                    time_since_last_smoke = (current_time - player.last_smoked_at) if player.last_smoked_at else datetime.timedelta(minutes=999)
                    # Le manque commence après ~2h sans fumer
                    if time_since_last_smoke.total_seconds() > 7200:
                        # Le manque augmente en fonction du niveau d'addiction
                        player.withdrawal_severity = clamp(player.withdrawal_severity + player.substance_addiction_level * 0.02, 0, 100)
                
                player.intoxication_level = clamp(player.intoxication_level - 1.5, 0, 100)
                player.dizziness = clamp(player.dizziness - 2, 0, 100)

                # --- 3. Appliquer les conséquences globales (chain_reactions) ---
                state_dict = {k: v for k, v in player.__dict__.items() if not k.startswith('_')}
                updated_state = chain_reactions(state_dict)
                for key, value in updated_state.items():
                    if hasattr(player, key):
                        setattr(player, key, value)
                
                player.last_update = current_time
                db.commit()
                if action_taken:
                    try:
                        guild = await self.bot.fetch_guild(int(server_state.guild_id))
                        channel = await self.bot.fetch_channel(int(server_state.game_channel_id))
                        msg_to_edit = await channel.fetch_message(int(server_state.game_message_id))
                        
                        # Générer le nouvel embed avec l'état mis à jour
                        new_embed = main_embed_cog.generate_stats_embed(player, guild)
                        
                        await msg_to_edit.edit(embed=new_embed)
                        
                        # Envoyer un message pour informer les joueurs de l'action autonome
                        log_message = "\n".join(action_log)
                        await channel.send(f"**Pendant que vous aviez le dos tourné...**\n>>> {log_message}")

                    except (discord.NotFound, discord.Forbidden) as e:
                        print(f"Scheduler: Impossible de mettre à jour l'interface pour le serveur {server_state.guild_id}. Erreur: {e}")
                    except Exception as e:
                        print(f"Scheduler: Erreur inattendue lors de la mise à jour de l'interface: {e}")

        except Exception as e:
            print(f"Erreur critique dans Scheduler.tick : {e}")
            db.rollback()
        finally:
            db.close()

    def clamp(self, value, min_val, max_val):
        return max(min_val, min(max_val, value))

    @tick.before_loop
    async def before_tick(self):
        await self.bot.wait_until_ready()
        print("Scheduler prêt pour le tick.")

async def setup(bot):
    await bot.add_cog(Scheduler(bot))