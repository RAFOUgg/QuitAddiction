# --- utils/view_manager.py ---
from typing import Optional, Dict, Any
import discord
from discord.ext import commands
from db.models import PlayerProfile, ServerState
from utils.logger import get_logger

logger = get_logger(__name__)

class ViewState:
    def __init__(self):
        self.current_view: Optional[str] = None
        self.previous_view: Optional[str] = None
        self.view_stack: list[str] = []
        
    def push_view(self, view_type: str):
        if self.current_view:
            self.previous_view = self.current_view
            self.view_stack.append(self.current_view)
        self.current_view = view_type
        
    def pop_view(self) -> Optional[str]:
        if self.view_stack:
            self.current_view = self.view_stack.pop()
            self.previous_view = self.view_stack[-1] if self.view_stack else None
            return self.current_view
        return None

class ViewManager:
    def __init__(self):
        self.view_states: Dict[str, ViewState] = {}
        self.active_views: Dict[str, discord.ui.View] = {}
        
    def get_view_state(self, guild_id: str) -> ViewState:
        """Get or create view state for a guild"""
        if guild_id not in self.view_states:
            self.view_states[guild_id] = ViewState()
        return self.view_states[guild_id]
        
    def register_view(self, guild_id: str, view: discord.ui.View, view_type: str):
        """Register a new view for a guild"""
        self.active_views[guild_id] = view
        view_state = self.get_view_state(guild_id)
        view_state.push_view(view_type)
        
    def get_active_view(self, guild_id: str) -> Optional[discord.ui.View]:
        """Get the currently active view for a guild"""
        return self.active_views.get(guild_id)
        
    def go_back(self, guild_id: str) -> Optional[str]:
        """Go back to the previous view type"""
        view_state = self.get_view_state(guild_id)
        return view_state.pop_view()
        
    def cleanup_guild(self, guild_id: str):
        """Clean up all view state for a guild"""
        if guild_id in self.view_states:
            del self.view_states[guild_id]
        if guild_id in self.active_views:
            del self.active_views[guild_id]

# Global instance
view_manager = ViewManager()
