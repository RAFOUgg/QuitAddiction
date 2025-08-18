# --- cogs/view_handler.py ---
import discord
from discord.ext import commands
from db.models import PlayerProfile, ServerState
from utils.game_manager import game_manager
from utils.view_manager import view_manager
from utils.error_handler import handle_interaction_error, check_valid_state, GameError
from utils.logger import get_logger

logger = get_logger(__name__)

class ViewHandler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Handle all button interactions"""
        if not interaction.data or not interaction.guild:
            return
            
        try:
            # Get current state
            player, state = await game_manager.get_player_and_state(interaction)
            if not player or not state:
                raise GameError("Game not initialized for this server.")
                
            custom_id = interaction.data.get("custom_id", "")
            guild_id = str(interaction.guild.id)
            
            # Validate state for action-based interactions
            if custom_id.startswith("action_"):
                check_valid_state(player, custom_id[7:])  # Remove "action_" prefix
                
            # Handle navigation
            if custom_id.startswith("nav_"):
                view_type = custom_id[4:]  # Remove "nav_" prefix
                if view_type == "back":
                    previous_view = view_manager.go_back(guild_id)
                    if previous_view:
                        view = self._create_view(previous_view, player, state)
                        view_manager.register_view(guild_id, view, previous_view)
                else:
                    view = self._create_view(view_type, player, state)
                    view_manager.register_view(guild_id, view, view_type)
                    
            # Update game message
            await game_manager.update_game_message(
                interaction,
                player,
                state,
                view_manager.get_active_view(guild_id),
                self._create_embed(player, state, interaction.guild)
            )
            
        except Exception as e:
            await handle_interaction_error(interaction, e)
            
    def _create_view(self, view_type: str, player: PlayerProfile, state: ServerState) -> discord.ui.View:
        """Create the appropriate view based on type"""
        from cogs.main_embed import DashboardView, ActionsView
        from cogs.phone import PhoneMainView
        
        if view_type == "main_menu":
            return DashboardView(player, state)
        elif view_type == "actions":
            return ActionsView(player, state)
        elif view_type == "phone":
            return PhoneMainView(player)
        else:
            return DashboardView(player, state)  # Default to dashboard
            
    def _create_embed(self, player: PlayerProfile, state: ServerState, guild: discord.Guild) -> discord.Embed:
        """Create the appropriate embed for the current view"""
        from cogs.main_embed import MainEmbed
        cog = self.bot.get_cog("MainEmbed")
        if not cog:
            raise GameError("Main embed cog not found!")
        return cog.generate_dashboard_embed(player, state, guild)

async def setup(bot: commands.Bot):
    await bot.add_cog(ViewHandler(bot))
