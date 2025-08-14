# --- cogs/main_embed.py (REFACTORED AND CORRECTED) ---

import discord
from discord.ext import commands
from discord import ui
from db.database import SessionLocal
from db.models import ServerState, PlayerProfile
import datetime
import traceback
from .phone import PhoneMainView
from utils.helpers import clamp

def generate_progress_bar(value: float, max_value: float = 100.0, length: int = 10, high_is_bad: bool = False) -> str:
    if not isinstance(value, (int, float)): value = 0.0
    value = clamp(value, 0, max_value)
    percent = value / max_value
    bar_filled = '🟥' if (high_is_bad and percent > 0.7) or (not high_is_bad and percent < 0.3) else '🟧' if (high_is_bad and percent > 0.4) or (not high_is_bad and percent < 0.6) else '🟩'
    bar_empty = '⬛'
    return f"`{bar_filled * filled_length}{bar_empty * (length - filled_length)}`"

# --- VUES ---

class DashboardView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=None)
        self.update_buttons(player)

    def update_buttons(self, player: PlayerProfile):
        self.clear_items()
        self.add_item(ui.Button(label="Actions", style=discord.ButtonStyle.primary, custom_id="nav_actions", emoji="🏃‍♂️"))
        self.add_item(ui.Button(label="Inventaire", style=discord.ButtonStyle.secondary, custom_id="nav_inventory", emoji="👖"))
        self.add_item(ui.Button(label="Téléphone", style=discord.ButtonStyle.blurple, custom_id="phone_open", emoji="📱"))

        stats_label = "Cacher Cerveau" if player.show_stats_in_view else "Afficher Cerveau"
        stats_style = discord.ButtonStyle.success if player.show_stats_in_view else discord.ButtonStyle.secondary
        self.add_item(ui.Button(label=stats_label, style=stats_style, custom_id="nav_toggle_stats", row=1, emoji="🧠"))


class ActionsView(ui.View):
    """
    La vue pour les actions du joueur, maintenant avec plus d'options contextuelles.
    """
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=None)
        now = datetime.datetime.utcnow()
        cooldown_active = player.last_action_at and (now - player.last_action_at).total_seconds() < 10
        
        self.add_item(ui.Button(label="Manger", style=discord.ButtonStyle.success, custom_id="action_eat_menu", emoji="🍽️", disabled=cooldown_active))
        self.add_item(ui.Button(label="Boire", style=discord.ButtonStyle.primary, custom_id="action_drink_menu", emoji="💧", disabled=cooldown_active))
        self.add_item(ui.Button(label="Fumer", style=discord.ButtonStyle.danger, custom_id="action_smoke_menu", emoji="🚬", disabled=cooldown_active))
        self.add_item(ui.Button(label="Dormir", style=discord.ButtonStyle.secondary, custom_id="action_sleep", emoji="🛏️", disabled=cooldown_active))
        
        # --- LOGIQUE DE BOUTONS CONTEXTUELS AMÉLIORÉE ---
        # Regroupe les actions d'hygiène/besoins sur une deuxième ligne
        if player.hygiene < 40:
            self.add_item(ui.Button(label="Prendre une douche", style=discord.ButtonStyle.blurple, custom_id="action_shower", emoji="🚿", row=1, disabled=cooldown_active))
        if player.bladder > 30:
            style = discord.ButtonStyle.danger if player.bladder > 80 else discord.ButtonStyle.blurple
            self.add_item(ui.Button(label=f"Uriner ({player.bladder:.0f}%)", style=style, custom_id="action_urinate", emoji="🚽", row=1, disabled=cooldown_active))
        if player.bowels > 40: # NOUVEAU BOUTON
            style = discord.ButtonStyle.danger if player.bowels > 80 else discord.ButtonStyle.blurple
            self.add_item(ui.Button(label=f"Déféquer ({player.bowels:.0f}%)", style=style, custom_id="action_defecate", emoji="💩", row=1, disabled=cooldown_active))

        self.add_item(ui.Button(label="Retour", style=discord.ButtonStyle.grey, custom_id="nav_main_menu", row=2, emoji="⬅️"))

class EatView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=60)
        if player.food_servings > 0:
            self.add_item(ui.Button(label=f"Sandwich ({player.food_servings})", emoji="🥪", style=discord.ButtonStyle.success, custom_id="eat_sandwich"))
        if getattr(player, 'tacos', 0) > 0:
            self.add_item(ui.Button(label=f"Tacos ({player.tacos})", emoji="🌮", style=discord.ButtonStyle.primary, custom_id="eat_tacos"))
        if getattr(player, 'salad_servings', 0) > 0:
            self.add_item(ui.Button(label=f"Salade ({player.salad_servings})", emoji="🥗", style=discord.ButtonStyle.success, custom_id="eat_salad"))
        self.add_item(ui.Button(label="Retour", style=discord.ButtonStyle.grey, custom_id="nav_actions", row=1, emoji="⬅️"))

class DrinkView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=60)
        if player.water_bottles > 0:
            self.add_item(ui.Button(label=f"Eau ({player.water_bottles})", emoji="💧", style=discord.ButtonStyle.primary, custom_id="drink_water"))
        if player.soda_cans > 0:
            self.add_item(ui.Button(label=f"Soda ({player.soda_cans})", emoji="🥤", style=discord.ButtonStyle.blurple, custom_id="drink_soda"))
        self.add_item(ui.Button(label="Retour", style=discord.ButtonStyle.grey, custom_id="nav_actions", row=1, emoji="⬅️"))

class SmokeView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=60)
        if player.cigarettes > 0:
            self.add_item(ui.Button(label=f"Cigarette ({player.cigarettes})", emoji="🚬", style=discord.ButtonStyle.danger, custom_id="smoke_cigarette"))
        if player.e_cigarettes > 0:
            self.add_item(ui.Button(label=f"Vapoteuse ({player.e_cigarettes})", emoji="💨", style=discord.ButtonStyle.primary, custom_id="smoke_ecigarette"))
        self.add_item(ui.Button(label="Retour", style=discord.ButtonStyle.grey, custom_id="nav_actions", row=1, emoji="⬅️"))
        
class InventoryView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ui.Button(label="Retour au Tableau de Bord", style=discord.ButtonStyle.grey, custom_id="nav_main_menu", emoji="⬅️"))

# --- COG ---

class MainEmbed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_image_url(self, player: PlayerProfile) -> str | None:
        """Logique d'image améliorée pour inclure les nouvelles sensations."""
        now = datetime.datetime.utcnow()
        asset_cog = self.bot.get_cog("AssetManager")
        if not asset_cog: return None

        # Priority 1: Action récente (dure 10s)
        if player.last_action and player.last_action_time and (now - player.last_action_time).total_seconds() < 10:
            return asset_cog.get_url(player.last_action)

        image_name = "neutral"
        # Priority 2: Besoins critiques
        if player.bowels > 85: image_name = "neutral_pooping" # <- Ajouté
        elif player.bladder > 85: image_name = "need_pee"
        elif player.hunger > 85: image_name = "hungry"
        # Priority 3: États mentaux et physiques sévères
        elif player.fatigue > 90: image_name = "neutral_sleep"
        elif player.happiness < 10 and player.stress > 80: image_name = "sob"
        elif player.headache > 70: image_name = "scratch_eye" # <- Ajouté
        elif player.stomachache > 70: image_name = "hand_stomach" # <- Ajouté
        elif player.stress > 70 or player.health < 40: image_name = "sad"
        # Priority 4: Autres états
        elif player.withdrawal_severity > 60: image_name = "neutral_hold_e_cig" # Manque
        elif player.hygiene < 20: image_name = "neutral_shower"
        
        return asset_cog.get_url(image_name)

    @staticmethod
    def get_character_thoughts(player: PlayerProfile) -> str:
        # High-priority combinations
        if player.hunger > 70 and player.stress > 60:
            return "J'ai l'estomac dans les talons et les nerfs à vif. Un rien pourrait me faire craquer."
        if player.withdrawal_severity > 60 and player.health < 40:
            return "Chaque partie de mon corps me fait souffrir. Le manque me ronge de l'intérieur, je suis à bout."
        if player.fatigue > 80 and player.boredom > 70:
            return "Je suis épuisé, mais je m'ennuie tellement que je n'arrive même pas à fermer l'œil."
        if player.thirst > 80 and player.hygiene < 30:
            return "J'ai la gorge sèche et je me sens sale. Un verre d'eau et une douche, c'est tout ce que je demande."

        # Single-condition thoughts (from highest to lowest priority)
        thoughts = {
            95: (player.thirst > 85, "J'ai la gorge complètement sèche, je pourrais boire n'importe quoi."),
            90: (player.hunger > 80, "Mon estomac gargouille si fort, il faut que je mange."),
            85: (player.withdrawal_severity > 60, "Ça tremble... il m'en faut une, vite. Je peux plus réfléchir."),
            80: (player.fatigue > 85, "Mes paupières sont lourdes, je pourrais m'endormir debout."),
            75: (player.bladder > 90, "J'ai une envie TRÈS pressante, je vais plus tenir !"),
            70: (player.stress > 70, "J'ai les nerfs à vif, tout m'angoisse."),
            60: (player.hygiene < 20, "Je me sens vraiment sale, une douche me ferait le plus grand bien."),
            50: (player.craving_nicotine > 40, "Une clope me calmerait, là."),
            40: (player.health < 40, "Je... je ne me sens pas bien. J'ai mal partout."),
            30: (player.boredom > 60, "Je m'ennuie... il ne se passe jamais rien."),
            20: (player.craving_alcohol > 50, "Un verre me détendrait bien..."),
        }
        for priority in sorted(thoughts.keys(), reverse=True):
            condition, text = thoughts[priority]
            if condition: return text
            
        return "Pour l'instant, ça va à peu près."

    def generate_dashboard_embed(self, player: PlayerProfile, state: ServerState, guild: discord.Guild) -> discord.Embed:
        embed = discord.Embed(title="👨‍🍳 Le Quotidien du Cuisinier", color=0x3498db)
        image_url = self.get_image_url(player)
        
        if image_url:
            embed.set_image(url=image_url)
            if player.show_stats_in_view:
                embed.set_thumbnail(url=image_url)

        embed.description = f"**Pensées du Cuisinier :**\n*\"{self.get_character_thoughts(player)}\"*"

        if state and state.is_test_mode and state.game_start_time:
            admin_cog = self.bot.get_cog("AdminCog")
            if admin_cog:
                # 1 real minute = 1 game hour. 24 minutes = 24 hours.
                TIME_RATIO = 60 
                elapsed_real_seconds = (datetime.datetime.utcnow() - state.game_start_time).total_seconds()
                elapsed_game_seconds = elapsed_real_seconds * TIME_RATIO
                start_time_in_seconds = (state.game_day_start_hour or 8) * 3600
                current_game_total_seconds = start_time_in_seconds + elapsed_game_seconds
                game_hour = int((current_game_total_seconds / 3600) % 24)
                game_minute = int((current_game_total_seconds % 3600) / 60)
                time_str = f"{game_hour:02d}:{game_minute:02d}"
                
                progress_percent = (elapsed_real_seconds / (admin_cog.TEST_DURATION_MINUTES * 60)) * 100
                progress_bar = generate_progress_bar(progress_percent, 100, length=20)
                logs = player.recent_logs if player.recent_logs and player.recent_logs.strip() else "- RAS"
                
                embed.add_field(name="🕒 Horloge de Jeu (Test)", value=f"**Jour 1 - {time_str}**", inline=False)
                debug_info = (f"**Progression:** {progress_bar}\n" f"**Journal d'Événements :**\n```md\n{logs}\n```")
                embed.add_field(name="⚙️ Moniteur de Test", value=debug_info, inline=False)
                
        if player.show_stats_in_view:
            vital_needs = (f"**Faim:** {generate_progress_bar(player.hunger, high_is_bad=True)} `{player.hunger:.0f}%`\n"
                           f"**Soif:** {generate_progress_bar(player.thirst, high_is_bad=True)} `{player.thirst:.0f}%`\n"
                           f"**Vessie:** {generate_progress_bar(player.bladder, high_is_bad=True)} `{player.bladder:.0f}%`")
            embed.add_field(name="⚠️ Besoins Vitaux", value=vital_needs, inline=True)
            cravings = (f"🚬 **Tabac:** {generate_progress_bar(player.craving_nicotine, high_is_bad=True)} `{player.craving_nicotine:.0f}%`\n"
                        f"🍺 **Alcool:** {generate_progress_bar(player.craving_alcohol, high_is_bad=True)} `{player.craving_alcohol:.0f}%`\n"
                        f"❤️ **Sexe:** {generate_progress_bar(player.sex_drive, high_is_bad=True)} `{player.sex_drive:.0f}%`")
            embed.add_field(name="🔥 Désirs & Envies", value=cravings, inline=True)
            phys_health = (f"**Santé:** {generate_progress_bar(player.health)} `{player.health:.0f}%`\n"
                           f"**Énergie:** {generate_progress_bar(player.energy)} `{player.energy:.0f}%`\n"
                           f"**Hygiène:** {generate_progress_bar(player.hygiene)} `{player.hygiene:.0f}%`")
            embed.add_field(name="❤️ Santé Physique", value=phys_health, inline=False)
            mental_health = (f"**Mentale:** {generate_progress_bar(player.sanity, high_is_bad=False)} `{player.sanity:.0f}%`\n"
                             f"**Stress:** {generate_progress_bar(player.stress, high_is_bad=True)} `{player.stress:.0f}%`\n"
                             f"**Humeur:** {generate_progress_bar(player.happiness, high_is_bad=False)} `{player.happiness:.0f}%`\n"
                             f"**Ennui:** {generate_progress_bar(player.boredom, high_is_bad=True)} `{player.boredom:.0f}%`")
            embed.add_field(name="🧠 État Mental", value=mental_health, inline=True)
            embed.add_field(name="\u200b", value="\u200b", inline=False)
            symptoms = (f"**Douleur:** {generate_progress_bar(player.pain, high_is_bad=True)} `{player.pain:.0f}%`\n"
                        f"**Nausée:** {generate_progress_bar(player.nausea, high_is_bad=True)} `{player.nausea:.0f}%`\n"
                        f"**Vertiges:** {generate_progress_bar(player.dizziness, high_is_bad=True)} `{player.dizziness:.0f}%`")
            embed.add_field(name="🤕 Symptômes", value=symptoms, inline=True)
            addiction = (f"**Dépendance:** {generate_progress_bar(player.substance_addiction_level, high_is_bad=True)}`{player.substance_addiction_level:.1f}%`\n"
                         f"**Manque:** {generate_progress_bar(player.withdrawal_severity, high_is_bad=True)} `{player.withdrawal_severity:.1f}%`\n"
                         f"**Défonce:** {generate_progress_bar(player.intoxication_level, high_is_bad=True)} `{player.intoxication_level:.1f}%`")
            embed.add_field(name="🚬 Addiction", value=addiction, inline=True)
            if player.is_sick:
                embed.add_field(name="État Actuel", value="**Malade 🤒**", inline=False)

        embed.set_footer(text=f"Jeu sur le serveur {guild.name} • Dernière mise à jour :")
        embed.timestamp = datetime.datetime.utcnow()
        return embed

    def generate_inventory_embed(self, player: PlayerProfile, guild: discord.Guild) -> discord.Embed:
        embed = discord.Embed(title="👖 Inventaire du Cuisinier", color=0x2ecc71)
        inventory_items = [("cigarettes", "🚬 Cigarettes"), ("beers", "🍺 Bières"), ("water_bottles", "💧 Bouteilles d'eau"), ("food_servings", "🍔 Portions")]
        inventory_list = "".join([f"{label}: **{getattr(player, attr, 0)}\n" for attr, label in inventory_items if getattr(player, attr, 0) > 0])
        embed.add_field(name="Consommables", value=inventory_list or "*Vide*", inline=True)
        embed.add_field(name="Argent", value=f"💰 **{player.wallet}$**", inline=True)
        
        image_url = self.get_image_url(player)
        if image_url:
            embed.set_thumbnail(url=image_url)
            
        return embed

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.data or "custom_id" not in interaction.data: return
        
        custom_id = interaction.data["custom_id"]
        db = SessionLocal()
        try:
            state = db.query(ServerState).filter_by(guild_id=str(interaction.guild.id)).first()

            if state and state.game_message_id and interaction.message.id != state.game_message_id:
                if not custom_id.startswith(("phone_", "shop_buy_", "ubereats_buy_")):
                    return

            if custom_id.startswith(("phone_", "shop_buy_", "ubereats_buy_")):
                player = db.query(PlayerProfile).filter_by(guild_id=str(interaction.guild.id)).first()
                if not player:
                    try: await interaction.response.send_message("Erreur: Profil du joueur introuvable.", ephemeral=True)
                    except discord.errors.InteractionResponded: pass
                    return
                phone_cog = self.bot.get_cog("Phone")
                if phone_cog: await phone_cog.handle_interaction(interaction, db, player, state, self)
                return

            player = db.query(PlayerProfile).filter_by(guild_id=str(interaction.guild.id)).first()
            if not player:
                try: await interaction.response.send_message("Erreur: Profil ou état introuvable.", ephemeral=True)
                except discord.errors.InteractionResponded: pass
                return

            await interaction.response.defer()

            if custom_id == "nav_toggle_stats":
                player.show_stats_in_view = not player.show_stats_in_view
                db.commit()
                new_embed = self.generate_dashboard_embed(player, state, interaction.guild)
                new_view = DashboardView(player)
                await interaction.edit_original_response(embed=new_embed, view=new_view)
                return

            if custom_id == "nav_main_menu":
                view = DashboardView(player)
                await interaction.edit_original_response(embed=self.generate_dashboard_embed(player, state, interaction.guild), view=view)
                return
            elif custom_id == "nav_actions":
                await interaction.edit_original_response(view=ActionsView(player))
                return
            elif custom_id == "nav_inventory":
                await interaction.edit_original_response(embed=self.generate_inventory_embed(player, interaction.guild), view=InventoryView())
                return

            action_menus = {
                "action_eat_menu": EatView(player),
                "action_drink_menu": DrinkView(player),
                "action_smoke_menu": SmokeView(player),
            }
            if custom_id in action_menus:
                await interaction.edit_original_response(view=action_menus[custom_id])
                return

            cooker_brain = self.bot.get_cog("CookerBrain")
            message = None
            action_map = {
                "action_sleep": cooker_brain.perform_sleep,
                "action_shower": cooker_brain.perform_shower,
                "action_urinate": cooker_brain.perform_urinate,
                "action_defecate": cooker_brain.perform_defecate, # NOUVELLE ACTION MAPPÉE
                "drink_water": cooker_brain.perform_drink_water,
                "drink_soda": cooker_brain.use_soda,
                "eat_sandwich": cooker_brain.perform_eat_sandwich,
                "eat_tacos": cooker_brain.use_tacos,
                "eat_salad": cooker_brain.use_salad,
                "smoke_cigarette": cooker_brain.perform_smoke_cigarette,
                "smoke_ecigarette": cooker_brain.use_ecigarette,
            }
            if custom_id in action_map:
                message, _ = action_map[custom_id](player)

            if message:
                player.last_action_at = datetime.datetime.utcnow()
                db.commit()
                await interaction.followup.send(f"✅ {message}", ephemeral=True)
                
                # After an action, show the updated actions view, not the main menu
                await interaction.edit_original_response(
                    embed=self.generate_dashboard_embed(player, state, interaction.guild),
                    view=ActionsView(player)
                )

        except Exception as e:
            print(f"Erreur critique dans le listener on_interaction: {e}")
            traceback.print_exc()
            db.rollback()
        finally:
            db.close()

async def setup(bot):
    cog = MainEmbed(bot)
    await bot.add_cog(cog)