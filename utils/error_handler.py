# --- utils/error_handler.py ---
from typing import Optional, Tuple, Any
import discord
from discord.ext import commands
from db.models import PlayerProfile, ServerState
from utils.logger import get_logger

logger = get_logger(__name__)

class GameError(Exception):
    """Base class for game-specific errors"""
    def __init__(self, message: str, is_user_facing: bool = True):
        self.message = message
        self.is_user_facing = is_user_facing
        super().__init__(message)

class StateError(GameError):
    """Error for invalid game states"""
    pass

class ActionError(GameError):
    """Error for invalid actions"""
    pass

class ResourceError(GameError):
    """Error for missing resources"""
    pass

async def handle_interaction_error(interaction: discord.Interaction, error: Exception) -> bool:
    """Handle an interaction error, returns True if handled"""
    try:
        if isinstance(error, GameError):
            if error.is_user_facing:
                await interaction.response.send_message(
                    f"⚠️ {error.message}",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "An error occurred. Please try again.",
                    ephemeral=True
                )
            logger.error(f"Game error: {error.message}")
            return True
            
        # Handle Discord-specific errors
        if isinstance(error, discord.errors.NotFound):
            await interaction.response.send_message(
                "That message no longer exists.",
                ephemeral=True
            )
            return True
            
        if isinstance(error, discord.errors.Forbidden):
            await interaction.response.send_message(
                "I don't have permission to do that.",
                ephemeral=True
            )
            return True
            
        # Log unexpected errors
        logger.error(f"Unexpected error: {str(error)}", exc_info=error)
        await interaction.response.send_message(
            "An unexpected error occurred. Please try again later.",
            ephemeral=True
        )
        return True
        
    except Exception as e:
        logger.error(f"Error in error handler: {str(e)}", exc_info=e)
        return False

def check_valid_state(player: PlayerProfile, action: str) -> None:
    """Validate player state for an action"""
    if not player:
        raise StateError("Player not found.")
        
    if player.is_sleeping and action != "wake_up":
        raise StateError("You can't do that while sleeping.")
        
    if player.is_working and action not in ["work_break", "drink_water", "urinate", "defecate"]:
        if not getattr(player, "is_on_break", False):
            raise StateError("You can't do that while working.")
            
    if getattr(player, "action_cooldown_end_time", None):
        raise StateError("You're busy with another action.")
