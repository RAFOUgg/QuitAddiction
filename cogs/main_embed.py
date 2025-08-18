import discord
from discord.ext import commands
from typing import Dict, Optional
import asyncio

from utils.game_manager import GameManager
from utils.view_manager import ViewManager
from utils.embed_builder import generate_progress_bar
from db.models import PlayerProfile, ServerState

class DashboardView(discord.ui.View):
    """Main dashboard view with player controls.
    
    Provides access to core game actions like checking stats,
    inventory, sleeping, and working. The view adapts its available
    buttons based on the player's current state.
    
    Attributes:
        player (PlayerProfile): The player associated with this view.
        show_stats (bool): Whether to display player stats in the view.
        show_inventory (bool): Whether to display inventory in the view.
    """
    
    def __init__(self, player: PlayerProfile, show_stats: bool = False, show_inventory: bool = False):
        """Initialize dashboard view."""
        super().__init__(timeout=None)
        self.player = player
        self.show_stats = show_stats
        self.show_inventory = show_inventory
        self._init_buttons()
        
    def _init_buttons(self):
        """Initialize the view's buttons based on state."""
        # Add base buttons that are always available
        self.add_item(discord.ui.Button(label="Statistiques", style=discord.ButtonStyle.primary, custom_id="stats"))
        self.add_item(discord.ui.Button(label="Inventaire", style=discord.ButtonStyle.secondary, custom_id="inventory"))
        
        # Add conditional buttons based on player state
        if not getattr(self.player, 'is_sleeping', False):
            self.add_item(discord.ui.Button(label="Dormir", style=discord.ButtonStyle.secondary, custom_id="sleep"))
        if not getattr(self.player, 'is_working', False):
            self.add_item(discord.ui.Button(label="Travailler", style=discord.ButtonStyle.success, custom_id="work"))

class ActionsView(discord.ui.View):
    """View for player actions (work, smoke, drink, etc).
    
    Shows situation-specific action buttons based on player state
    and inventory. For example, shows work controls when working,
    and consumption controls based on available items.
    
    Attributes:
        player (PlayerProfile): The player associated with this view.
        server_state (ServerState): The current server state.
    """
    
    def __init__(self, player: PlayerProfile, server_state: ServerState):
        """Initialize actions view."""
        super().__init__(timeout=None)
        self.player = player
        self.server_state = server_state
        self._init_buttons()
        
    def _init_buttons(self):
        """Initialize the view's action buttons."""
        # Work related buttons
        if getattr(self.player, 'is_working', False):
            self.add_item(discord.ui.Button(label="Pause", style=discord.ButtonStyle.secondary, custom_id="break"))
            self.add_item(discord.ui.Button(label="Quitter", style=discord.ButtonStyle.danger, custom_id="quit_work"))
        
        # Add smoke buttons if player has items
        if getattr(self.player, 'cigarettes', 0) > 0:
            self.add_item(discord.ui.Button(label="Fumer une cigarette", style=discord.ButtonStyle.secondary, custom_id="smoke_cigarette"))
        if getattr(self.player, 'e_cigarettes', 0) > 0:
            self.add_item(discord.ui.Button(label="Vapoter", style=discord.ButtonStyle.secondary, custom_id="vape"))
        if getattr(self.player, 'joints', 0) > 0:
            self.add_item(discord.ui.Button(label="Fumer un joint", style=discord.ButtonStyle.secondary, custom_id="smoke_joint"))
            
        # Always show drink water button
        self.add_item(discord.ui.Button(label="Boire de l'eau", style=discord.ButtonStyle.primary, custom_id="drink_water"))

class MainEmbed(commands.Cog):
    """Main game interface cog for managing player interactions and views."""
    
    def __init__(self, bot):
        """Initialize the cog."""
        self.bot = bot
        self.active_views = {}  # Track active views per guild
        self.view_states = {}  # Track current view state per guild
        self.view_expiry_tasks = {}  # Track cleanup tasks per guild
        self.view_locks = {}  # Lock per guild to prevent race conditions
    
    async def _schedule_view_cleanup(self, guild_id: str):
        """Schedule cleanup of inactive views."""
        try:
            await asyncio.sleep(900)  # 15 minutes
            if guild_id in self.active_views:
                del self.active_views[guild_id]
            if guild_id in self.view_states:
                del self.view_states[guild_id]
            if guild_id in self.view_expiry_tasks:
                del self.view_expiry_tasks[guild_id]
        except asyncio.CancelledError:
            pass  # Task was cancelled, probably because a new view was created

    async def cleanup_views(self, guild_id: str):
        """Clean up views for a guild immediately."""
        if guild_id in self.view_expiry_tasks:
            self.view_expiry_tasks[guild_id].cancel()
            del self.view_expiry_tasks[guild_id]
        if guild_id in self.active_views:
            del self.active_views[guild_id]
        if guild_id in self.view_states:
            del self.view_states[guild_id]

    async def acquire_view_lock(self, guild_id: str):
        """Acquire a lock for view operations in a guild."""
        if guild_id not in self.view_locks:
            self.view_locks[guild_id] = asyncio.Lock()
        await self.view_locks[guild_id].acquire()

    def release_view_lock(self, guild_id: str):
        """Release the view lock for a guild."""
        if guild_id in self.view_locks and self.view_locks[guild_id].locked():
            self.view_locks[guild_id].release()

    def get_view_for_player(self, player: PlayerProfile, server_state: ServerState, force_new: bool = False) -> discord.ui.View:
        """Get the appropriate view for a player's current state."""
        guild_id = player.guild_id
        
        # Cancel any existing cleanup task
        if guild_id in self.view_expiry_tasks:
            self.view_expiry_tasks[guild_id].cancel()
            del self.view_expiry_tasks[guild_id]
            
        # Determine the appropriate view type based on state
        view_type = self._determine_view_type(player, server_state)
        current_state = self.view_states.get(guild_id, {"type": None, "view": None})
        
        # Only create new view if type changes or force_new
        if force_new or current_state["type"] != view_type:
            view = self._create_view(view_type, player, server_state)
            self.active_views[guild_id] = view
            self.view_states[guild_id] = {"type": view_type, "view": view}
            
            # Schedule cleanup after 15 minutes of inactivity
            task = self.bot.loop.create_task(self._schedule_view_cleanup(guild_id))
            self.view_expiry_tasks[guild_id] = task
            return view
            
        return self.active_views[guild_id]

    def _determine_view_type(self, player: PlayerProfile, server_state: ServerState) -> str:
        """Determine which view type should be shown based on player state."""
        if player.is_sleeping:
            return "sleep"
        elif player.is_working:
            return "work"
        elif getattr(player, 'show_stats_in_view', False):
            return "stats"
        elif getattr(player, 'show_inventory_in_view', False):
            return "inventory"
        else:
            return "dashboard"

    def _create_view(self, view_type: str, player: PlayerProfile, server_state: ServerState) -> discord.ui.View:
        """Create the appropriate view based on the determined type."""
        if view_type == "dashboard":
            return DashboardView(player)
        elif view_type == "actions":
            return ActionsView(player, server_state)
        elif view_type == "stats":
            return DashboardView(player, show_stats=True)
        elif view_type == "inventory":
            return DashboardView(player, show_inventory=True)
        elif view_type == "sleep":
            return DashboardView(player)  # Sleep state handled by UI update
        elif view_type == "work":
            return ActionsView(player, server_state)
        else:
            return DashboardView(player)

    async def generate_dashboard_embed(self, player: PlayerProfile, server_state: ServerState, guild: discord.Guild) -> discord.Embed:
        """Generate the dashboard embed."""
        embed = discord.Embed(title="Tableau de bord", color=discord.Color.blue())
        # Add embed fields based on player state
        embed.add_field(name="Status", value=self._get_player_status(player), inline=False)
        if getattr(player, 'show_stats_in_view', False):
            embed.add_field(name="Statistiques", value=self._get_player_stats(player), inline=False)
        if getattr(player, 'show_inventory_in_view', False):
            embed.add_field(name="Inventaire", value=self._get_player_inventory(player), inline=False)
        embed.set_footer(text=f"Serveur: {guild.name}")
        return embed

    def _get_player_status(self, player: PlayerProfile) -> str:
        """Get the player's current status text."""
        status = []
        if getattr(player, 'is_sleeping', False):
            status.append("💤 Endormi")
        if getattr(player, 'is_working', False):
            status.append("💼 Au travail")
        if getattr(player, 'is_on_break', False):
            status.append("☕ En pause")
        if not status:
            status.append("🆓 Disponible")
        return " | ".join(status)

    def _get_player_stats(self, player: PlayerProfile) -> str:
        """Get a formatted string of player stats."""
        stats = [
            f"💪 Énergie: {generate_progress_bar(getattr(player, 'energy', 0), 100)}",
            f"🍖 Faim: {generate_progress_bar(getattr(player, 'hunger', 0), 100)}",
            f"🌊 Soif: {generate_progress_bar(getattr(player, 'thirst', 0), 100)}",
            f"💰 Argent: {getattr(player, 'money', 0)}€"
        ]
        return "\n".join(stats)

    def _get_player_inventory(self, player: PlayerProfile) -> str:
        """Get a formatted string of player inventory."""
        inv = []
        if getattr(player, 'cigarettes', 0):
            inv.append(f"🚬 Cigarettes: {player.cigarettes}")
        if getattr(player, 'e_cigarettes', 0):
            inv.append(f"💨 Vapoteuse: {player.e_cigarettes}")
        if getattr(player, 'joints', 0):
            inv.append(f"🌿 Joints: {player.joints}")
        if getattr(player, 'has_bong', False):
            inv.append("🌊 Bong disponible")
        if not inv:
            return "Inventaire vide"
        return "\n".join(inv)

    # Interaction handling methods
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Handle button interactions."""
        if not interaction.guild_id:
            return
        
        guild = interaction.guild
        if not guild or not isinstance(guild, discord.Guild):
            return
        
        # Get the custom ID from the interaction
        data = getattr(interaction, 'data', {})
        if isinstance(data, dict):
            custom_id = data.get('custom_id')
            if not isinstance(custom_id, str):
                return
        else:
            return
            
        await self.acquire_view_lock(str(interaction.guild_id))
        try:
            # Process the interaction based on the custom_id
            handlers = {
                'stats': lambda i: self._handle_stats_button(i, guild),
                'inventory': lambda i: self._handle_inventory_button(i, guild),
                'sleep': lambda i: self._handle_sleep_button(i, guild),
                'work': lambda i: self._handle_work_button(i, guild),
                'break': lambda i: self._handle_break_button(i, guild),
                'quit_work': lambda i: self._handle_quit_work_button(i, guild),
                'smoke_cigarette': lambda i: self._handle_smoke_button(i, guild),
                'vape': lambda i: self._handle_vape_button(i, guild),
                'smoke_joint': lambda i: self._handle_joint_button(i, guild),
                'drink_water': lambda i: self._handle_drink_button(i, guild)
            }
            
            handler = handlers.get(custom_id)
            if handler:
                await handler(interaction)
            
        finally:
            self.release_view_lock(str(interaction.guild_id))

    async def _handle_stats_button(self, interaction: discord.Interaction, guild: discord.Guild):
        """Handle stats button click."""
        # Update player stats visibility and refresh view
        player = await PlayerProfile.get(interaction.user.id)
        server_state = await ServerState.get(interaction.guild_id)
        player.show_stats_in_view = not getattr(player, 'show_stats_in_view', False)
        await player.save()
        
        view = self.get_view_for_player(player, server_state, force_new=True)
        embed = await self.generate_dashboard_embed(player, server_state, guild)
        await interaction.response.edit_message(embed=embed, view=view)

    async def _handle_inventory_button(self, interaction: discord.Interaction, guild: discord.Guild):
        """Handle inventory button click."""
        player = await PlayerProfile.get(interaction.user.id)
        server_state = await ServerState.get(interaction.guild_id)
        player.show_inventory_in_view = not getattr(player, 'show_inventory_in_view', False)
        await player.save()
        
        view = self.get_view_for_player(player, server_state, force_new=True)
        embed = await self.generate_dashboard_embed(player, server_state, guild)
        await interaction.response.edit_message(embed=embed, view=view)

    async def _handle_sleep_button(self, interaction: discord.Interaction, guild: discord.Guild):
        """Handle sleep button click."""
        player = await PlayerProfile.get(interaction.user.id)
        server_state = await ServerState.get(interaction.guild_id)
        
        if not getattr(player, 'is_sleeping', False):
            player.is_sleeping = True
            await player.save()
            
        view = self.get_view_for_player(player, server_state, force_new=True)
        embed = await self.generate_dashboard_embed(player, server_state, guild)
        await interaction.response.edit_message(embed=embed, view=view)

    async def _handle_work_button(self, interaction: discord.Interaction, guild: discord.Guild):
        """Handle work button click."""
        player = await PlayerProfile.get(interaction.user.id)
        server_state = await ServerState.get(interaction.guild_id)
        
        if not getattr(player, 'is_working', False):
            player.is_working = True
            await player.save()
            
        view = self.get_view_for_player(player, server_state, force_new=True)
        embed = await self.generate_dashboard_embed(player, server_state, guild)
        await interaction.response.edit_message(embed=embed, view=view)

    async def _handle_break_button(self, interaction: discord.Interaction, guild: discord.Guild):
        """Handle break button click."""
        player = await PlayerProfile.get(interaction.user.id)
        server_state = await ServerState.get(interaction.guild_id)
        
        if getattr(player, 'is_working', False) and not getattr(player, 'is_on_break', False):
            player.is_on_break = True
            await player.save()
            
        view = self.get_view_for_player(player, server_state, force_new=True)
        embed = await self.generate_dashboard_embed(player, server_state, guild)
        await interaction.response.edit_message(embed=embed, view=view)

    async def _handle_quit_work_button(self, interaction: discord.Interaction, guild: discord.Guild):
        """Handle quit work button click."""
        player = await PlayerProfile.get(interaction.user.id)
        server_state = await ServerState.get(interaction.guild_id)
        
        if getattr(player, 'is_working', False):
            player.is_working = False
            player.is_on_break = False
            await player.save()
            
        view = self.get_view_for_player(player, server_state, force_new=True)
        embed = await self.generate_dashboard_embed(player, server_state, guild)
        await interaction.response.edit_message(embed=embed, view=view)

    async def _handle_smoke_button(self, interaction: discord.Interaction, guild: discord.Guild):
        """Handle smoke cigarette button click."""
        player = await PlayerProfile.get(interaction.user.id)
        server_state = await ServerState.get(interaction.guild_id)
        
        if getattr(player, 'cigarettes', 0) > 0:
            player.cigarettes -= 1
            # Additional effects handled by the game manager
            await player.save()
            
        view = self.get_view_for_player(player, server_state, force_new=True)
        embed = await self.generate_dashboard_embed(player, server_state, guild)
        await interaction.response.edit_message(embed=embed, view=view)

    async def _handle_vape_button(self, interaction: discord.Interaction, guild: discord.Guild):
        """Handle vape button click."""
        player = await PlayerProfile.get(interaction.user.id)
        server_state = await ServerState.get(interaction.guild_id)
        
        if getattr(player, 'e_cigarettes', 0) > 0:
            # E-cigarette effects handled by game manager
            await player.save()
            
        view = self.get_view_for_player(player, server_state, force_new=True)
        embed = await self.generate_dashboard_embed(player, server_state, guild)
        await interaction.response.edit_message(embed=embed, view=view)

    async def _handle_joint_button(self, interaction: discord.Interaction, guild: discord.Guild):
        """Handle smoke joint button click."""
        player = await PlayerProfile.get(interaction.user.id)
        server_state = await ServerState.get(interaction.guild_id)
        
        if getattr(player, 'joints', 0) > 0:
            player.joints -= 1
            # Joint effects handled by game manager
            await player.save()
            
        view = self.get_view_for_player(player, server_state, force_new=True)
        embed = await self.generate_dashboard_embed(player, server_state, guild)
        await interaction.response.edit_message(embed=embed, view=view)

    async def _handle_drink_button(self, interaction: discord.Interaction, guild: discord.Guild):
        """Handle drink water button click."""
        player = await PlayerProfile.get(interaction.user.id)
        server_state = await ServerState.get(interaction.guild_id)
        
        # Water drinking effects handled by game manager
        await player.save()
        
        view = self.get_view_for_player(player, server_state, force_new=True)
        embed = await self.generate_dashboard_embed(player, server_state, guild)
        await interaction.response.edit_message(embed=embed, view=view)

def setup(bot):
    """Add the cog to the bot."""
    bot.add_cog(MainEmbed(bot))