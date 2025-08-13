# --- cogs/scheduler.py (FINAL & CORRECTED) ---

import discord
from discord.ext import commands, tasks
from db.database import SessionLocal
from db.models import ServerState, PlayerProfile
import datetime
from utils.calculations import chain_reactions
from utils.helpers import clamp

class Scheduler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        if not self.tick.is_running():
            self.tick.start()
        print("Scheduler tick started.")

    def cog_unload(self):
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
                player = db.query(PlayerProfile).filter_by(guild_id=server_state.guild_id).first()
                if not player: continue

                # --- 1. DÉGRADATION & LOGIQUE TEMPORELLE ---
                if not player.last_update: player.last_update = current_time
                time_delta_minutes = (current_time - player.last_update).total_seconds() / 60
                
                interval = server_state.game_tick_interval_minutes or 30
                player.hunger = clamp(player.hunger + (server_state.degradation_rate_hunger / interval) * time_delta_minutes, 0, 100)
                player.thirst = clamp(player.thirst + (server_state.degradation_rate_thirst / interval) * time_delta_minutes, 0, 100)
                player.stress = clamp(player.stress + (server_state.degradation_rate_stress / interval) * time_delta_minutes, 0, 100)
                player.bladder = clamp(player.bladder + (server_state.degradation_rate_bladder / interval) * time_delta_minutes, 0, 100)

                if player.substance_addiction_level > 20 and player.last_smoked_at:
                    if (current_time - player.last_smoked_at).total_seconds() > 7200:
                        player.withdrawal_severity = clamp(player.withdrawal_severity + player.substance_addiction_level * 0.02, 0, 100)
                
                player.intoxication_level = clamp(player.intoxication_level - 1.5, 0, 100)
                player.dizziness = clamp(player.dizziness - 2, 0, 100)

                # --- 2. ACTIONS AUTONOMES (IA AMÉLIORÉE) ---
                action_log, action_taken = [], False
                if player.health < 20 and not action_taken:
                    cooker_brain.perform_sleep(player); action_log.append("😴 Extrêmement faible, il s'est effondré pour dormir."); action_taken = True
                if player.hunger > 85 and player.food_servings > 0 and not action_taken:
                    cooker_brain.perform_eat(player); action_log.append("🍔 Tourmenté par la faim, il a dévoré quelque chose."); action_taken = True
                if player.thirst > 90 and (player.water_bottles > 0 or player.beers > 0) and not action_taken:
                    log_msg = cooker_brain.perform_drink(player)
                    action_log.append(f"💧 Déshydraté, il a bu. ({log_msg})"); action_taken = True

                # --- NOUVEAU : SYSTÈME D'ÉVÉNEMENTS NARRATIFS ---
                if server_state.game_start_time and not player.has_unlocked_joints:
                    game_duration_hours = (current_time - server_state.game_start_time).total_seconds() / 3600
                    trigger_time = 0.05 if (server_state.game_tick_interval_minutes < 5) else 2.0 
                    
                    if game_duration_hours > trigger_time:
                        player.has_unlocked_joints = True
                        player.joints += 1
                        
                        try:
                            channel = await self.bot.fetch_channel(int(server_state.game_channel_id))
                            await channel.send("📱 **Nouveau message d'un ami :**\n> *\"Hey ! J'suis passé te voir mais t'étais pas là. Je t'ai laissé un petit cadeau pour te détendre après le boulot. Fais-toi plaisir !\"*\n(Vous avez reçu votre premier joint !)")
                        except Exception as e:
                            print(f"Scheduler: Erreur lors de l'envoi de l'event narratif: {e}")

                # --- 3. RÉACTIONS EN CHAÎNE ---
                state_dict = {k: v for k, v in player.__dict__.items() if not k.startswith('_')}
                updated_state = chain_reactions(state_dict)
                for key, value in updated_state.items():
                    if hasattr(player, key): setattr(player, key, value)
                
                player.last_update = current_time
                db.commit()

                # --- 4. MISE À JOUR DE L'INTERFACE ---
                if action_taken:
                    try:
                        guild = await self.bot.fetch_guild(int(server_state.guild_id))
                        channel = await self.bot.fetch_channel(int(server_state.game_channel_id))
                        msg = await channel.fetch_message(int(server_state.game_message_id))
                        
                        # --- MODIFICATION : Utilise la nouvelle fonction avec les stats visibles ---
                        await msg.edit(embed=main_embed_cog.generate_dashboard_embed(player, guild, show_stats=True))
                        await channel.send(f"**Pendant que vous aviez le dos tourné...**\n>>> {''.join(action_log)}")
                    except Exception as e:
                        print(f"Scheduler: Erreur maj interface pour guild {server_state.guild_id}: {e}")

        except Exception as e:
            print(f"Erreur critique dans Scheduler.tick: {e}")
            db.rollback()
        finally:
            db.close()

    @tick.before_loop
    async def before_tick(self):
        await self.bot.wait_until_ready()
        print("Scheduler prêt pour le tick.")

async def setup(bot):
    await bot.add_cog(Scheduler(bot))