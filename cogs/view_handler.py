# --- cogs/view_handler.py ---
from typing import Tuple, Optional
import discord
from discord.ext import commands
from discord.ext.commands import Cog
from db.models import PlayerProfile, ServerState
from db.database import SessionLocal
from utils.game_manager import game_manager
from utils.view_manager import view_manager
from utils.error_handler import handle_interaction_error, check_valid_state, GameError
from utils.logger import get_logger

logger = get_logger(__name__)

class ViewHandler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._db_session = SessionLocal()
        
    def create_view(self, view_type: str, player: PlayerProfile, state: ServerState) -> discord.ui.View:
        """Create the appropriate view based on type"""
        from cogs.main_embed import DashboardView, ActionsView
        from cogs.phone import PhoneMainView
        
        if view_type == "main_menu":
            return DashboardView(player)
        elif view_type == "actions":
            return ActionsView(player, state)
        elif view_type == "phone":
            return PhoneMainView(player)
        elif view_type == "stats":
            view = DashboardView(player, show_stats=True)
            return view
        elif view_type == "inventory":
            view = DashboardView(player, show_inventory=True)
            return view
        else:
            return DashboardView(player)
            
    def create_embed(self, player: PlayerProfile, state: ServerState, guild: Optional[discord.Guild]) -> discord.Embed:
        """Create the appropriate embed for the current view"""
        if not guild:
            return discord.Embed(
                title="Erreur",
                description="Impossible de créer l'affichage - Serveur non trouvé",
                color=discord.Color.red()
            )

        # Get the GameEmbed cog to use its embed generation
        game_embed_cog = self.bot.get_cog("GameEmbed")
        if not game_embed_cog:
            # Fallback basic embed if cog not found
            embed = discord.Embed(
                title="Tableau de bord",
                description="Erreur: GameEmbed cog non trouvé",
                color=discord.Color.red()
            )
            return embed
            
        if hasattr(game_embed_cog, 'generate_dashboard_embed'):
            return game_embed_cog.generate_dashboard_embed(player, state, guild)
            
        # Fallback simple embed if no generate method
        embed = discord.Embed(
            title="État du joueur",
            description=f"Points de vie: {getattr(player, 'health', 0)}/100\nÉnergie: {getattr(player, 'energy', 0)}/100",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Serveur: {guild.name}")
        return embed
        
    def process_button_action(self, interaction: discord.Interaction, player: PlayerProfile, state: ServerState, custom_id: str) -> Tuple[discord.ui.View, discord.Embed]:
        """Process a button action and return the appropriate view and embed"""
        if not interaction.guild:
            return self._create_view("main_menu", player, state), discord.Embed(
                title="Erreur", 
                description="Serveur non trouvé",
                color=discord.Color.red()
            )

        try:
            view_type = "main_menu"  # Default view type
            
            if custom_id == "stats":
                view_type = "stats"
            elif custom_id == "inventory":
                view_type = "inventory"
            elif custom_id == "sleep":
                player.is_sleeping = True
                self._db_session.commit()
            elif custom_id == "work":
                player.is_working = True
                self._db_session.commit()
            elif custom_id == "phone":
                view_type = "phone"
                
            view = self._create_view(view_type, player, state)
            embed = self._create_embed(player, state, interaction.guild)

        except Exception as e:
            logger.error(f"Error processing button action: {e}")
            return self._create_view("main_menu", player, state), discord.Embed(
                title="Erreur",
                description="Une erreur est survenue lors du traitement de l'action.",
                color=discord.Color.red()
            )

        return view, embed

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Handle all button interactions"""
        if not interaction.data or not interaction.guild:
            return
            
        custom_id = interaction.data.get('custom_id')
        if not custom_id:
            return

        try:
            # Get the player and server state from the database
            guild_id = str(interaction.guild.id)
            
            state = self._db_session.query(ServerState).filter(
                ServerState.guild_id == guild_id
            ).first()
            
            player = self._db_session.query(PlayerProfile).filter(
                PlayerProfile.guild_id == guild_id
            ).first()
            
            if not state or not player:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "Erreur: Profil de jeu introuvable. Utilisez /start pour commencer.",
                        ephemeral=True
                    )
                return

            # Process the button action
            view, embed = self.process_button_action(interaction, player, state, custom_id)
            
            if not view or not embed:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "Une erreur est survenue lors du traitement de l'action.",
                        ephemeral=True
                    )
                return

            # Handle navigation based on custom_id
            view_type = "main_menu"  # Default view type
            if custom_id.startswith("nav_"):
                nav_type = custom_id[4:]  # Remove "nav_" prefix
                if nav_type == "back":
                    previous_view = view_manager.go_back(guild_id)
                    if previous_view:
                        view = self._create_view(previous_view, player, state)
                        view_manager.register_view(guild_id, view, previous_view)
                else:
                    view = self._create_view(nav_type, player, state)
                    view_manager.register_view(guild_id, view, nav_type)
                view_type = nav_type

            # Validate state for action-based interactions
            if custom_id.startswith("action_"):
                check_valid_state(player, custom_id[7:])  # Remove "action_" prefix

            # Update the message
            try:
                if isinstance(interaction.channel, (discord.TextChannel, discord.Thread)):
                    if not interaction.response.is_done():
                        await interaction.response.edit_message(view=view, embed=embed)
                    elif interaction.message:
                        await interaction.message.edit(view=view, embed=embed)
                    else:
                        await interaction.channel.send(embed=embed, view=view)
                else:
                    logger.error(f"Invalid channel type for interaction: {type(interaction.channel)}")
                    if not interaction.response.is_done():
                        await interaction.response.send_message(
                            "Cette commande ne peut être utilisée que dans un canal de texte.",
                            ephemeral=True
                        )

                # Register the current view
                view_manager.register_view(guild_id, view, view_type)

            except discord.errors.NotFound:
                logger.warning("Message not found, might have been deleted")
            except Exception as e:
                logger.error(f"Error updating message: {e}", exc_info=True)
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "Une erreur est survenue lors de la mise à jour du message.",
                        ephemeral=True
                    )
            
        except Exception as e:
            logger.error(f"Error in interaction handler: {e}", exc_info=True)
            await handle_interaction_error(interaction, e)
            self._db_session.rollback()
            
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
        from cogs.main_embed import GameEmbed
        
        cog = self.bot.get_cog("GameEmbed")
        if not isinstance(cog, GameEmbed):
            return discord.Embed(
                title="Erreur",
                description="Le module GameEmbed n'a pas été trouvé.",
                color=discord.Color.red()
            )

        try:
            return cog.generate_dashboard_embed(player=player, state=state, guild=guild)
        except Exception as e:
            logger.error(f"Error generating dashboard embed: {e}")
            return discord.Embed(
                title="Erreur",
                description="Une erreur est survenue lors de la génération de l'affichage.",
                color=discord.Color.red()
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(ViewHandler(bot))
