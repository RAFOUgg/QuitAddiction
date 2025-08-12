import discord
from discord.ext import commands
from discord import ui
from db.database import SessionLocal
import datetime
from .phone import PhoneMainView 
from db.models import ServerState, PlayerProfile

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

# --- Helper function pour le temps (à mettre dans utils/helpers.py) ---
def format_time_delta(td: datetime.timedelta) -> str:
    seconds = int(td.total_seconds())
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    return f"{hours}h"

# ---------------------------------------------------
# --- SECTION 1: DÉFINITION DES VUES (BOUTONS) ---
# ---------------------------------------------------

class ActionsView(ui.View):
    def __init__(self, player: PlayerProfile, server_state: ServerState):
        super().__init__(timeout=None)
        now = datetime.datetime.utcnow()

        # --- Bouton Manger ---
        if player.last_eaten_at:
            label = f"Manger (il y a {format_time_delta(now - player.last_eaten_at)})"
        else:
            label = "Manger"
        self.add_item(ui.Button(label=label, style=discord.ButtonStyle.success, custom_id="action_eat", emoji="🍽️"))

        # --- Bouton Boire ---
        if player.last_drank_at:
            label = f"Boire (il y a {format_time_delta(now - player.last_drank_at)})"
        else:
            label = "Boire"
        self.add_item(ui.Button(label=label, style=discord.ButtonStyle.primary, custom_id="action_drink", emoji="💧"))

        # --- Bouton Dormir ---
        if player.last_slept_at:
            label = f"Dormir (il y a {format_time_delta(now - player.last_slept_at)})"
        else:
            label = "Dormir"
        self.add_item(ui.Button(label=label, style=discord.ButtonStyle.secondary, custom_id="action_sleep", emoji="🛏️"))

        # --- Bouton Fumer (prédictif pour le manque) ---
        time_to_craving = (20 - player.withdrawal_severity) * 5 # estimation en minutes
        if player.withdrawal_severity > 5:
            label = f"Fumer (Manque dans ~{int(time_to_craving)}m)"
            style = discord.ButtonStyle.danger
        else:
            label = "Fumer"
            style = discord.ButtonStyle.secondary
        self.add_item(ui.Button(label=label, style=style, custom_id="action_smoke", emoji="🚬"))
        
        # --- Bouton Uriner ---
        if player.bladder > 30:
            label = f"Uriner ({player.bladder:.0f}%)"
            style = discord.ButtonStyle.danger if player.bladder > 80 else discord.ButtonStyle.blurple
            self.add_item(ui.Button(label=label, style=style, custom_id="action_urinate", emoji="🚽", row=1))

        # --- Bouton Retour ---
        self.add_item(ui.Button(label="⬅️ Retour au menu", style=discord.ButtonStyle.grey, custom_id="nav_main_menu", row=2))

class MainMenuView(ui.View):
    """La vue principale avec les 3 boutons de navigation."""
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ui.Button(label="🧠 Cerveau", style=discord.ButtonStyle.secondary, custom_id="nav_stats", row=0))
        self.add_item(ui.Button(label="🏃‍♂️ Actions", style=discord.ButtonStyle.primary, custom_id="nav_actions", row=0))
        self.add_item(ui.Button(label="📱 Téléphone", style=discord.ButtonStyle.blurple, custom_id="nav_phone", row=0))

class ActionsView(ui.View):
    """La vue pour les actions du joueur (manger, boire, etc.)."""
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ui.Button(label="🍽️ Manger", style=discord.ButtonStyle.success, custom_id="action_eat", row=0))
        self.add_item(ui.Button(label="💧 Boire", style=discord.ButtonStyle.primary, custom_id="action_drink", row=0))
        self.add_item(ui.Button(label="🛏️ Dormir", style=discord.ButtonStyle.secondary, custom_id="action_sleep", row=0))
        self.add_item(ui.Button(label="🚬 Fumer", style=discord.ButtonStyle.danger, custom_id="action_smoke", row=0))
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
        bot.add_view(MainMenuView())
        bot.add_view(ActionsView())
        bot.add_view(BackView())
        bot.add_view(PhoneMainView())

    # --- Fonctions pour générer les embeds ---

    def get_base_embed(self, player_profile: PlayerProfile, guild: discord.Guild) -> discord.Embed:
        """Crée l'embed de base avec titre, thumbnail, et l'image dynamique du cuisinier."""
        embed = discord.Embed(
            title="👨‍🍳 Le Quotidien du Cuisinier",
            color=0x3498db
        )
        
        asset_cog = self.bot.get_cog("AssetManager")
        image_name = "happy"
        
        # On se base sur le profil du joueur, pas l'état global du serveur
        if player_profile.stress > 70 or player_profile.hunger > 70 or player_profile.thirst > 70:
            image_name = "sad"
            embed.color = 0xe74c3c
        
        image_url = asset_cog.get_url(image_name) if asset_cog else None

        if image_url:
            embed.set_image(url=image_url)
        else:
            embed.add_field(name="⚠️ Erreur d'affichage", value=f"L'image '{image_name}.png' n'a pas pu être chargée.")
            
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3423/3423485.png")
        embed.set_footer(text=f"Jeu sur le serveur {guild.name}")
        return embed

    # MODIFICATION: On passe 'guild'
    def generate_main_embed(self, player_profile: PlayerProfile, guild: discord.Guild) -> discord.Embed:
        """Génère l'embed de l'écran d'accueil."""
        embed = self.get_base_embed(player_profile, guild)
        
        status_description = "Il a l'air de bien se porter."
        if player_profile.stress > 70 or player_profile.hunger > 70 or player_profile.thirst > 70:
            status_description = "Il a l'air fatigué et stressé... Il a besoin d'aide."

        embed.description = f"*Dernière mise à jour : <t:{int(datetime.datetime.now().timestamp())}:R>*\n{status_description}"
        return embed

    # MODIFICATION: On passe 'guild'
    def generate_stats_embed(self, player: PlayerProfile, guild: discord.Guild) -> discord.Embed:
        """Génère l'embed détaillé et réorganisé des statistiques."""
        embed = self.get_base_embed(player, guild)
        embed.description = "Aperçu de l'état de santé physique et mental du cuisinier."
        
        # --- SECTION 1: SANTÉ PHYSIQUE ---
        phys_health = (
            f"**Santé:** {generate_progress_bar(player.health)} `{player.health:.0f}%`\n"
            f"**Énergie:** {generate_progress_bar(player.energy)} `{player.energy:.0f}%`\n"
            f"**Fatigue:** {generate_progress_bar(player.fatigue)} `{player.fatigue:.0f}%`\n"
            f"**Toxines:** {generate_progress_bar(player.tox)} `{player.tox:.0f}%`"
        )
        embed.add_field(name="❤️ Santé Physique", value=phys_health, inline=True)

        # --- SECTION 2: ÉTAT MENTAL & ÉMOTIONNEL ---
        mental_health = (
            f"**Mentale:** {generate_progress_bar(player.sanity)} `{player.sanity:.0f}%`\n"
            f"**Stress:** {generate_progress_bar(player.stress)} `{player.stress:.0f}%`\n"
            f"**Humeur:** {generate_progress_bar(player.happiness)} `{player.happiness:.0f}%`\n"
            f"**Ennui:** {generate_progress_bar(player.boredom)} `{player.boredom:.0f}%`"
        )
        embed.add_field(name="🧠 État Mental", value=mental_health, inline=True)
        
        # Saut de ligne pour l'esthétique
        embed.add_field(name="\u200b", value="\u200b", inline=False) 

        # --- SECTION 3: SYMPTÔMES & MALAISE ---
        symptoms = (
            f"**Douleur:** {generate_progress_bar(player.pain)} `{player.pain:.0f}%`\n"
            f"**Nausée:** {generate_progress_bar(player.nausea)} `{player.nausea:.0f}%`\n"
            f"**Vertiges:** {generate_progress_bar(player.dizziness)} `{player.dizziness:.0f}%`\n"
            f"**Mal de Tête:** {generate_progress_bar(player.headache)} `{player.headache:.0f}%`\n"
            f"**Gorge Irritée:** {generate_progress_bar(player.sore_throat)} `{player.sore_throat:.0f}%`\n"
            f"**Bouche Sèche:** {generate_progress_bar(player.dry_mouth)} `{player.dry_mouth:.0f}%`"
        )
        embed.add_field(name="🤕 Symptômes", value=symptoms, inline=True)
        
        # --- SECTION 4: ADDICTION & DÉPENDANCE ---
        addiction = (
            f"**Dépendance:** {generate_progress_bar(player.substance_addiction_level)} `{player.substance_addiction_level:.0f}%`\n"
            f"**Manque:** {generate_progress_bar(player.withdrawal_severity)} `{player.withdrawal_severity:.0f}%`\n"
            f"**Défonce:** {generate_progress_bar(player.intoxication_level)} `{player.intoxication_level:.0f}%`"
        )
        embed.add_field(name="🚬 Addiction", value=addiction, inline=True)
        
        return embed

    # --- Le Listener qui gère TOUS les clics de l'interface principale ---
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.data or "custom_id" not in interaction.data:
            return

        custom_id = interaction.data["custom_id"]
        
        if not (custom_id.startswith("nav_") or custom_id.startswith("action_")):
            return

        await interaction.response.defer()
        db = SessionLocal()
        try:
            # ON RÉCUPÈRE LE PROFIL DU JOUEUR, PAS L'ÉTAT DU SERVEUR
            player = db.query(PlayerProfile).filter_by(guild_id=str(interaction.guild.id)).first()
            if not player:
                return await interaction.followup.send("Erreur: Profil du cuisinier introuvable.", ephemeral=True)

            cooker_brain = self.bot.get_cog("CookerBrain")
            if not cooker_brain:
                return await interaction.followup.send("Erreur critique: Le moteur de jeu est introuvable.", ephemeral=True)

            # --- LOGIQUE DE NAVIGATION (utilise 'player' et 'interaction.guild') ---
            if custom_id == "nav_main_menu":
                embed = self.generate_main_embed(player, interaction.guild)
                await interaction.edit_original_response(embed=embed, view=MainMenuView())
            elif custom_id == "nav_stats":
                embed = self.generate_stats_embed(player, interaction.guild)
                await interaction.edit_original_response(embed=embed, view=BackView())
            elif custom_id == "nav_actions":
                server_state = db.query(ServerState).filter_by(guild_id=str(interaction.guild.id)).first()
                embed = self.generate_main_embed(player, interaction.guild)
                await interaction.edit_original_response(embed=embed, view=ActionsView(player, server_state))
            elif custom_id == "nav_phone":
                embed = self.get_base_embed(player, interaction.guild)
                embed.description = "Vous ouvrez votre téléphone."
                await interaction.edit_original_response(embed=embed, view=PhoneMainView())

            # --- LOGIQUE D'ACTION (centralisée) ---
            message = ""
            if custom_id.startswith("action_"):
                if custom_id == "action_eat":
                    message = cooker_brain.perform_eat(player)
                elif custom_id == "action_drink":
                    message = cooker_brain.perform_drink(player)
                elif custom_id == "action_sleep":
                    message = cooker_brain.perform_sleep(player)
                elif custom_id == "action_smoke":
                    message = cooker_brain.perform_smoke(player)
                if custom_id == "action_urinate":
                    message = cooker_brain.perform_urinate(player)
                
                db.commit() # Sauvegarde les changements faits par le CookerBrain
                db.refresh(player)
                
                server_state = db.query(ServerState).filter_by(guild_id=str(interaction.guild.id)).first()
                new_embed = self.generate_main_embed(player, interaction.guild)
                await interaction.edit_original_response(embed=new_embed, view=ActionsView(player, server_state))
                await interaction.followup.send(f"✅ {message}", ephemeral=True)

        except Exception as e:
            print(f"Erreur dans le listener d'interaction: {e}")
            await interaction.followup.send(f"Une erreur est survenue: {e}", ephemeral=True)
            db.rollback()
        finally:
            db.close()

async def setup(bot):
    await bot.add_cog(MainEmbed(bot))