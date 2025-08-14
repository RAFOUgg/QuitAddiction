# --- cogs/scheduler.py (CORRECTED) ---

import discord
from discord.ext import commands, tasks
from db.database import SessionLocal
from db.models import ServerState, PlayerProfile
import datetime
import traceback
from utils.calculations import chain_reactions
from utils.helpers import clamp, get_player_notif_settings
from cogs.main_embed import DashboardView

class Scheduler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tick.start()
        print("Scheduler tick task has been started.")

    def cog_unload(self):
        self.tick.cancel()

    async def _send_notification(self, channel: discord.TextChannel, player: PlayerProfile, title: str, message: str, role_id: int | None, notif_key: str):
        # ... (code inchangé)
        settings = get_player_notif_settings(player)
        if not settings.get(notif_key, True): return
        if title in player.notification_history: return
        embed = discord.Embed(title=title, description=message, color=discord.Color.orange())
        content = f"<@&{role_id}>" if role_id else None
        try:
            await channel.send(content=content, embed=embed)
            player.notification_history += f"\n{title}"
        except (discord.Forbidden, discord.HTTPException) as e:
            print(f"Could not send notification to channel {channel.id}: {e}")


    @tasks.loop(minutes=1)
    async def tick(self):
        main_embed_cog = self.bot.get_cog("MainEmbed")
        if not main_embed_cog:
            return

        db = SessionLocal()
        try:
            active_games = db.query(ServerState).filter(ServerState.game_started == True).all()
            for server_state in active_games:
                player = db.query(PlayerProfile).filter_by(guild_id=server_state.guild_id).first()
                if not player: continue

                # --- 1. DÉGRADATION (LOGIQUE CORRIGÉE) ---
                time_delta_minutes = (datetime.datetime.utcnow() - player.last_update).total_seconds() / 60
                
                # Récupère la durée d'un jour de jeu en minutes réelles (ex: 24 pour le test, 1440 pour le temps réel)
                minutes_per_game_day = server_state.game_minutes_per_day
                if not minutes_per_game_day or minutes_per_game_day <= 0:
                    minutes_per_game_day = 1440 # Valeur par défaut de sécurité (24h)

                degradation_map = {
                    'hunger': server_state.degradation_rate_hunger,
                    'thirst': server_state.degradation_rate_thirst,
                    'stress': server_state.degradation_rate_stress,
                    'bladder': server_state.degradation_rate_bladder,
                    'boredom': server_state.degradation_rate_boredom,
                    'hygiene': server_state.degradation_rate_hygiene
                }

                for stat, daily_rate in degradation_map.items():
                    current_val = getattr(player, stat)
                    # Calcule la dégradation par minute en se basant sur la durée du jour
                    degradation_per_minute = daily_rate / minutes_per_game_day
                    change = degradation_per_minute * time_delta_minutes
                    new_val = clamp(current_val + change, 0, 100)
                    setattr(player, stat, new_val)
                
                # --- 2. RÉACTIONS EN CHAÎNE ---
                time_since_last_smoke = datetime.datetime.utcnow() - (player.last_smoked_at or datetime.datetime.utcnow())
                state_dict = {k: v for k, v in player.__dict__.items() if not k.startswith('_')}
                updated_state, new_logs = chain_reactions(state_dict, time_since_last_smoke)
                
                for key, value in updated_state.items():
                    if hasattr(player, key):
                        setattr(player, key, value)
                player.recent_logs = "\n".join(f"- {log}" for log in new_logs)
                
                # --- 4. MISE À JOUR ET COMMIT ---
                player.last_update = datetime.datetime.utcnow()
                db.commit()

                # --- 5. RAFRAÎCHISSEMENT DE L'INTERFACE ---
                try:
                    guild = self.bot.get_guild(int(server_state.guild_id))
                    if guild and server_state.game_channel_id and server_state.game_message_id:
                        channel = await self.bot.fetch_channel(int(server_state.game_channel_id))
                        game_message = await channel.fetch_message(int(server_state.game_message_id))
                        new_embed = main_embed_cog.generate_dashboard_embed(player, server_state, guild)
                        await game_message.edit(embed=new_embed, view=DashboardView(player))
                except (discord.NotFound, discord.Forbidden):
                    pass 
        except Exception as e:
            print(f"Erreur critique dans la boucle Scheduler.tick: {e}")
            traceback.print_exc()
            db.rollback()
        finally:
            db.close()

async def setup(bot):
    await bot.add_cog(Scheduler(bot))