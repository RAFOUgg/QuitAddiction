# --- cogs/main_embed.py (FINAL VERSION WITH VISUAL UPGRADES) ---

import discord
from discord.ext import commands
from discord import ui
from db.database import SessionLocal
from db.models import ServerState, PlayerProfile
import datetime
import asyncio

from .phone import PhoneMainView 
from utils.helpers import clamp, format_time_delta

def generate_progress_bar(value: float, max_value: float = 100.0, length: int = 10, high_is_bad: bool = False) -> str:
    """Génère une barre de progression textuelle et colorée."""
    if not isinstance(value, (int, float)): value = 0.0
    value = clamp(value, 0, max_value)
    
    percent = value / max_value
    filled_length = int(length * percent)
    
    # Déterminer la couleur en fonction du pourcentage et du type de jauge
    if (high_is_bad and percent > 0.7) or (not high_is_bad and percent < 0.3):
        bar_filled = '🟥' # Rouge pour un état critique
    elif (high_is_bad and percent > 0.4) or (not high_is_bad and percent < 0.6):
        bar_filled = '🟧' # Orange pour un état moyen
    else:
        bar_filled = '🟩' # Vert pour un bon état
        
    bar_empty = '⬛'
    return f"`{bar_filled * filled_length}{bar_empty * (length - filled_length)}`"

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
        cooldown_active = player.last_action_at and (now - player.last_action_at).total_seconds() < 10

        self.add_item(ui.Button(label=f"Manger (x{player.food_servings})", style=discord.ButtonStyle.success, custom_id="action_eat", emoji="🍽️", disabled=(player.food_servings <= 0 or cooldown_active)))
        self.add_item(ui.Button(label=f"Boire (x{player.water_bottles + player.beers})", style=discord.ButtonStyle.primary, custom_id="action_drink", emoji="💧", disabled=((player.water_bottles + player.beers) <= 0 or cooldown_active)))
        self.add_item(ui.Button(label="Dormir", style=discord.ButtonStyle.secondary, custom_id="action_sleep", emoji="🛏️", disabled=(cooldown_active)))
        self.add_item(ui.Button(label=f"Fumer (x{player.cigarettes})", style=discord.ButtonStyle.danger, custom_id="action_smoke", emoji="🚬", disabled=(player.cigarettes <= 0 or cooldown_active)))
        if player.bladder > 30:
            self.add_item(ui.Button(label=f"Uriner ({player.bladder:.0f}%)", style=discord.ButtonStyle.danger if player.bladder > 80 else discord.ButtonStyle.blurple, custom_id="action_urinate", emoji="🚽", row=1, disabled=(cooldown_active)))
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
        
        # --- LOGIQUE D'IMAGE MISE À JOUR ---
        image_name = "neutral" # Utilise neutral.png par défaut
        if player.stress > 70 or player.hunger > 70 or player.thirst > 70 or player.health < 40:
            image_name = "sad" # Utilise sad.png si l'état est mauvais
            embed.color = 0xe74c3c
        
        image_url = asset_cog.get_url(image_name) if asset_cog else None
        if image_url: embed.set_image(url=image_url)
        else: embed.add_field(name="⚠️ Asset manquant", value=f"L'image '{image_name}.png' n'a pas été trouvée.")
        
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
        """Génère l'embed détaillé et réorganisé des statistiques avec les nouvelles jauges."""
        embed = self.get_base_embed(player, guild)
        embed.description = "Aperçu de l'état de santé physique et mental du cuisinier."
        
        phys_health = (
            f"**Santé:** {generate_progress_bar(player.health, high_is_bad=False)} `{player.health:.0f}%`\n"
            f"**Énergie:** {generate_progress_bar(player.energy, high_is_bad=False)} `{player.energy:.0f}%`\n"
            f"**Fatigue:** {generate_progress_bar(player.fatigue, high_is_bad=True)} `{player.fatigue:.0f}%`\n"
            f"**Toxines:** {generate_progress_bar(player.tox, high_is_bad=True)} `{player.tox:.0f}%`"
        )
        embed.add_field(name="❤️ Santé Physique", value=phys_health, inline=True)

        mental_health = (
            f"**Mentale:** {generate_progress_bar(player.sanity, high_is_bad=False)} `{player.sanity:.0f}%`\n"
            f"**Stress:** {generate_progress_bar(player.stress, high_is_bad=True)} `{player.stress:.0f}%`\n"
            f"**Humeur:** {generate_progress_bar(player.happiness, high_is_bad=False)} `{player.happiness:.0f}%`\n"
            f"**Ennui:** {generate_progress_bar(player.boredom, high_is_bad=True)} `{player.boredom:.0f}%`"
        )
        embed.add_field(name="🧠 État Mental", value=mental_health, inline=True)
        
        embed.add_field(name="\u200b", value="\u200b", inline=False) 

        symptoms = (
            f"**Douleur:** {generate_progress_bar(player.pain, high_is_bad=True)} `{player.pain:.0f}%`\n"
            f"**Nausée:** {generate_progress_bar(player.nausea, high_is_bad=True)} `{player.nausea:.0f}%`\n"
            f"**Vertiges:** {generate_progress_bar(player.dizziness, high_is_bad=True)} `{player.dizziness:.0f}%`\n"
            f"**Mal de Tête:** {generate_progress_bar(player.headache, high_is_bad=True)} `{player.headache:.0f}%`\n"
            f"**Gorge Irritée:** {generate_progress_bar(player.sore_throat, high_is_bad=True)} `{player.sore_throat:.0f}%`\n"
            f"**Bouche Sèche:** {generate_progress_bar(player.dry_mouth, high_is_bad=True)} `{player.dry_mouth:.0f}%`"
        )
        embed.add_field(name="🤕 Symptômes", value=symptoms, inline=True)
        
        addiction = (
            f"**Dépendance:** {generate_progress_bar(player.substance_addiction_level, high_is_bad=True)} `{player.substance_addiction_level:.1f}%`\n"
            f"**Manque:** {generate_progress_bar(player.withdrawal_severity, high_is_bad=True)} `{player.withdrawal_severity:.1f}%`\n"
            f"**Défonce:** {generate_progress_bar(player.intoxication_level, high_is_bad=True)} `{player.intoxication_level:.1f}%`"
        )
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
            if not player: return await interaction.followup.send("Erreur: Profil du cuisinier introuvable.", ephemeral=True)

            # --- LOGIQUE DE NAVIGATION ---
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
            
            # --- LOGIQUE D'ACTION ---
            elif custom_id.startswith("action_"):
                if player.last_action_at and (datetime.datetime.utcnow() - player.last_action_at).total_seconds() < 10:
                    return await interaction.followup.send("Vous agissez trop vite ! Attendez un peu.", ephemeral=True)
                player.last_action_at = datetime.datetime.utcnow()
                cooker_brain = self.bot.get_cog("CookerBrain")
                if not cooker_brain: return await interaction.followup.send("Erreur: Moteur de jeu non trouvé.", ephemeral=True)
                
                message = ""
                
                # --- CAS SPÉCIAL POUR L'ACTION DE FUMER ---
                if custom_id == "action_smoke":
                    message = cooker_brain.perform_smoke(player)
                    db.commit(); db.refresh(player)
                    asset_cog = self.bot.get_cog("AssetManager")
                    smoking_image_url = asset_cog.get_url("smoke_cig") if asset_cog else None
                    if smoking_image_url:
                        smoking_embed = self.get_base_embed(player, interaction.guild)
                        smoking_embed.set_image(url=smoking_image_url)
                        smoking_embed.description = "Le cuisinier prend une pause cigarette..."
                        await interaction.edit_original_response(embed=smoking_embed, view=ActionsView(player))
                    await interaction.followup.send(f"✅ {message}", ephemeral=True)
                    await asyncio.sleep(7)
                    db.refresh(player) 
                    final_embed = self.generate_main_embed(player, interaction.guild)
                    await interaction.edit_original_response(embed=final_embed, view=ActionsView(player))

                # --- NOUVEAU CAS SPÉCIAL POUR L'ACTION DE BOIRE ---
                elif custom_id == "action_drink":
                    message = cooker_brain.perform_drink(player)
                    db.commit(); db.refresh(player)
                    asset_cog = self.bot.get_cog("AssetManager")
                    
                    # Choisir l'image de boisson en fonction de l'état du joueur
                    is_sad = player.stress > 70 or player.hunger > 70 or player.health < 40
                    drink_image_name = "sad_drinking" if is_sad else "neutral_drinking"
                    drinking_image_url = asset_cog.get_url(drink_image_name) if asset_cog else None

                    if drinking_image_url:
                        drinking_embed = self.get_base_embed(player, interaction.guild)
                        drinking_embed.set_image(url=drinking_image_url)
                        drinking_embed.description = "Il s'hydrate..."
                        await interaction.edit_original_response(embed=drinking_embed, view=ActionsView(player))
                    
                    await interaction.followup.send(f"✅ {message}", ephemeral=True)
                    await asyncio.sleep(5)
                    db.refresh(player)
                    final_embed = self.generate_main_embed(player, interaction.guild)
                    await interaction.edit_original_response(embed=final_embed, view=ActionsView(player))

                # --- CAS GÉNÉRAL POUR LES AUTRES ACTIONS ---
                else:
                    if custom_id == "action_eat": message = cooker_brain.perform_eat(player)
                    elif custom_id == "action_sleep": message = cooker_brain.perform_sleep(player)
                    elif custom_id == "action_urinate": message = cooker_brain.perform_urinate(player)
                    
                    if message:
                        db.commit(); db.refresh(player)
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