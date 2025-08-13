# --- cogs/scheduler.py (FINAL & CORRECTED WITH UI REFRESH) ---

import discord
from discord.ext import commands, tasks
from db.database import SessionLocal
from db.models import ServerState, PlayerProfile
import datetime
import traceback
from utils.calculations import chain_reactions
from utils.helpers import clamp

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
        main_embed_cog = self.bot.get_cog("MainEmbed")
        cooker_brain = self.bot.get_cog("CookerBrain")
        if not main_embed_cog or not cooker_brain:
            print("Scheduler tick skipped: MainEmbed or CookerBrain cog not ready.")
            return

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
                state_dict = {k: v for k, v in player.__dict__.items() if not k.startswith('_')}
                updated_state = chain_reactions(state_dict)
                for key, value in updated_state.items():
                    if hasattr(player, key): setattr(player, key, value)
                
                # --- 5. ÉVÉNEMENTS ALÉATOIRES (ex: tomber malade) ---
                if not player.is_sick:
                    # Chance de base très faible, augmentée massivement par un système immunitaire bas
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

                # --- 4. MISE À JOUR DE L'INTERFACE & LOGGING ---
                # On met à jour l'UI uniquement s'il y a un changement significatif ou toutes les 5 minutes.
                significant_change = action_taken
                
                # Le logging autonome est géré ici
                if significant_change and action_log_message:
                    # Envoyer un message discret dans le canal
                    try:
                        channel = await self.bot.fetch_channel(int(server_state.game_channel_id))
                        await channel.send(f"**Pendant que vous aviez le dos tourné...**\n> {action_log_message}")
                    except (discord.NotFound, discord.Forbidden): pass
                
                # On rafraîchit TOUJOURS le dashboard principal pour que les stats progressent visuellement.
                try:
                    guild = self.bot.get_guild(int(server_state.guild_id))
                    channel = self.bot.get_channel(int(server_state.game_channel_id))
                    if guild and channel and server_state.game_message_id:
                        game_message = await channel.fetch_message(int(server_state.game_message_id))
                        # IMPORTANT: On met à jour l'embed seulement si l'embed actuel est le dashboard
                        # pour ne pas interrompre l'utilisateur s'il est dans la boutique par ex.
                        if game_message.embeds and game_message.embeds[0].title == "👨‍🍳 Le Quotidien du Cuisinier":
                           new_embed = main_embed_cog.generate_dashboard_embed(player, server_state, guild)
                           # Ne pas changer la vue, juste le contenu de l'embed
                           await game_message.edit(embed=new_embed)
                except (discord.NotFound, discord.Forbidden):
                    print(f"Scheduler: Message/channel {server_state.game_message_id} introuvable pour la guilde {server_state.guild_id}.")
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
        print("Scheduler prêt pour le tick.")

async def setup(bot):
    await bot.add_cog(Scheduler(bot))