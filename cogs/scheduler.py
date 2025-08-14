# --- cogs/scheduler.py (CORRECTED & ENHANCED) ---

import discord
from discord.ext import commands, tasks
from db.database import SessionLocal
from db.models import ServerState, PlayerProfile
import datetime
import traceback
from utils.calculations import chain_reactions
from utils.helpers import clamp
import random 
from cogs.main_embed import DashboardView

class Scheduler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        if not self.tick.is_running():
            self.tick.start()
            print("Scheduler tick started.")

    def cog_unload(self):
        self.tick.cancel()

    @tasks.loop(minutes=1)
    async def tick(self):
        main_embed_cog = self.bot.get_cog("MainEmbed")
        if not main_embed_cog:
            return

        current_time = datetime.datetime.utcnow()
        db = SessionLocal()
        try:
            active_games = db.query(ServerState).filter(ServerState.game_started == True).all()
            for server_state in active_games:
                player = db.query(PlayerProfile).filter_by(guild_id=server_state.guild_id).first()
                if not player: continue

                # --- 1. DÉGRADATION ---
                time_delta_minutes = (current_time - player.last_update).total_seconds() / 60
                interval = server_state.game_tick_interval_minutes or 30
                degradation_map = { 'hunger': server_state.degradation_rate_hunger, 'thirst': server_state.degradation_rate_thirst, 'stress': server_state.degradation_rate_stress, 'bladder': server_state.degradation_rate_bladder, 'boredom': server_state.degradation_rate_boredom, 'hygiene': server_state.degradation_rate_hygiene }
                for stat, rate in degradation_map.items():
                    current_val = getattr(player, stat)
                    new_val = clamp(current_val + (rate / interval) * time_delta_minutes, 0, 100)
                    setattr(player, stat, new_val)
                
                # --- 2. RÉACTIONS EN CHAÎNE ---
                time_since_last_smoke = current_time - (player.last_smoked_at or current_time)
                state_dict = {k: v for k, v in player.__dict__.items() if not k.startswith('_')}
                updated_state, new_logs = chain_reactions(state_dict, time_since_last_smoke)
                
                for key, value in updated_state.items():
                    if hasattr(player, key):
                        setattr(player, key, value)
                player.recent_logs = "\n".join(f"- {log}" for log in new_logs)
                
                # --- 3. ÉVÉNEMENTS & NOTIFICATIONS ---
                if player.health < 20 and "Santé critique" not in player.notification_history:
                    notif = "⚠️ Santé critique !"
                    player.notification_history += f"\n{notif}"

                # --- 4. MISE À JOUR ET COMMIT ---
                player.last_update = current_time
                db.commit()

                # --- 5. RAFRAÎCHISSEMENT DE L'INTERFACE (Logique améliorée) ---
                try:
                    guild = self.bot.get_guild(int(server_state.guild_id))
                    channel = self.bot.get_channel(int(server_state.game_channel_id))
                    if guild and channel and server_state.game_message_id:
                        game_message = await channel.fetch_message(int(server_state.game_message_id))
                        
                        # NOUVEAU : On récupère la vue actuelle pour conserver les préférences de l'utilisateur
                        current_view = game_message.view
                        if not isinstance(current_view, DashboardView):
                            # Si la vue est invalide ou a expiré, on en recrée une par défaut
                            current_view = DashboardView()

                        # On passe la vue actuelle à la fonction de génération de l'embed
                        new_embed = main_embed_cog.generate_dashboard_embed(player, server_state, guild, current_view)
                        
                        # On ré-applique la vue pour s'assurer que les boutons ne disparaissent pas
                        await game_message.edit(embed=new_embed, view=current_view)
                except (discord.NotFound, discord.Forbidden):
                    pass # Le message ou le salon a été supprimé, ce n'est pas grave.
                except Exception as e:
                    print(f"Erreur non critique lors du rafraîchissement de l'UI pour la guilde {server_state.guild_id}: {e}")

        except Exception as e:
            print(f"Erreur critique dans la boucle Scheduler.tick: {e}")
            traceback.print_exc()
            db.rollback()
        finally:
            db.close()

async def setup(bot):
    await bot.add_cog(Scheduler(bot))