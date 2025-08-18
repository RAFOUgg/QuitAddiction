from typing import Optional, Tuple, Any
import discord
from discord.ext import commands
from datetime import datetime, timedelta
from db.models import PlayerProfile, ServerState
from db.database import SessionLocal
from utils.logger import get_logger
from utils.time_manager import get_current_game_time

logger = get_logger(__name__)

class InteractionRouter:
    """Handles routing and processing of button interactions"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    async def handle_interaction(self, 
                               interaction: discord.Interaction,
                               custom_id: str,
                               player: PlayerProfile,
                               state: ServerState,
                               view_manager: Any) -> Tuple[Optional[discord.ui.View], Optional[discord.Embed], str]:
        """Handle a button interaction
        
        Args:
            interaction: The interaction event
            custom_id: The button's custom_id
            player: The current player profile
            state: The current server state
            view_manager: The MainEmbed cog instance for view/embed generation
            
        Returns:
            Tuple of (view, embed, message) where message explains what happened
        """
        # Get required cogs
        cooker_brain = self.bot.get_cog("CookerBrain")
        if not cooker_brain:
            return None, None, "Error: CookerBrain cog not found"
            
        # Initialize result containers
        view = None
        embed = None
        message = ""
        
        try:
            # Phone-related interactions
            if custom_id.startswith("phone_"):
                phone_cog = self.bot.get_cog("Phone")
                if phone_cog:
                    await phone_cog.handle_interaction(interaction, player, state, view_manager)
                    return None, None, ""
            
            # View transitions
            if custom_id == "toggle_stats":
                player.show_stats_in_view = not player.show_stats_in_view
                view = view_manager.create_dashboard_view(player, state, show_stats=player.show_stats_in_view)
                embed = view_manager.generate_dashboard_embed(player, state)
                
            elif custom_id == "toggle_inv":
                player.show_inventory_in_view = not player.show_inventory_in_view
                view = view_manager.create_dashboard_view(player, state, show_inventory=player.show_inventory_in_view)
                embed = view_manager.generate_dashboard_embed(player, state)
                
            elif custom_id == "main_menu":
                view = view_manager.create_dashboard_view(player, state)
                embed = view_manager.generate_dashboard_embed(player, state)
                
            elif custom_id == "show_actions":
                view = view_manager.create_actions_view(player, state)
                embed = view_manager.generate_dashboard_embed(player, state)
                
            # Game actions
            else:
                action_map = {
                    "action_sleep": cooker_brain.perform_sleep,
                    "action_wake_up": cooker_brain.perform_wake_up,
                    "action_eat": cooker_brain.perform_eat_food,
                    "action_drink": cooker_brain.perform_drink_water,
                    # Add other actions here
                }
                
                if custom_id in action_map:
                    try:
                        result = await action_map[custom_id](player, get_current_game_time(state))
                        if isinstance(result, tuple):
                            message = result[0]
                            # Update cooldown if duration provided
                            if len(result) >= 3:
                                duration = result[2]
                                if duration:
                                    player.action_cooldown_end_time = datetime.utcnow() + timedelta(seconds=duration)
                    except Exception as e:
                        logger.error(f"Error executing action {custom_id}: {e}")
                        message = f"Une erreur s'est produite: {str(e)}"
                        
            return view, embed, message
            
        except Exception as e:
            logger.error(f"Error in interaction handler: {e}")
            return None, None, f"Une erreur s'est produite: {str(e)}"
