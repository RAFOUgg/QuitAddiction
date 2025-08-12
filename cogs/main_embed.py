# --- cogs/main_embed.py (Refactored for Interactive Navigation) ---

import discord
from discord.ext import commands
from discord import ui
from db.database import SessionLocal
from db.models import ServerState
import datetime

# --- On importe les vues des autres modules pour les utiliser ici ---
from .phone import PhoneMainView 

# --- Helper function for creating progress bars (no changes) ---
def generate_progress_bar(value: float, max_value: float = 100.0, length: int = 10) -> str:
    """Generates a text-based progress bar."""
    if value < 0: value = 0
    if value > max_value: value = max_value
    percent = value / max_value
    filled_length = int(length * percent)
    bar_filled = '🟩'
    bar_empty = '⬛'
    bar = bar_filled * filled_length + bar_empty * (length - filled_length)
    return f"`{bar}`"

# ---------------------------------------------------
# --- SECTION 1: DÉFINITION DES VUES (BOUTONS) ---
# ---------------------------------------------------

class MainMenuView(ui.View):
    """La vue principale avec les 3 boutons de navigation."""
    def __init__(self):
        super().__init__(timeout=None)
        # custom_id commence par "nav_" pour la navigation
        self.add_item(ui.Button(label="🧠 Cerveau", style=discord.ButtonStyle.secondary, custom_id="nav_stats", row=0))
        self.add_item(ui.Button(label="🏃‍♂️ Actions", style=discord.ButtonStyle.primary, custom_id="nav_actions", row=0))
        self.add_item(ui.Button(label="📱 Téléphone", style=discord.ButtonStyle.blurple, custom_id="nav_phone", row=0))

class ActionsView(ui.View):
    """La vue pour les actions du joueur (manger, boire, etc.)."""
    def __init__(self):
        super().__init__(timeout=None)
        # custom_id commence par "action_" pour une action directe
        self.add_item(ui.Button(label="🍽️ Manger", style=discord.ButtonStyle.success, custom_id="action_eat", row=0))
        self.add_item(ui.Button(label="💧 Boire", style=discord.ButtonStyle.primary, custom_id="action_drink", row=0))
        self.add_item(ui.Button(label="🛏️ Dormir", style=discord.ButtonStyle.secondary, custom_id="action_sleep", row=0))
        self.add_item(ui.Button(label="🚬 Fumer", style=discord.ButtonStyle.danger, custom_id="action_smoke", row=0))
        # Le bouton de retour
        self.add_item(ui.Button(label="⬅️ Retour", style=discord.ButtonStyle.grey, custom_id="nav_main_menu", row=1))

class BackView(ui.View):
    """Une vue simple avec seulement un bouton Retour."""
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ui.Button(label="⬅️ Retour", style=discord.ButtonStyle.grey, custom_id="nav_main_menu"))


# -----------------------------------------
# --- SECTION 2: LE COG PRINCIPAL ---
# -----------------------------------------

class MainEmbed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # On s'assure que les vues persistantes sont ajoutées au redémarrage du bot
        bot.add_view(MainMenuView())
        bot.add_view(ActionsView())
        bot.add_view(BackView())
        # La vue du téléphone est gérée dans son propre cog
        bot.add_view(PhoneMainView())

    # --- Fonctions pour générer les embeds ---

    def get_base_embed(self, state: ServerState, interaction: discord.Interaction) -> discord.Embed:
        """Crée l'embed de base avec le titre et le thumbnail."""
        embed = discord.Embed(
            title="👨‍🍳 Le Quotidien du Cuisinier",
            color=0x3498db
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3423/3423485.png")
        embed.set_footer(text=f"Jeu sur le serveur {interaction.guild.name}")
        return embed

    def generate_main_embed(self, state: ServerState, interaction: discord.Interaction) -> discord.Embed:
        """Génère l'embed de l'écran d'accueil."""
        embed = self.get_base_embed(state, interaction)
        
        status_description = "Il a l'air de bien se porter."
        image_url = "https://img.freepik.com/vecteurs-premium/chef-cuisinier-donnant-pouce-air-isole-blanc_1639-44043.jpg"
        
        if state.stress > 70 or state.food < 30 or state.water < 30:
            status_description = "Il a l'air fatigué et stressé... Il a besoin d'aide."
            image_url = "https://img.freepik.com/vecteurs-premium/chef-triste-pleurant-isole_1639-22687.jpg"
            embed.color = 0xe74c3c

        embed.description = f"*Dernière mise à jour : <t:{int(datetime.datetime.now().timestamp())}:R>*\n{status_description}"
        embed.set_image(url=image_url)
        return embed

    def generate_stats_embed(self, state: ServerState, interaction: discord.Interaction) -> discord.Embed:
        """Génère l'embed détaillé des statistiques (l'écran 'Cerveau')."""
        embed = self.get_base_embed(state, interaction)
        embed.description = "Aperçu de l'état de santé physique et mental du cuisinier."
        
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
        
        addiction_text = (
            f"**🚬 Addiction:** {generate_progress_bar(state.addiction)} `({state.addiction:.1f}%)`\n"
            f"**💰 Portefeuille:** `{state.wallet} $`"
        )
        embed.add_field(name="--- État Secondaire ---", value=addiction_text, inline=False)
        embed.set_image(url="https://i.imgur.com/QpjO1aN.png") # Image "cerveau"
        return embed

    # --- Le Listener qui gère TOUS les clics de l'interface principale ---
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.data or "custom_id" not in interaction.data:
            return

        custom_id = interaction.data["custom_id"]
        
        # Ce listener ne gère que les ID commençant par "nav_" ou "action_"
        if not (custom_id.startswith("nav_") or custom_id.startswith("action_")):
            return

        await interaction.response.defer()
        db = SessionLocal()
        try:
            state = db.query(ServerState).filter_by(guild_id=str(interaction.guild.id)).first()
            if not state:
                return await interaction.followup.send("Erreur: état du serveur introuvable.", ephemeral=True)

            # --- LOGIQUE DE NAVIGATION ---
            if custom_id == "nav_main_menu":
                embed = self.generate_main_embed(state, interaction)
                await interaction.edit_original_response(embed=embed, view=MainMenuView())
            
            elif custom_id == "nav_stats":
                embed = self.generate_stats_embed(state, interaction)
                await interaction.edit_original_response(embed=embed, view=BackView())

            elif custom_id == "nav_actions":
                embed = self.generate_main_embed(state, interaction) # On affiche l'embed principal avec les boutons d'action
                await interaction.edit_original_response(embed=embed, view=ActionsView())
            
            elif custom_id == "nav_phone":
                embed = self.get_base_embed(state, interaction)
                embed.description = "Vous ouvrez votre téléphone."
                embed.set_image(url="https://i.imgur.com/7aD4k6A.png") # Image de téléphone
                await interaction.edit_original_response(embed=embed, view=PhoneMainView())

            # --- LOGIQUE D'ACTION ---
            message = ""
            action_taken = False
            if custom_id.startswith("action_"):
                action_taken = True
                if custom_id == "action_eat":
                    state.food = max(0.0, state.food - 30.0)
                    state.happy = min(100.0, state.happy + 5.0)
                    message = "Vous avez mangé. Votre faim est apaisée."
                elif custom_id == "action_drink":
                    state.water = max(0.0, state.water - 40.0)
                    message = "Vous avez bu. Vous vous sentez hydraté."
                elif custom_id == "action_sleep":
                    state.phys = min(100.0, state.phys + 50.0)
                    state.stress = max(0.0, state.stress - 30.0)
                    message = "Une bonne nuit de sommeil ! Vous vous sentez reposé."
                elif custom_id == "action_smoke":
                    state.stress = max(0.0, state.stress - 15.0)
                    state.happy = min(100.0, state.happy + 10.0)
                    state.tox = min(100.0, state.tox + 5.0)
                    state.addiction = min(100.0, state.addiction + 2.0)
                    message = "Une cigarette pour décompresser... mais à quel prix ?"

            # Si une action a été effectuée, on met à jour la BDD et on rafraîchit l'affichage
            if action_taken:
                db.commit()
                db.refresh(state)
                # On réaffiche l'écran d'action avec l'embed principal mis à jour
                new_embed = self.generate_main_embed(state, interaction)
                await interaction.edit_original_response(embed=new_embed, view=ActionsView())
                await interaction.followup.send(f"✅ {message}", ephemeral=True)

        except Exception as e:
            print(f"Erreur dans le listener d'interaction: {e}")
            await interaction.followup.send(f"Une erreur est survenue: {e}", ephemeral=True)
            db.rollback()
        finally:
            db.close()

async def setup(bot):
    await bot.add_cog(MainEmbed(bot))