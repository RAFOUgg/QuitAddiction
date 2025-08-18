from typing import Optional
import discord
from utils.view_base import BaseGameView, ActionButton
from db.models import PlayerProfile, ServerState

class ActionsView(BaseGameView):
    """View for player actions"""
    
    def __init__(self, player: PlayerProfile, server_state: Optional[ServerState] = None):
        """Initialize an actions view"""
        super().__init__(player, server_state)
        self._init_view()
        
    def _init_view(self):
        """Initialize the view"""
        # Get player states
        is_working = getattr(self.player, 'is_working', False)
        is_at_home = getattr(self.player, 'is_at_home', True)
        is_on_break = getattr(self.player, 'is_on_break', False)
        
        if is_working and not is_on_break:
            self._init_work_actions()
        elif is_working and is_on_break:
            self._init_break_actions()
        elif is_at_home:
            self._init_home_actions()
        else:
            self._init_basic_actions()
            
    def _init_work_actions(self):
        """Initialize work-specific actions"""
        # Take break button
        break_button = ActionButton(
            label="Pause",
            style=discord.ButtonStyle.primary,
            custom_id="action_take_break",
            emoji="⏸️"
        )
        break_button.update_state(self)
        self.add_item(break_button)
        
        # Go home button
        home_button = ActionButton(
            label="Rentrer",
            style=discord.ButtonStyle.secondary,
            custom_id="action_go_home",
            emoji="🏠"
        )
        home_button.update_state(self)
        self.add_item(home_button)
        
    def _init_break_actions(self):
        """Initialize break-time actions"""
        # End break button
        end_break_button = ActionButton(
            label="Fin de pause",
            style=discord.ButtonStyle.success,
            custom_id="action_end_break",
            emoji="▶️"
        )
        end_break_button.update_state(self)
        self.add_item(end_break_button)
        
        # Smoke actions
        if getattr(self.player, 'cigarettes', 0) > 0:
            cig_button = ActionButton(
                label="Fumer",
                style=discord.ButtonStyle.danger,
                custom_id="smoke_cigarette_break",
                emoji="🚬",
                requires_inventory="cigarettes"
            )
            cig_button.update_state(self)
            self.add_item(cig_button)
            
    def _init_home_actions(self):
        """Initialize home-specific actions"""
        # Basic needs buttons
        need_buttons = [
            # Sleep action
            ActionButton(
                label="Dormir",
                style=discord.ButtonStyle.secondary,
                custom_id="action_sleep",
                emoji="😴"
            ),
            # Eat action
            ActionButton(
                label="Manger",
                style=discord.ButtonStyle.primary,
                custom_id="action_eat",
                emoji="🍽️",
                requires_inventory="food_servings"
            ),
            # Drink action
            ActionButton(
                label="Boire",
                style=discord.ButtonStyle.primary,
                custom_id="action_drink",
                emoji="💧",
                requires_inventory="water_bottles"
            )
        ]
        
        for button in need_buttons:
            button.update_state(self)
            self.add_item(button)
            
        # Add go to work button during work hours
        if self.state and self.game_time.hour >= 8 and self.game_time.hour < 17:
            work_button = ActionButton(
                label="Aller au travail",
                style=discord.ButtonStyle.success,
                custom_id="action_go_to_work",
                emoji="🏢"
            )
            work_button.update_state(self)
            self.add_item(work_button)
            
    def _init_basic_actions(self):
        """Initialize basic actions available anywhere"""
        back_button = ActionButton(
            label="Retour",
            style=discord.ButtonStyle.secondary,
            custom_id="main_menu",
            emoji="⬅️"
        )
        self.add_item(back_button)
