# --- cogs/scheduler.py (FINAL & CORRECTED WITH UI REFRESH) ---

import discord
from discord.ext import commands, tasks
from db.database import SessionLocal
from db.models import ServerState, PlayerProfile
import datetime
import traceback
from utils.calculations import chain_reactions
from utils.helpers import clamp
import random 

class Scheduler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Nombre de lignes de log à garder en mode test
        self.max_log_lines = 10

    async def cog_load(self):
        if not self.tick.is_running():
            self.tick.start()
        print("Scheduler tick started.")

    def cog_unload(self):
        self.tick.cancel()
        print("Scheduler tick cancelled.")

    @tasks.loop(minutes=1)
    async def tick(self):
        current_time = datetime.datetime.utcnow()
        db = SessionLocal()
        try:
            active_games = db.query(ServerState).filter(ServerState.game_started == True).all()
            for server_state in active_games:
                player = db.query(PlayerProfile).filter_by(guild_id=server_state.guild_id).first()
                if not player: continue

        current_time = datetime.datetime.utcnow()
        db = SessionLocal()
        try:
            active_games = db.query(ServerState).filter(ServerState.game_started == True).all()
            for server_state in active_games:
                player = db.query(PlayerProfile).filter_by(guild_id=server_state.guild_id).first()
                if not player: continue

                # --- 1. GESTION DE LA MALADIE ---
                # Le joueur est-il malade ? Si oui, vérifie s'il doit guérir.
                if player.is_sick and player.sickness_end_time and current_time > player.sickness_end_time:
                    player.is_sick = False
                    player.sickness_end_time = None
                    try:
                        channel = await self.bot.fetch_channel(int(server_state.game_channel_id))
                        await channel.send("🎉 **Bonne nouvelle !** Vous vous sentez enfin mieux et n'êtes plus malade.")
                    except (discord.NotFound, discord.Forbidden): pass
                
                # --- 2. DÉGRADATION & LOGIQUE TEMPORELLE ---
                time_delta_minutes = (current_time - player.last_update).total_seconds() / 60
                interval = server_state.game_tick_interval_minutes or 30
                
                # Map de dégradation incluant la nouvelle hygiène
                degradation_map = {
                    'hunger': server_state.degradation_rate_hunger, 'thirst': server_state.degradation_rate_thirst,
                    'stress': server_state.degradation_rate_stress, 'bladder': server_state.degradation_rate_bladder,
                    'boredom': server_state.degradation_rate_boredom,
                    'hygiene': server_state.degradation_rate_hygiene # Ajout
                }
                for stat, rate in degradation_map.items():
                    current_val = getattr(player, stat)
                    new_val = clamp(current_val + (rate / interval) * time_delta_minutes, 0, 100)
                    setattr(player, stat, new_val)

                if player.substance_addiction_level > 20 and player.last_smoked_at:
                    if (current_time - player.last_smoked_at).total_seconds() > 7200:
                        player.withdrawal_severity = clamp(player.withdrawal_severity + player.substance_addiction_level * 0.02, 0, 100)
                
                player.intoxication_level = clamp(player.intoxication_level - 1.5, 0, 100)
                player.dizziness = clamp(player.dizziness - 2, 0, 100)

                # --- 3. ACTIONS AUTONOMES (IA AMÉLIORÉE) ---
                action_log_message, action_taken = None, False
                if player.health < 20 and not action_taken:
                    message, _ = cooker_brain.perform_sleep(player); action_log_message = f"😴 {message}"; action_taken = True
                if player.hunger > 85 and player.food_servings > 0 and not action_taken:
                    message, _ = cooker_brain.perform_eat(player); action_log_message = f"🍔 Tourmenté par la faim, il a dévoré quelque chose."; action_taken = True
                if player.thirst > 90 and (player.water_bottles > 0 or player.beers > 0) and not action_taken:
                    message, _ = cooker_brain.perform_drink(player); action_log_message = f"💧 Déshydraté, il a bu."; action_taken = True
                
                # --- 4. RÉACTIONS EN CHAÎNE ---

                time_since_last_smoke = current_time - (player.last_smoked_at or current_time)
                state_dict = {k: v for k, v in player.__dict__.items() if not k.startswith('_')}
                updated_state = chain_reactions(state_dict, time_since_last_smoke)
                for key, value in updated_state.items():
                    if hasattr(player, key): setattr(player, key, value)
                
                # --- NEW: Detailed logging in test mode ---
                
                if server_state.is_test_mode:
                    print(f"[TEST][{server_state.guild_id}] Chain reaction input: {state_dict}")
                    print(f"[TEST][{server_state.guild_id}] Chain reaction output: {updated_state}")
                for key, value in updated_state.items():
                    if hasattr(player, key): setattr(player, key, value)
                
                # --- 5. ÉVÉNEMENTS ALÉATOIRES (ex: tomber malade) ---

                if not player.is_sick:
                    sickness_chance = (100 - player.immune_system) / 5000.0 
                    if random.random() < sickness_chance:
                        player.is_sick = True
                        player.sickness_end_time = current_time + datetime.timedelta(days=2) # Malade pour 2 jours
                        try:
                            channel = await self.bot.fetch_channel(int(server_state.game_channel_id))
                            await channel.send("🤒 **Aïe...** Vous ne vous sentez pas bien du tout. Vous avez probablement attrapé quelque chose. (Vous êtes malade !)")
                        except (discord.NotFound, discord.Forbidden): pass
                
                player.last_update = current_time
                db.commit()

                if player.sex_drive > 70 and random.random() < 0.05: # 5% de chance/min si la libido est haute
                    random_message = random.choice([
                        "Salut, dsl pour hier soir, ma grand-mère est tombée dans les escaliers. On remet ça ?", "Vu. 21:54", "Hey ! Ce soir ça va pas être possible, j'ai aquaponey.",
                        "Désolé, je crois pas que ça va le faire entre nous. T'es un mec bien mais...", "C'est qui ?"
                    ])
                    if not player.messages: player.messages = ""
                    player.messages += f"\n---\nDe: Inconnu\n{random_message}"
                    player.sex_drive = clamp(player.sex_drive - 40, 0, 100) 
                    try:
                        channel = await self.bot.fetch_channel(int(server_state.game_channel_id))
                        await channel.send("📳 Le téléphone du cuisinier a vibré. Il a l'air contrarié...")
                    except (discord.NotFound, discord.Forbidden): pass
                
                player.last_update = current_time
                db.commit()
                try:
                    guild = self.bot.get_guild(int(server_state.guild_id))
                    channel = self.bot.get_channel(int(server_state.game_channel_id))
                    if guild and channel and server_state.game_message_id:
                        game_message = await channel.fetch_message(int(server_state.game_message_id))
                        if game_message.embeds and "Le Quotidien du Cuisinier" in game_message.embeds[0].title:
                           main_embed_cog = self.bot.get_cog("MainEmbed")
                           if main_embed_cog:
                               new_embed = main_embed_cog.generate_dashboard_embed(player, server_state, guild)
                               await game_message.edit(embed=new_embed)
                except (discord.NotFound, discord.Forbidden):
                    pass # Le message a été supprimé, pas grave
                except Exception as e:
                    print(f"Erreur lors du rafraîchissement de l'UI par le scheduler: {e}")
                    traceback.print_exc()
        except Exception as e:
            print(f"Erreur critique dans Scheduler.tick: {e}")
            traceback.print_exc()
            db.rollback()
        finally:
            db.close()
            
    @tick.before_loop
    async def before_tick(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Scheduler(bot))