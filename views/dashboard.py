from typing import Optional
import discord
from utils.view_base import BaseGameView, ActionButton
from db.models import PlayerProfile, ServerState

class DashboardView(BaseGameView):
    """The main dashboard view for the game"""
    
    def __init__(self, player: PlayerProfile, server_state: Optional[ServerState] = None,
                 show_stats: bool = False, show_inventory: bool = False):
        """Initialize a dashboard view"""
        super().__init__(player, server_state)
        self.show_stats = show_stats or getattr(player, 'show_stats_in_view', False)
        self.show_inventory = show_inventory or getattr(player, 'show_inventory_in_view', False)
        self._init_view()
        
    def _init_view(self):
        """Initialize the view"""
        if getattr(self.player, 'is_sleeping', False):
            self._init_sleep_mode()
        elif self.show_stats:
            self._init_stats_mode()
        elif self.show_inventory:
            self._init_inventory_mode()
        else:
            self._init_default_mode()
            
    def _init_sleep_mode(self):
        """Initialize sleep mode buttons"""
        wake_button = ActionButton(
            label="Réveiller",
            style=discord.ButtonStyle.success,
            custom_id="action_wake_up"
        )
        wake_button.update_state(self)
        self.add_item(wake_button)
        
    def _init_stats_mode(self):
        """Initialize stats view buttons"""
        back_button = ActionButton(
            label="Retour",
            style=discord.ButtonStyle.secondary,
            custom_id="toggle_stats",
            emoji="📊"
        )
        self.add_item(back_button)
        
    def _init_inventory_mode(self):
        """Initialize inventory view buttons"""
        back_button = ActionButton(
            label="Retour",
            style=discord.ButtonStyle.secondary,
            custom_id="toggle_inv",
            emoji="🎒"
        )
        self.add_item(back_button)
        
    def _init_default_mode(self):
        """Initialize default dashboard buttons"""
        # Add main action button
        actions_button = ActionButton(
            label="Actions",
            style=discord.ButtonStyle.primary,
            custom_id="show_actions",
            emoji="🏃‍♂️"
        )
        actions_button.update_state(self)
        self.add_item(actions_button)
        
        # Add stats toggle
        stats_button = ActionButton(
            label="Stats",
            style=discord.ButtonStyle.secondary,
            custom_id="toggle_stats",
            emoji="📊"
        )
        self.add_item(stats_button)
        
        # Add inventory toggle
        inv_button = ActionButton(
            label="Inventaire",
            style=discord.ButtonStyle.secondary,
            custom_id="toggle_inv",
            emoji="🎒"
        )
        self.add_item(inv_button)
        
        # Add phone button if available
        if not self.is_on_cooldown():
            phone_button = ActionButton(
                label="Téléphone",
                style=discord.ButtonStyle.success,
                custom_id="phone_main",
                emoji="📱"
            )
            phone_button.update_state(self)
            self.add_item(phone_button)
