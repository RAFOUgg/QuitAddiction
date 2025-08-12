# --- cogs/main_embed.py (Refactored for Visual Dashboard) ---

import discord
from discord.ext import commands
from discord import ui
from db.database import SessionLocal
from db.models import ServerState, PlayerProfile, ActionLog
import datetime
import random

# --- Helper function for creating progress bars ---
def generate_progress_bar(value: float, max_value: float = 100.0, length: int = 10) -> str:
    """Generates a text-based progress bar."""
    if value < 0: value = 0
    if value > max_value: value = max_value
    
    percent = value / max_value
    filled_length = int(length * percent)
    
    # You can customize these emojis
    bar_filled = '🟩'
    bar_empty = '⬛'
    
    bar = bar_filled * filled_length + bar_empty * (length - filled_length)
    return f"`{bar}`"

class MainEmbed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ----------------------------------------
    # --- 1. THE MAIN DASHBOARD GENERATION ---
    # ----------------------------------------

    def generate_menu_embed(self, state: ServerState) -> discord.Embed:
        """
        Generates the main visual dashboard embed, inspired by the screenshot.
        """
        embed = discord.Embed(
            title="👨‍🍳 Le Quotidien du Cuisinier",
            color=0x3498db # A nice blue color
        )
        
        # Determine the character's overall status for the description and image
        status_description = "Il a l'air de bien se porter."
        image_url = "https://img.freepik.com/vecteurs-premium/chef-cuisinier-donnant-pouce-air-isole-blanc_1639-44043.jpg" # Happy chef
        
        if state.stress > 70 or state.food < 30 or state.water < 30:
            status_description = "Il a l'air fatigué et stressé... Il a besoin d'aide."
            image_url = "https://img.freepik.com/vecteurs-premium/chef-triste-pleurant-isole_1639-22687.jpg" # Sad chef
            embed.color = 0xe74c3c # Red color for danger

        embed.description = f"*Dernière mise à jour : <t:{int(datetime.datetime.now().timestamp())}:R>*\n{status_description}"

        # --- Visual Stats with Progress Bars ---
        stats_text = (
            f"**❤️ Santé:** {generate_progress_bar(state.phys)} `({state.phys:.0f}%)`\n"
            f"**🧠 Mental:** {generate_progress_bar(state.ment)} `({state.ment:.0f}%)`\n"
            f"**😊 Humeur:** {generate_progress_bar(state.happy)} `({state.happy:.0f}%)`\n"
            f"**🍔 Faim:** {generate_progress_bar(100 - state.food)} `({100 - state.food:.0f}%)`\n"
            f"**💧 Soif:** {generate_progress_bar(100 - state.water)} `({100 - state.water:.0f}%)`\n"
            f"**😨 Stress:** {generate_progress_bar(state.stress)} `({state.stress:.0f}%)`\n"
            f"**☠️ Toxines:** {generate_progress_bar(state.tox)} `({state.tox:.0f}%)`"
        )
        embed.add_field(name="--- Statistiques Vitales ---", value=stats_text, inline=False)
        
        # --- Secondary Stats ---
        addiction_text = (
            f"**🚬 Addiction:** {generate_progress_bar(state.addiction)} `({state.addiction:.1f}%)`\n"
            f"**💰 Portefeuille:** `{state.wallet} $`"
        )
        embed.add_field(name="--- État Secondaire ---", value=addiction_text, inline=False)
        
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3423/3423485.png") # A fixed icon for the chef
        embed.set_image(url=image_url) # The main image that can change
        embed.set_footer(text="Interagissez avec les boutons ci-dessous.")

        return embed

    def generate_main_menu(self, guild_id: str) -> discord.ui.View:
        """
        Generates the main view with primary and secondary action buttons.
        """
        view = discord.ui.View(timeout=None)
        
        # Primary actions, directly impacting core needs
        view.add_item(DashboardActionButton("🍽️ Manger", "action_eat", discord.ButtonStyle.success, row=0))
        view.add_item(DashboardActionButton("💧 Boire", "action_drink", discord.ButtonStyle.primary, row=0))
        view.add_item(DashboardActionButton("🛏️ Dormir", "action_sleep", discord.ButtonStyle.secondary, row=0))
        view.add_item(DashboardActionButton("🚬 Fumer", "action_smoke", discord.ButtonStyle.danger, row=0))
        
        # Secondary actions, leading to other functions
        view.add_item(DashboardActionButton("🏪 Boutique", "nav_shop", discord.ButtonStyle.blurple, row=1))
        view.add_item(DashboardActionButton("📦 Inventaire", "nav_inventory", discord.ButtonStyle.blurple, row=1))
        view.add_item(DashboardActionButton("📱 Téléphone", "nav_phone", discord.ButtonStyle.blurple, row=1))

        return view
        
# -------------------------------------
# --- 2. THE DYNAMIC DASHBOARD BUTTON ---
# -------------------------------------
# This single button class handles all actions and navigation.

class DashboardActionButton(discord.ui.Button):
    def __init__(self, label: str, custom_id: str, style: discord.ButtonStyle, row: int):
        super().__init__(label=label, style=style, custom_id=custom_id, row=row)

    async def callback(self, interaction: discord.Interaction):
        # We need the cog to access its methods like generate_menu_embed
        cog = interaction.client.get_cog("MainEmbed")
        if not cog:
            return await interaction.response.send_message("Erreur: Cog non trouvé.", ephemeral=True)

        # Defer the interaction immediately
        await interaction.response.defer()

        db = SessionLocal()
        try:
            state = db.query(ServerState).filter_by(guild_id=str(interaction.guild.id)).first()
            if not state:
                return await interaction.followup.send("Erreur: état du serveur introuvable.", ephemeral=True)
            
            # --- ACTION LOGIC ---
            message = ""
            if self.custom_id == "action_eat":
                state.food = max(0.0, state.food - 30.0) # Eating reduces hunger
                state.happy = min(100.0, state.happy + 5.0)
                message = "Vous avez mangé. Votre faim est apaisée."
            
            elif self.custom_id == "action_drink":
                state.water = max(0.0, state.water - 40.0) # Drinking reduces thirst
                message = "Vous avez bu de l'eau. Vous vous sentez hydraté."
            
            elif self.custom_id == "action_sleep":
                state.phys = min(100.0, state.phys + 50.0) # Sleeping restores physical health
                state.stress = max(0.0, state.stress - 30.0)
                message = "Une bonne nuit de sommeil ! Vous vous sentez reposé."
            
            elif self.custom_id == "action_smoke":
                state.stress = max(0.0, state.stress - 15.0)
                state.happy = min(100.0, state.happy + 10.0)
                state.tox = min(100.0, state.tox + 5.0)
                state.addiction = min(100.0, state.addiction + 2.0)
                message = "Une cigarette pour décompresser... mais à quel prix ?"

            # --- NAVIGATION LOGIC ---
            # (This part can be expanded with dedicated views for shop, etc.)
            elif self.custom_id == "nav_shop":
                # For now, just a message. Can be replaced with a real shop view.
                await interaction.followup.send("La boutique est en cours de développement !", ephemeral=True)
                return # Return here as we are not updating the dashboard
            
            # If any action was taken, commit the changes and refresh the dashboard
            if message:
                db.commit()
                db.refresh(state)
                
                # Generate the new embed and view with updated data
                new_embed = cog.generate_menu_embed(state)
                new_view = cog.generate_main_menu(str(interaction.guild.id))
                
                # Edit the original message
                await interaction.edit_original_response(embed=new_embed, view=new_view)
                
                # Send a small, ephemeral confirmation message
                await interaction.followup.send(f"✅ {message}", ephemeral=True)
            else:
                # If no action was matched, just acknowledge to avoid an error.
                # This case shouldn't be hit with the current buttons.
                 await interaction.followup.send("Action non reconnue.", ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"Une erreur est survenue: {e}", ephemeral=True)
            db.rollback()
        finally:
            db.close()

async def setup(bot):
    await bot.add_cog(MainEmbed(bot))