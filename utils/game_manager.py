# --- utils/game_manager.py ---
from typing import Optional, Dict, Any
import discord
from discord.ext import commands
from db.models import PlayerProfile, ServerState
from db.database import SessionLocal
from utils.time_manager import get_current_game_time, is_work_time, is_night
from utils.logger import get_logger

logger = get_logger(__name__)

class GameStateManager:
    def __init__(self):
        self.active_views: Dict[str, discord.ui.View] = {}
        self.active_messages: Dict[str, int] = {}
        
    async def initialize_player_state(self, player: PlayerProfile, server_state: ServerState) -> None:
        """Initialize or update player state based on current game time"""
        game_time = get_current_game_time(server_state)
        
        # First, ensure we're using real time if that's the setting
        if server_state.duration_key == 'real_time':
            server_state.game_start_time = None
            
        # Reset base states
        player.is_sleeping = False
        player.is_working = False
        player.is_on_break = False
        player.is_at_home = True
        player.action_cooldown_end_time = None
        
        # Initialize stats if they're None
        if player.health is None: player.health = 100.0
        if player.energy is None: player.energy = 100.0
        if player.hunger is None: player.hunger = 0.0
        if player.thirst is None: player.thirst = 0.0
        if player.hygiene is None: player.hygiene = 100.0
        if player.bladder is None: player.bladder = 0.0
        if player.bowels is None: player.bowels = 0.0
        if player.stress is None: player.stress = 0.0
        
        # Set state based on time
        hour = game_time.hour
        if is_night(game_time):
            player.is_sleeping = True
            player.is_at_home = True
        elif is_work_time(game_time):
            player.is_working = True
            player.is_at_home = False
            # Check if it's lunch break time (12-14)
            if 12 <= hour < 14:
                player.is_on_break = True
        
        # Set correct state based on time
        if is_night(game_time):
            player.is_sleeping = True
            player.is_at_home = True
        elif is_work_time(game_time):
            player.is_working = True
            player.is_at_home = False
            
    async def update_game_message(self, 
                                interaction: discord.Interaction, 
                                player: PlayerProfile, 
                                server_state: ServerState,
                                view: discord.ui.View,
                                embed: discord.Embed) -> bool:
        """Update the game message with new state"""
        if not interaction.guild or not isinstance(interaction.channel, (discord.TextChannel, discord.Thread)):
            return False
            
        try:
            if server_state.game_message_id:
                message = await interaction.channel.fetch_message(server_state.game_message_id)
                if message:
                    await message.edit(embed=embed, view=view)
                    return True
        except discord.NotFound:
            logger.error(f"Game message not found for guild {server_state.guild_id}")
        except Exception as e:
            logger.error(f"Error updating game message: {e}")
        
        return False
        
    def cleanup_state(self, guild_id: str) -> None:
        """Clean up state for a guild"""
        if guild_id in self.active_views:
            del self.active_views[guild_id]
        if guild_id in self.active_messages:
            del self.active_messages[guild_id]
            
    @staticmethod
    async def get_player_and_state(interaction: discord.Interaction) -> tuple[Optional[PlayerProfile], Optional[ServerState]]:
        """Get player and server state from an interaction"""
        if not interaction.guild:
            return None, None
            
        db = SessionLocal()
        try:
            guild_id = str(interaction.guild.id)
            player = db.query(PlayerProfile).filter_by(guild_id=guild_id).first()
            state = db.query(ServerState).filter_by(guild_id=guild_id).first()
            return player, state
        except Exception as e:
            logger.error(f"Error getting player/state: {e}")
            return None, None
        finally:
            db.close()

# Global instance
game_manager = GameStateManager()
