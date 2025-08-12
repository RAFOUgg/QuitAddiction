# --- cogs/main_embed.py (FINAL VERSION WITH NEW UI) ---

import discord
from discord.ext import commands
from discord import ui
from db.database import SessionLocal
from db.models import ServerState, PlayerProfile
import datetime
from .phone import PhoneMainView 
from utils.helpers import clamp, format_time_delta # Assurez-vous d'avoir ce fichier

def generate_progress_bar(value: float, max_value: float = 100.0, length: int = 10) -> str:
    if not isinstance(value, (int, float)): value = 0
    if value < 0: value = 0
    if value > max_value: value = max_value
    percent = value / max_value
    filled_length = int(length * percent)
    bar_filled = '🟩'
    bar_empty = '⬛'
    return f"`{bar_filled * filled_length}{bar_empty * (length - filled_length)}`"

# --- VUES ---
class MainMenuView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ui.Button(label="🧠 Cerveau", style=discord.ButtonStyle.secondary, custom_id="nav_stats"))
        self.add_item(ui.Button(label="🏃‍♂️ Actions", style=discord.ButtonStyle.primary, custom_id="nav_actions"))
        self.add_item(ui.Button(label="📱 Téléphone", style=discord.ButtonStyle.blurple, custom_id="nav_phone"))

class BackView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ui.Button(label="⬅️ Retour", style=discord.ButtonStyle.grey, custom_id="nav_main_menu"))

class ActionsView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=None)
        now = datetime.datetime.utcnow()

        self.add_item(ui.Button(label=f"Manger (il y a {format_time_delta(now - player.last_eaten_at)})", style=discord.ButtonStyle.success, custom_id="action_eat", emoji="🍽️", row=0))
        self.add_item(ui.Button(label=f"Boire (il y a {format_time_delta(now - player.last_drank_at)})", style=discord.ButtonStyle.primary, custom_id="action_drink", emoji="💧", row=0))
        self.add_item(ui.Button(label=f"Dormir (il y a {format_time_delta(now - player.last_slept_at)})", style=discord.ButtonStyle.secondary, custom_id="action_sleep", emoji="🛏️", row=0))

        time_since_last_smoke_sec = (now - player.last_smoked_at).total_seconds() if player.last_smoked_at else float('inf')
        time_to_craving_min = max(0, (7200 - time_since_last_smoke_sec) / 60)
        
        if player.withdrawal_severity > 10:
            smoke_label = "Fumer (Manque !)"
            smoke_style = discord.ButtonStyle.danger
        elif time_to_craving_min < 60 :
            smoke_label = f"Fumer (Manque ~{int(time_to_craving_min)}m)"
            smoke_style = discord.ButtonStyle.danger
        else:
            smoke_label = "Fumer"
            smoke_style = discord.ButtonStyle.secondary
        self.add_item(ui.Button(label=smoke_label, style=smoke_style, custom_id="action_smoke", emoji="🚬", row=0))

        if player.bladder > 30:
            self.add_item(ui.Button(label=f"Uriner ({player.bladder:.0f}%)", style=discord.ButtonStyle.danger if player.bladder > 80 else discord.ButtonStyle.blurple, custom_id="action_urinate", emoji="🚽", row=1))
        
        self.add_item(ui.Button(label="⬅️ Retour au menu", style=discord.ButtonStyle.grey, custom_id="nav_main_menu", row=2))

# --- COG ---
class MainEmbed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.add_view(MainMenuView())
        bot.add_view(BackView())
        bot.add_view(PhoneMainView())

    def get_base_embed(self, player: PlayerProfile, guild: discord.Guild) -> discord.Embed:
        embed = discord.Embed(title="👨‍🍳 Le Quotidien du Cuisinier", color=0x3498db)
        asset_cog = self.bot.get_cog("AssetManager")
        image_name = "happy"
        if player.stress > 70 or player.hunger > 70 or player.thirst > 70 or player.health < 40:
            image_name = "sad"
            embed.color = 0xe74c3c
        image_url = asset_cog.get_url(image_name) if asset_cog else None
        if image_url: embed.set_image(url=image_url)
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3423/3423485.png")
        embed.set_footer(text=f"Jeu sur le serveur {guild.name}")
        return embed

    def generate_main_embed(self, player: PlayerProfile, guild: discord.Guild) -> discord.Embed:
        embed = self.get_base_embed(player, guild)
        status_description = "Il a l'air de bien se porter."
        if player.stress > 70 or player.hunger > 70 or player.thirst > 70:
            status_description = "Il a l'air fatigué et stressé... Il a besoin d'aide."
        embed.description = f"*Dernière mise à jour : <t:{int(datetime.datetime.now().timestamp())}:R>*\n{status_description}"
        return embed

    def generate_stats_embed(self, player: PlayerProfile, guild: discord.Guild) -> discord.Embed:
        embed = self.get_base_embed(player, guild)
        embed.description = "Aperçu de l'état de santé physique et mental du cuisinier."
        
        phys_health = (f"**Santé:** {generate_progress_bar(player.health)} `{player.health:.0f}%`\n" f"**Énergie:** {generate_progress_bar(player.energy)} `{player.energy:.0f}%`\n" f"**Fatigue:** {generate_progress_bar(player.fatigue)} `{player.fatigue:.0f}%`\n" f"**Toxines:** {generate_progress_bar(player.tox)} `{player.tox:.0f}%`")
        embed.add_field(name="❤️ Santé Physique", value=phys_health, inline=True)

        mental_health = (f"**Mentale:** {generate_progress_bar(player.sanity)} `{player.sanity:.0f}%`\n" f"**Stress:** {generate_progress_bar(player.stress)} `{player.stress:.0f}%`\n" f"**Humeur:** {generate_progress_bar(player.happiness)} `{player.happiness:.0f}%`\n" f"**Ennui:** {generate_progress_bar(player.boredom)} `{player.boredom:.0f}%`")
        embed.add_field(name="🧠 État Mental", value=mental_health, inline=True)
        
        embed.add_field(name="\u200b", value="\u200b", inline=False) 

        symptoms = (f"**Douleur:** {generate_progress_bar(player.pain)} `{player.pain:.0f}%`\n" f"**Nausée:** {generate_progress_bar(player.nausea)} `{player.nausea:.0f}%`\n" f"**Vertiges:** {generate_progress_bar(player.dizziness)} `{player.dizziness:.0f}%`\n" f"**Mal de Tête:** {generate_progress_bar(player.headache)} `{player.headache:.0f}%`\n" f"**Gorge Irritée:** {generate_progress_bar(player.sore_throat)} `{player.sore_throat:.0f}%`\n" f"**Bouche Sèche:** {generate_progress_bar(player.dry_mouth)} `{player.dry_mouth:.0f}%`")
        embed.add_field(name="🤕 Symptômes", value=symptoms, inline=True)
        
        addiction = (f"**Dépendance:** {generate_progress_bar(player.substance_addiction_level)} `{player.substance_addiction_level:.1f}%`\n" f"**Manque:** {generate_progress_bar(player.withdrawal_severity)} `{player.withdrawal_severity:.1f}%`\n" f"**Défonce:** {generate_progress_bar(player.intoxication_level)} `{player.intoxication_level:.1f}%`")
        embed.add_field(name="🚬 Addiction", value=addiction, inline=True)
        
        return embed

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.data or "custom_id" not in interaction.data: return
        custom_id = interaction.data["custom_id"]
        if not (custom_id.startswith("nav_") or custom_id.startswith("action_")): return

        await interaction.response.defer()
        db = SessionLocal()
        try:
            player = db.query(PlayerProfile).filter_by(guild_id=str(interaction.guild.id)).first()
            if not player:
                return await interaction.followup.send("Erreur: Profil du cuisinier introuvable.", ephemeral=True)

            # Navigation
            if custom_id == "nav_main_menu":
                await interaction.edit_original_response(embed=self.generate_main_embed(player, interaction.guild), view=MainMenuView())
            elif custom_id == "nav_stats":
                await interaction.edit_original_response(embed=self.generate_stats_embed(player, interaction.guild), view=BackView())
            elif custom_id == "nav_actions":
                await interaction.edit_original_response(embed=self.generate_main_embed(player, interaction.guild), view=ActionsView(player))
            elif custom_id == "nav_phone":
                embed = self.get_base_embed(player, interaction.guild)
                embed.description = "Vous ouvrez votre téléphone."
                await interaction.edit_original_response(embed=embed, view=PhoneMainView())
            
            # Actions
            elif custom_id.startswith("action_"):
                cooker_brain = self.bot.get_cog("CookerBrain")
                message = ""
                if custom_id == "action_eat": message = cooker_brain.perform_eat(player)
                elif custom_id == "action_drink": message = cooker_brain.perform_drink(player)
                elif custom_id == "action_sleep": message = cooker_brain.perform_sleep(player)
                elif custom_id == "action_smoke": message = cooker_brain.perform_smoke(player)
                elif custom_id == "action_urinate": message = cooker_brain.perform_urinate(player)
                
                db.commit()
                db.refresh(player)
                
                new_embed = self.generate_main_embed(player, interaction.guild)
                await interaction.edit_original_response(embed=new_embed, view=ActionsView(player))
                await interaction.followup.send(f"✅ {message}", ephemeral=True)

        except Exception as e:
            print(f"Erreur dans le listener d'interaction: {e}")
            await interaction.followup.send("Une erreur est survenue.", ephemeral=True)
            db.rollback()
        finally:
            db.close()

async def setup(bot):
    await bot.add_cog(MainEmbed(bot))