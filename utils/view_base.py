from typing import Optional
import discord
from discord import ui
from db.models import PlayerProfile, ServerState
import datetime
from utils.time_manager import get_current_game_time, is_work_time, is_night

class BaseGameView(ui.View):
    """Base class for all game views with common functionality"""
    
    def __init__(self, player: PlayerProfile, server_state: Optional[ServerState] = None):
        super().__init__(timeout=None)
        self.player = player
        self.state = server_state
        self.game_time = (get_current_game_time(server_state) 
                         if server_state else datetime.datetime.utcnow())
        self._init_view()
    
    def _init_view(self):
        """Initialize the view. Override in subclasses."""
        pass
    
    def is_on_cooldown(self) -> bool:
        """Check if player is on action cooldown"""
        now = datetime.datetime.utcnow()
        cooldown_end = getattr(self.player, 'action_cooldown_end_time', None)
        return bool(cooldown_end and now < cooldown_end)
    
    def get_player_states(self) -> tuple[bool, bool, bool, bool]:
        """Get current player states
        
        Returns:
            Tuple of (is_working, is_sleeping, is_on_break, is_at_home)
        """
        return (
            getattr(self.player, 'is_working', False),
            getattr(self.player, 'is_sleeping', False),
            getattr(self.player, 'is_on_break', False),
            getattr(self.player, 'is_at_home', True)
        )
    
    def validate_player_state(self):
        """Validate and update player state based on game time"""
        # Ensure basic state attributes exist
        if not hasattr(self.player, 'is_at_home'):
            self.player.is_at_home = True
            
        if not hasattr(self.player, 'is_working'):
            self.player.is_working = False
            
        if not hasattr(self.player, 'is_sleeping'):
            self.player.is_sleeping = False
            
        if not hasattr(self.player, 'is_on_break'):
            self.player.is_on_break = False
        
        # Update state based on game time if available
        if self.state:
            # Work status
            should_be_working = (is_work_time(self.game_time) and 
                               not self.player.is_on_break)
            self.player.is_at_home = not should_be_working
            self.player.is_working = should_be_working
            
            # Sleep status
            if is_night(self.game_time):
                self.player.is_sleeping = True
                self.player.is_working = False
                self.player.is_at_home = True

class ActionButton(ui.Button):
    """A button that handles its own state based on player conditions"""
    
    def __init__(self, *, label: str, custom_id: str, 
                 style: discord.ButtonStyle = discord.ButtonStyle.secondary,
                 emoji: Optional[str] = None, disabled: bool = False,
                 requires_inventory: bool = False):
        super().__init__(
            label=label,
            style=style,
            custom_id=custom_id,
            emoji=emoji,
            disabled=disabled
        )
        self.requires_inventory = requires_inventory
    
    def update_state(self, view: BaseGameView):
        """Update button state based on player conditions"""
        if self.requires_inventory:
            item_count = getattr(view.player, self.requires_inventory, 0)
            self.disabled = item_count <= 0
        
        is_on_cooldown = view.is_on_cooldown()
        is_working, is_sleeping, is_on_break, _ = view.get_player_states()
        
        # Disable during cooldown or sleep
        if is_on_cooldown or is_sleeping:
            self.disabled = True
            return
        
        # Specific button logic
        if self.custom_id == "phone_main":
            self.disabled = is_working and not is_on_break
