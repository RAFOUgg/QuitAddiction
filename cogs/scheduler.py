# --- cogs/scheduler.py (SYNTAX CORRECTED) ---

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

    async def cog_load(self):
        # S'assure que le tick ne démarre qu'une fois le bot complètement prêt.
        await self.bot.wait_until_ready()
        if not self.tick.is_running():
            self.tick.start()
            print("Scheduler tick started.")

    def cog_unload(self):
        self.tick.cancel()

    @tasks.loop(minutes=1)
    async def tick(self):
        main_embed_cog = self.bot.get_cog("MainEmbed")
        if not main_embed_cog:
            # Attend que le cog principal soit prêt, ne fait rien ce tick-ci.
            return

        current_time = datetime.datetime.utcnow()
        db = SessionLocal()
        try:
            active_games = db.query(ServerState).filter(ServerState.game_started == True).all()
            for server_state in active_games:
                player = db.query(PlayerProfile).filter_by(guild_id=server_state.guild_id).first()
                if not player:
                    continue

                # --- 1. DÉGRADATION & LOGIQUE TEMPORELLE ---
                # (Cette partie est correcte)
                time_delta_minutes = (current_time - player.last_update).total_seconds() / 60
                interval = server_state.game_tick_interval_minutes or 30
                degradation_map = {
                    'hunger': server_state.degradation_rate_hunger, 'thirst': server_state.degradation_rate_thirst,
                    'stress': server_state.degradation_rate_stress, 'bladder': server_state.degradation_rate_bladder,
                    'boredom': server_state.degradation_rate_boredom, 'hygiene': server_state.degradation_rate_hygiene
                }
                for stat, rate in degradation_map.items():
                    current_val = getattr(player, stat)
                    new_val = clamp(current_val + (rate / interval) * time_delta_minutes, 0, 100)
                    setattr(player, stat, new_val)

                if player.substance_addiction_level > 20 and player.last_smoked_at:
                    if (current_time - player.last_smoked_at).total_seconds() > 3600: # 1 heure
                        player.withdrawal_severity = clamp(player.withdrawal_severity + player.substance_addiction_level * 0.015, 0, 100)

                player.intoxication_level = clamp(player.intoxication_level - 1.5, 0, 100)
                
                # --- 2. RÉACTIONS EN CHAÎNE ---
                time_since_last_smoke = current_time - (player.last_smoked_at or current_time)
                state_dict = {k: v for k, v in player.__dict__.items() if not k.startswith('_')}
                updated_state = chain_reactions(state_dict, time_since_last_smoke)
                for key, value in updated_state.items():
                    if hasattr(player, key):
                        setattr(player, key, value)
                
                # --- 3. ÉVÉNEMENTS ALÉATOIRES ---
                # Easter Egg pour la vie sentimentale
                if player.sex_drive > 70 and random.random() < 0.05: # 5% de chance/min si libido haute
                    random_message = random.choice([
                        "Salut, dsl pour hier soir, ma grand-mère est tombée dans les escaliers. On remet ça ?",
                        "Vu. 21:54",
                        "Hey ! Ce soir ça va pas être possible, j'ai aquaponey.",
                        "Désolé, je crois pas que ça va le faire entre nous. T'es un mec bien mais...",
                        "C'est qui ?"
                    ])
                    if not player.messages: player.messages = ""
                    player.messages += f"\n---\nDe: Inconnu\n{random_message}"
                    player.sex_drive = clamp(player.sex_drive - 40, 0, 100) 
                    try:
                        channel = await self.bot.fetch_channel(int(server_state.game_channel_id))
                        await channel.send("📳 Le téléphone du cuisinier a vibré. Il a l'air contrarié...")
                    except (discord.NotFound, discord.Forbidden):
                        pass

                # --- 4. MISE À JOUR ET COMMIT ---
                player.last_update = current_time
                db.commit() # On commit les changements pour ce joueur avant de passer au suivant.

                # --- 5. RAFRAÎCHISSEMENT DE L'INTERFACE ---
                try:
                    guild = self.bot.get_guild(int(server_state.guild_id))
                    channel = self.bot.get_channel(int(server_state.game_channel_id))
                    if guild and channel and server_state.game_message_id:
                        game_message = await channel.fetch_message(int(server_state.game_message_id))
                        if game_message.embeds and "Le Quotidien du Cuisinier" in game_message.embeds[0].title:
                           new_embed = main_embed_cog.generate_dashboard_embed(player, server_state, guild)
                           await game_message.edit(embed=new_embed)
                except (discord.NotFound, discord.Forbidden):
                    # Pas grave si le message a été supprimé.
                    pass
                except Exception as e:
                    print(f"Erreur non critique lors du rafraîchissement de l'UI pour la guilde {server_state.guild_id}: {e}")

        except Exception as e:
            # Attrape toute autre erreur critique durant la boucle pour l'empêcher de planter.
            print(f"Erreur critique dans la boucle Scheduler.tick: {e}")
            traceback.print_exc()
            db.rollback()
        finally:
            # S'assure que la connexion à la BDD est TOUJOURS fermée à la fin de chaque tick.
            db.close()

async def setup(bot):
    await bot.add_cog(Scheduler(bot))