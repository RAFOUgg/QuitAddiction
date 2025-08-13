# --- cogs/main_embed.py (FINAL & ROBUST - CRASH FIX) ---

import discord
from discord.ext import commands
from discord import ui
from db.database import SessionLocal
from db.models import ServerState, PlayerProfile
import datetime
import asyncio
import traceback
from .phone import PhoneMainView
from utils.helpers import clamp, format_time_delta

def generate_progress_bar(value: float, max_value: float = 100.0, length: int = 10, high_is_bad: bool = False) -> str:
    """Génère une barre de progression textuelle et colorée."""
    if not isinstance(value, (int, float)): value = 0.0
    value = clamp(value, 0, max_value)
    percent = value / max_value
    filled_length = int(length * percent)
    if (high_is_bad and percent > 0.7) or (not high_is_bad and percent < 0.3): bar_filled = '🟥'
    elif (high_is_bad and percent > 0.4) or (not high_is_bad and percent < 0.6): bar_filled = '🟧'
    else: bar_filled = '🟩'
    bar_empty = '⬛'
    return f"`{bar_filled * filled_length}{bar_empty * (length - filled_length)}`"

# --- VUES ---
class MainMenuView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ui.Button(label="🏃‍♂️ Actions", style=discord.ButtonStyle.primary, custom_id="nav_actions"))
        self.add_item(ui.Button(label="👖 Inventaire", style=discord.ButtonStyle.secondary, custom_id="nav_inventory"))
        self.add_item(ui.Button(label="📱 Téléphone", style=discord.ButtonStyle.blurple, custom_id="nav_phone"))
        self.add_item(ui.Button(label="🧠 Voir les Stats", style=discord.ButtonStyle.grey, custom_id="nav_stats"))

class StatsView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ui.Button(label="🏃‍♂️ Actions", style=discord.ButtonStyle.primary, custom_id="nav_actions"))
        self.add_item(ui.Button(label="👖 Inventaire", style=discord.ButtonStyle.secondary, custom_id="nav_inventory"))
        self.add_item(ui.Button(label="📱 Téléphone", style=discord.ButtonStyle.blurple, custom_id="nav_phone"))
        self.add_item(ui.Button(label="🙈 Cacher les Stats", style=discord.ButtonStyle.grey, custom_id="nav_main_menu"))

class BackView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ui.Button(label="⬅️ Retour au Tableau de Bord", style=discord.ButtonStyle.grey, custom_id="nav_main_menu"))

class ActionsView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=None)
        now = datetime.datetime.utcnow()
        cooldown_active = player.last_action_at and (now - player.last_action_at).total_seconds() < 10
        self.add_item(ui.Button(label=f"Manger (x{player.food_servings})", style=discord.ButtonStyle.success, custom_id="action_eat", emoji="🍽️", disabled=(player.food_servings <= 0 or cooldown_active)))
        self.add_item(ui.Button(label=f"Boire (x{player.water_bottles + player.beers})", style=discord.ButtonStyle.primary, custom_id="action_drink", emoji="💧", disabled=((player.water_bottles + player.beers) <= 0 or cooldown_active)))
        self.add_item(ui.Button(label="Dormir", style=discord.ButtonStyle.secondary, custom_id="action_sleep", emoji="🛏️", disabled=(cooldown_active)))
        self.add_item(ui.Button(label=f"Fumer (x{player.cigarettes})", style=discord.ButtonStyle.danger, custom_id="action_smoke", emoji="🚬", disabled=(player.cigarettes <= 0 or cooldown_active)))
        if player.bladder > 30: self.add_item(ui.Button(label=f"Uriner ({player.bladder:.0f}%)", style=discord.ButtonStyle.danger if player.bladder > 80 else discord.ButtonStyle.blurple, custom_id="action_urinate", emoji="🚽", row=1, disabled=(cooldown_active)))
        self.add_item(ui.Button(label="⬅️ Retour au Tableau de Bord", style=discord.ButtonStyle.grey, custom_id="nav_main_menu", row=2))

# --- COG ---
class MainEmbed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(MainMenuView())
        self.bot.add_view(StatsView())
        self.bot.add_view(BackView())
        self.bot.add_view(PhoneMainView())

    def get_character_thoughts(self, player: PlayerProfile) -> str:
        """Détermine la pensée la plus urgente du personnage."""
        if player.health < 30: return "Je... je ne me sens pas bien du tout. J'ai mal partout."
        if player.withdrawal_severity > 60: return "Ça tremble... il m'en faut une, et vite. Je n'arrive plus à réfléchir."
        if player.thirst > 80: return "J'ai la gorge complètement sèche, je pourrais boire n'importe quoi."
        if player.hunger > 75: return "Mon estomac gargouille si fort, il faut que je mange."
        if player.fatigue > 80: return "Mes paupières sont lourdes, je pourrais m'endormir debout."
        if player.stress > 70: return "J'ai les nerfs à vif, tout m'angoisse."
        if player.withdrawal_severity > 20: return "Je commence à sentir le manque... Une cigarette me ferait du bien."
        if player.boredom > 60: return "Je m'ennuie... il ne se passe jamais rien."
        return "Pour l'instant, ça va à peu près."

    def generate_dashboard_embed(self, player: PlayerProfile, guild: discord.Guild, show_stats: bool = False) -> discord.Embed:
        embed = discord.Embed(title="👨‍🍳 Le Quotidien du Cuisinier", color=0x3498db)
        
        asset_cog = self.bot.get_cog("AssetManager")
        image_name = "neutral"
        if player.stress > 70 or player.hunger > 70 or player.health < 40:
            image_name = "sad"
            embed.color = 0xe74c3c
        image_url = asset_cog.get_url(image_name) if asset_cog else None
        
        embed.description = f"**Pensées du Cuisinier :**\n*\"{self.get_character_thoughts(player)}\"*"

        if state and state.is_test_mode and state.game_start_time:
            admin_cog = self.bot.get_cog("AdminCog")
            if admin_cog:
                now = datetime.datetime.utcnow()
                elapsed_time = now - state.game_start_time
                elapsed_seconds = elapsed_time.total_seconds()
                
                minutes, seconds = divmod(int(elapsed_seconds), 60)
                elapsed_str = f"{minutes:02d}:{seconds:02d}"

                test_total_seconds = admin_cog.TEST_DURATION_MINUTES * 60
                progress_percent = (elapsed_seconds / test_total_seconds) * 100
                progress_bar = generate_progress_bar(progress_percent, 100, length=20)
                
                logs = player.recent_logs if player.recent_logs else "No autonomous actions yet."

                debug_info = (
                    f"**Temps Écoulé:** `{elapsed_str}` / `{admin_cog.TEST_DURATION_MINUTES}:00`\n"
                    f"**Progression:** {progress_bar}\n"
                    f"**Logs Autonomes:**\n```\n{logs}\n```"
                )
                embed.add_field(name="📊 Test-Mode Monitoring", value=debug_info, inline=False)

        if show_stats:
            if image_url:
                embed.set_thumbnail(url=image_url)
                # --- CORRECTION ---
                # Remplacer 'embed.image = None' par 'embed.set_image(url=None)'
                embed.set_image(url=None) 

            phys_health = (f"**Santé:** {generate_progress_bar(player.health, high_is_bad=False)} `{player.health:.0f}%`\n" f"**Énergie:** {generate_progress_bar(player.energy, high_is_bad=False)} `{player.energy:.0f}%`\n" f"**Fatigue:** {generate_progress_bar(player.fatigue, high_is_bad=True)} `{player.fatigue:.0f}%`\n" f"**Toxines:** {generate_progress_bar(player.tox, high_is_bad=True)} `{player.tox:.0f}%`")
            embed.add_field(name="❤️ Santé Physique", value=phys_health, inline=True)
            mental_health = (f"**Mentale:** {generate_progress_bar(player.sanity, high_is_bad=False)} `{player.sanity:.0f}%`\n" f"**Stress:** {generate_progress_bar(player.stress, high_is_bad=True)} `{player.stress:.0f}%`\n" f"**Humeur:** {generate_progress_bar(player.happiness, high_is_bad=False)} `{player.happiness:.0f}%`\n" f"**Ennui:** {generate_progress_bar(player.boredom, high_is_bad=True)} `{player.boredom:.0f}%`")
            embed.add_field(name="🧠 État Mental", value=mental_health, inline=True)
            embed.add_field(name="\u200b", value="\u200b", inline=False)
            symptoms = (f"**Douleur:** {generate_progress_bar(player.pain, high_is_bad=True)} `{player.pain:.0f}%`\n" f"**Nausée:** {generate_progress_bar(player.nausea, high_is_bad=True)} `{player.nausea:.0f}%`\n" f"**Vertiges:** {generate_progress_bar(player.dizziness, high_is_bad=True)} `{player.dizziness:.0f}%`\n" f"**Gorge Irritée:** {generate_progress_bar(player.sore_throat, high_is_bad=True)} `{player.sore_throat:.0f}%`")
            embed.add_field(name="🤕 Symptômes", value=symptoms, inline=True)
            addiction = (f"**Dépendance:** {generate_progress_bar(player.substance_addiction_level, high_is_bad=True)}`{player.substance_addiction_level:.1f}%`\n" f"**Manque:** {generate_progress_bar(player.withdrawal_severity, high_is_bad=True)} `{player.withdrawal_severity:.1f}%`\n" f"**Défonce:** {generate_progress_bar(player.intoxication_level, high_is_bad=True)} `{player.intoxication_level:.1f}%`")
            embed.add_field(name="🚬 Addiction", value=addiction, inline=True)
        else:
            if image_url:
                embed.set_image(url=image_url)
            embed.add_field(name="\u200b", value="*Cliquez sur `🧠 Voir les Stats` pour afficher les détails.*", inline=False)

        embed.set_footer(text=f"Jeu sur le serveur {guild.name} • Dernière mise à jour :")
        embed.timestamp = datetime.datetime.utcnow()
        return embed

    def generate_inventory_embed(self, player: PlayerProfile, guild: discord.Guild) -> discord.Embed:
        embed = discord.Embed(title="👖 Inventaire du Cuisinier", color=0x2ecc71)
        embed.description = "Contenu de vos poches et de votre portefeuille."
        inventory_list = (
            f"🚬 Cigarettes: **{player.cigarettes}**\n"
            f"🍺 Bières: **{player.beers}**\n"
            f"💧 Bouteilles d'eau: **{player.water_bottles}**\n"
            f"🍔 Portions de nourriture: **{player.food_servings}**\n"
            f"🌿 Joints: **{player.joints}**"
        )
        embed.add_field(name="Consommables", value=inventory_list, inline=True)
        embed.add_field(name="Argent", value=f"💰 **{player.wallet}$**", inline=True)
        embed.set_footer(text=f"Jeu sur le serveur {guild.name}")
        embed.timestamp = datetime.datetime.utcnow()
        return embed

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.data or "custom_id" not in interaction.data: return
        custom_id = interaction.data["custom_id"]
        # On ne gère pas les interactions du shop ici
        if not (custom_id.startswith("nav_") or custom_id.startswith("action_")): return

        await interaction.response.defer()
        db = SessionLocal()
        try:
            player = db.query(PlayerProfile).filter_by(guild_id=str(interaction.guild.id)).first()
            state = db.query(ServerState).filter_by(guild_id=str(interaction.guild.id)).first()
            if not player or not state:
                return await interaction.followup.send("Erreur: Profil ou état du serveur introuvable.", ephemeral=True)

            if custom_id == "nav_main_menu":
                await interaction.edit_original_response(embed=self.generate_dashboard_embed(player, state, interaction.guild, show_stats=False), view=MainMenuView())
            
            elif custom_id == "nav_stats":
                await interaction.edit_original_response(embed=self.generate_dashboard_embed(player, state, interaction.guild, show_stats=True), view=StatsView())

            elif custom_id == "nav_inventory":
                await interaction.edit_original_response(embed=self.generate_inventory_embed(player, interaction.guild), view=BackView())
            
            elif custom_id == "nav_actions":
                await interaction.edit_original_response(embed=self.generate_dashboard_embed(player, state, interaction.guild, show_stats=True), view=ActionsView(player))

            elif custom_id == "nav_phone":
                embed = self.generate_dashboard_embed(player, state, interaction.guild, show_stats=False)
                embed.description = "Vous ouvrez votre téléphone."
                await interaction.edit_original_response(embed=embed, view=PhoneMainView())
            
            elif custom_id.startswith("action_"):
                cooker_brain = self.bot.get_cog("CookerBrain")
                if player.last_action_at and (datetime.datetime.utcnow() - player.last_action_at).total_seconds() < 10:
                    return await interaction.followup.send("Vous agissez trop vite ! Attendez un peu.", ephemeral=True)
                
                action_map = {
                    "action_eat": cooker_brain.perform_eat, "action_drink": cooker_brain.perform_drink,
                    "action_sleep": cooker_brain.perform_sleep, "action_smoke": cooker_brain.perform_smoke,
                    "action_urinate": cooker_brain.perform_urinate
                }
                message, changes = action_map[custom_id](player)
                
                if not changes: return await interaction.followup.send(f"⚠️ {message}", ephemeral=True)

                player.last_action_at = datetime.datetime.utcnow()
                db.commit(); db.refresh(player)
                
                feedback_str = " ".join([f"**{stat}:** `{val}`" for stat, val in changes.items()])
                await interaction.followup.send(f"✅ {message}\n{feedback_str}", ephemeral=True)
                
                current_view = ActionsView(player)
                
                if custom_id in ["action_smoke", "action_drink", "action_eat"]:
                    action_image_map = {"smoke": "smoke_cig", "drink": "neutral_drinking", "eat": "neutral_eating"}
                    image_key = custom_id.split('_')[1]
                    asset_cog = self.bot.get_cog("AssetManager")
                    action_image_url = asset_cog.get_url(action_image_map.get(image_key)) if asset_cog else None
                    
                    if action_image_url:
                        animated_embed = self.generate_dashboard_embed(player, state, interaction.guild, show_stats=True)
                        animated_embed.set_image(url=action_image_url)
                        animated_embed.set_thumbnail(url=None)
                        await interaction.edit_original_response(embed=animated_embed, view=current_view)
                        await asyncio.sleep(5)
                
                db.refresh(player)
                final_embed = self.generate_dashboard_embed(player, state, interaction.guild, show_stats=True)
                final_view = ActionsView(player)
                await interaction.edit_original_response(embed=final_embed, view=final_view)

        except Exception as e:
            print(f"Erreur dans le listener d'interaction de MainEmbed: {e}\n{traceback.format_exc()}")
            if not interaction.response.is_done():
                await interaction.followup.send("Une erreur est survenue.", ephemeral=True)
            db.rollback()
        finally:
            db.close()

async def setup(bot):
    await bot.add_cog(MainEmbed(bot))