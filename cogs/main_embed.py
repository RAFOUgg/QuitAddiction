# --- cogs/main_embed.py (REVISED) ---
import discord
from discord.ext import commands
from discord import ui
from db.database import SessionLocal
from db.models import ServerState, PlayerProfile
import datetime
import traceback
import asyncio
from .phone import PhoneMainView, Phone
from .brain_stats import BrainStatsView
from utils.helpers import clamp
from utils.logger import get_logger
from utils.time_manager import get_current_game_time, is_night, is_work_time, is_lunch_break, to_localized, get_utc_now
logger = get_logger(__name__)

# Configuration des durées d'actions (en secondes)
ACTION_DURATIONS = {
    # Actions de base
    "default": 10,            
    
    # Actions de repas
    "eat_sandwich": 180,      
    "eat_tacos": 240,        
    "eat_salad": 300,        
    
    # Actions de boisson
    "drink_water": 10,       
    "drink_soda": 20,        
    "drink_wine": 120,       
    
    # Actions de consommation de substances
    "smoke_cigarette": 240,   
    "smoke_cigarette_work": 240,  
    "smoke_ecigarette": 180,  
    "smoke_joint": 600,      
    "smoke_joint_work": 600,  
    "use_bong": 180,        
    
    # Actions physiologiques
    "sleep": {               
        "min": 6 * 3600,     
        "max": 10 * 3600,    
        "nap": 1800,         
    },
    "shower": 600,          
    "urinate": 120,         
    "defecate": 300,        
    
    # Actions de travail
    "work": {               
        "morning": 2.5 * 3600,   
        "afternoon": 4.5 * 3600, 
    },
    "work_break": {         
        "normal": 900,       
        "lunch": 5400,       
    },
    
    # Autres activités
    "sport": 3600,          
    "phone": 300,           
}

class DashboardView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=None)
        now = datetime.datetime.utcnow()
        is_on_cooldown = player.action_cooldown_end_time and now < player.action_cooldown_end_time
        # Le téléphone est désactivé au travail, sauf pendant une pause
        phone_disabled = is_on_cooldown or (player.is_working and not getattr(player, 'is_on_break', False))
        
        self.add_item(ui.Button(label="Actions", style=discord.ButtonStyle.primary, custom_id="nav_actions", emoji="🏃‍♂️", disabled=is_on_cooldown))
        self.add_item(ui.Button(label="Téléphone", style=discord.ButtonStyle.blurple, custom_id="phone_open", emoji="📱", disabled=phone_disabled))
        self.add_item(ui.Button(label="Travail", style=discord.ButtonStyle.secondary, custom_id="nav_work", emoji="🏢"))
        
        inv_label = "Cacher Inventaire" if player.show_inventory_in_view else "Afficher Inventaire"
        inv_style = discord.ButtonStyle.success if player.show_inventory_in_view else discord.ButtonStyle.secondary
        self.add_item(ui.Button(label=inv_label, style=inv_style, custom_id="nav_toggle_inventory", emoji="🎒", row=1))
        
        stats_label = "Cacher Cerveau" if player.show_stats_in_view else "Afficher Cerveau"
        stats_style = discord.ButtonStyle.success if player.show_stats_in_view else discord.ButtonStyle.secondary
        self.add_item(ui.Button(label=stats_label, style=stats_style, custom_id="nav_toggle_stats", row=1, emoji="🧠"))

class MainEmbed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.data or "custom_id" not in interaction.data: return
        db = SessionLocal()
        try:
            if interaction.message is None: return
            state = db.query(ServerState).filter_by(guild_id=str(interaction.guild.id)).first()
            if not state or not state.game_message_id or interaction.message.id != state.game_message_id: return
            player = db.query(PlayerProfile).filter_by(guild_id=str(interaction.guild.id)).first()
            if not player: 
                if not interaction.response.is_done(): await interaction.response.send_message("Erreur: Profil de joueur introuvable.", ephemeral=True)
                return

            custom_id = interaction.data["custom_id"]
            game_time = get_current_game_time(state)

            # Vérifier si c'est le début d'une nouvelle partie pendant la nuit
            if custom_id == "start_game" and is_night(game_time):
                player.is_sleeping = True
                player.current_state = "sleep"
                db.commit()
                await interaction.followup.send("💤 Le cuisinier dort profondément...", ephemeral=True)
                return

            # Gestion du téléphone
            if custom_id.startswith("phone_"):
                phone_cog = self.bot.get_cog("Phone")
                player.last_action = "phone_open"  # Pour l'affichage de l'image on_phone.png
                await phone_cog.handle_interaction(interaction, db, player, state, self)
                return

            if not interaction.response.is_done(): await interaction.response.defer()

            # Gestion des boutons du cerveau
            if custom_id.startswith("brain_"):
                brain_view = BrainStatsView(player)
                if custom_id == "brain_back":
                    player.show_stats_in_view = False
                    view = DashboardView(player)
                else:
                    brain_view.current_section = custom_id.replace("brain_", "")
                    view = brain_view
                embed = self.generate_dashboard_embed(player, state, interaction.guild)
                await interaction.edit_original_response(embed=embed, view=view)
                db.commit()
                return

            # ... reste du code existant

        except Exception as e:
            logger.error(f"Erreur critique dans on_interaction: {e}", exc_info=True)
            if not interaction.response.is_done():
                try: await interaction.followup.send("Une erreur est survenue.", ephemeral=True)
                except: pass
            db.rollback()
        finally:
            if db.is_active: db.close()

    def generate_dashboard_embed(self, player: PlayerProfile, state: ServerState, guild: discord.Guild) -> discord.Embed:
        game_time = get_current_game_time(state)

        title = "🧑‍🍳 Le Cuisinier"
        if player.is_working:
            title += " - Au Travail 🏢"
            if player.is_on_break:
                title += " (En Pause ☕)"
        elif player.is_sleeping:
            title += " - Endormi 💤"
        elif player.last_action == "phone_open":
            title += " - Au Téléphone 📱"

        embed = discord.Embed(title=title, color=0x3498db)

        # Stats view
        if getattr(player, 'show_stats_in_view', False):
            brain_view = BrainStatsView(player)
            fields = brain_view.get_stats_fields()
            for field in fields:
                embed.add_field(name=field["name"], value=field["value"], inline=True)

        # ... reste du code existant

    def get_image_url(self, player: PlayerProfile) -> str:
        """Get the appropriate image URL based on player state."""
        asset_cog = self.bot.get_cog("AssetsManager")
        if not asset_cog: return ""

        # Priorité à l'état téléphone si actif
        if player.last_action == "phone_open":
            return asset_cog.get_url("on_phone") or asset_cog.get_url("neutral")

        if player.current_state:
            return asset_cog.get_url(player.current_state) or asset_cog.get_url("neutral")

        return asset_cog.get_url("neutral")
