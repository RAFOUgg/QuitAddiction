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
from utils.helpers import clamp
from utils.logger import get_logger
from utils.time_manager import get_current_game_time, is_night, is_work_time, is_lunch_break, to_localized, get_utc_now
logger = get_logger(__name__)

# --- Sleep quota helper ---
def get_sleep_quota(player: PlayerProfile) -> float:
    # Example: base quota + penalty for low health/sanity, bonus for high willpower
    base_quota = 7.0  # hours
    penalty = 0
    if player.health < 50: penalty += 1
    if player.sanity < 50: penalty += 1
    if player.fatigue > 80: penalty += 1
    bonus = 0
    if player.willpower > 80: bonus += 0.5
    return max(5.0, base_quota + penalty - bonus)

def generate_progress_bar(value: float, max_value: float = 100.0, length: int = 5, high_is_bad: bool = False) -> str:
    if not isinstance(value, (int, float)): value = 0.0
    value = clamp(value, 0, max_value)
    filled_blocks = round((value / max_value) * length)
    percent = value / max_value
    bar_filled = '🟥' if (high_is_bad and percent > 0.75) or (not high_is_bad and percent < 0.25) else '🟧' if (high_is_bad and percent > 0.5) or (not high_is_bad and percent < 0.5) else '🟩'
    bar_empty = '⬛'
    return f"{bar_filled * filled_blocks}{bar_empty * (length - filled_blocks)}"

class DashboardView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=None)
        now = datetime.datetime.utcnow()
        is_on_cooldown = player.action_cooldown_end_time and now < player.action_cooldown_end_time
        # Le téléphone est désactivé au travail, sauf pendant une pause.
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

class ActionsView(ui.View):
    def __init__(self, player: PlayerProfile, server_state: ServerState):
        super().__init__(timeout=None)
        now = datetime.datetime.utcnow()
        self.add_item(ui.Button(label="Retour", style=discord.ButtonStyle.grey, custom_id="nav_main_menu", row=2, emoji="⬅️"))

        if player.action_cooldown_end_time and now < player.action_cooldown_end_time:
            remaining_seconds = int((player.action_cooldown_end_time - now).total_seconds())
            self.add_item(ui.Button(label=f"Occupé pour {remaining_seconds}s...", style=discord.ButtonStyle.secondary, disabled=True, row=0, emoji="⏳"))
        elif player.is_working:
            if player.willpower <= 25:  # Only show drink button if willpower is low
                self.add_item(ui.Button(label="Boire", style=discord.ButtonStyle.primary, custom_id="action_drink_menu", emoji="💧"))
            if player.bladder > 30: self.add_item(ui.Button(label=f"Uriner ({player.bladder:.0f}%)", style=discord.ButtonStyle.danger if player.bladder > 80 else discord.ButtonStyle.blurple, custom_id="action_urinate", emoji="🚽"))
            if player.bowels > 40: self.add_item(ui.Button(label=f"Déféquer ({player.bowels:.0f}%)", style=discord.ButtonStyle.danger if player.bowels > 80 else discord.ButtonStyle.blurple, custom_id="action_defecate", emoji="💩"))
            
            # Show smoke break button only if not on break
            if not player.is_on_break:
                self.add_item(ui.Button(label="Prendre une pause", style=discord.ButtonStyle.secondary, custom_id="action_take_smoke_break", emoji="🚬"))
            # When on break, show available smoke options
            elif player.is_on_break:
                if player.cigarettes > 0: self.add_item(ui.Button(label=f"Cigarette ({player.cigarettes})", emoji="🚬", style=discord.ButtonStyle.danger, custom_id="smoke_cigarette"))
                if player.e_cigarettes > 0: self.add_item(ui.Button(label=f"Vapoteuse ({player.e_cigarettes})", emoji="💨", style=discord.ButtonStyle.primary, custom_id="smoke_ecigarette"))
                if getattr(player, 'joints', 0) > 0: self.add_item(ui.Button(label=f"Joint ({player.joints})", emoji="🌿", style=discord.ButtonStyle.success, custom_id="smoke_joint"))

            game_time = get_current_game_time(server_state)
            if is_lunch_break(game_time) or not is_work_time(game_time):
                self.add_item(ui.Button(label="Rentrer à la maison", style=discord.ButtonStyle.success, custom_id="action_go_home", emoji="🏠"))
        else:
            game_time = get_current_game_time(server_state)
            if is_work_time(game_time):
                self.add_item(ui.Button(label="Aller au travail", style=discord.ButtonStyle.success, custom_id="action_go_to_work", emoji="🏢"))
            
            self.add_item(ui.Button(label="Manger", style=discord.ButtonStyle.success, custom_id="action_eat_menu", emoji="🍽️"))
            self.add_item(ui.Button(label="Boire", style=discord.ButtonStyle.primary, custom_id="action_drink_menu", emoji="💧"))
            self.add_item(ui.Button(label="Fumer", style=discord.ButtonStyle.danger, custom_id="action_smoke_menu", emoji="🚬"))
            night_time = is_night(game_time)
            if night_time:
                self.add_item(ui.Button(label="Dormir (Nuit)", style=discord.ButtonStyle.secondary, custom_id="action_sleep", emoji="🛏️"))
            else:
                can_nap = player.fatigue > 60
                self.add_item(ui.Button(label="Faire une sieste", style=discord.ButtonStyle.secondary, custom_id="action_sleep", emoji="😴", disabled=not can_nap))
            if player.hygiene < 40: self.add_item(ui.Button(label="Prendre une douche", style=discord.ButtonStyle.blurple, custom_id="action_shower", emoji="🚿", row=1))
            if player.bladder > 30: self.add_item(ui.Button(label=f"Uriner ({player.bladder:.0f}%)", style=discord.ButtonStyle.danger if player.bladder > 80 else discord.ButtonStyle.blurple, custom_id="action_urinate", emoji="🚽", row=1))
            if player.bowels > 40: self.add_item(ui.Button(label=f"Déféquer ({player.bowels:.0f}%)", style=discord.ButtonStyle.danger if player.bowels > 80 else discord.ButtonStyle.blurple, custom_id="action_defecate", emoji="💩", row=1))

class ScheduleButton(ui.Button):
    def __init__(self):
        super().__init__(
            label="📅 Emploi du temps",
            style=discord.ButtonStyle.secondary,
            custom_id="show_schedule",
            row=1
        )

    async def callback(self, interaction: discord.Interaction):
        from cogs.main_embed import get_dashboard_view
        db = SessionLocal()
        try:
            player = db.query(PlayerProfile).filter_by(guild_id=str(interaction.guild_id)).first()
            state = db.query(ServerState).filter_by(guild_id=str(interaction.guild_id)).first()
            if not player or not state:
                await interaction.response.send_message("Erreur : Profil ou état du jeu introuvable.", ephemeral=True)
                return

            # Basculer l'affichage de l'emploi du temps
            player.show_schedule_in_view = not getattr(player, 'show_schedule_in_view', False)
            # Désactiver les autres vues si on active l'emploi du temps
            if player.show_schedule_in_view:
                player.show_inventory_in_view = False
                player.show_stats_in_view = False
            db.commit()

            # Mettre à jour l'affichage
            self.label = "📅 Masquer l'emploi du temps" if player.show_schedule_in_view else "📅 Emploi du temps"
            await interaction.message.edit(
                embed=get_dashboard_view().generate_dashboard_embed(player, state, interaction.guild),
                view=DashboardView(player)
            )
            await interaction.response.defer()
            
        except Exception as e:
            print(f"Erreur dans ScheduleButton callback: {e}")
            await interaction.response.send_message("Une erreur est survenue.", ephemeral=True)
        finally:
            db.close()

class WorkView(ui.View):
    def __init__(self, player: PlayerProfile, server_state: ServerState):
        super().__init__(timeout=None)
        current_weekday = server_state.game_start_time.weekday() if server_state.game_start_time else -1
        
        # Jours de repos (Dimanche et Lundi)
        if current_weekday in [0, 6]:
            self.add_item(ui.Button(
                label="🏃‍♂️ Faire du sport",
                custom_id="action_do_sport",
                style=discord.ButtonStyle.success
            ))
        else:
            self.add_item(ui.Button(
                label="🏃 Aller au travail",
                custom_id="action_go_to_work",
                style=discord.ButtonStyle.primary
            ))
            self.add_item(ui.Button(
                label="🏠 Rentrer",
                custom_id="action_go_home",
                style=discord.ButtonStyle.danger
            ))
            self.add_item(ui.Button(
                label="☕ Pause",
                custom_id="action_take_smoke_break",
                style=discord.ButtonStyle.secondary
            ))
        
        self.add_item(ui.Button(label="Retour", style=discord.ButtonStyle.grey, custom_id="nav_main_menu", emoji="⬅️"))

class EatView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=60)
        if player.food_servings > 0: self.add_item(ui.Button(label=f"Sandwich ({player.food_servings})", emoji="🥪", style=discord.ButtonStyle.success, custom_id="eat_sandwich"))
        if getattr(player, 'tacos', 0) > 0: self.add_item(ui.Button(label=f"Tacos ({player.tacos})", emoji="🌮", style=discord.ButtonStyle.primary, custom_id="eat_tacos"))
        if getattr(player, 'salad_servings', 0) > 0: self.add_item(ui.Button(label=f"Salade ({player.salad_servings})", emoji="🥗", style=discord.ButtonStyle.success, custom_id="eat_salad"))
        self.add_item(ui.Button(label="Retour", style=discord.ButtonStyle.grey, custom_id="nav_actions", row=1, emoji="⬅️"))

class DrinkView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=None)
        if player.water_bottles > 0: self.add_item(ui.Button(label=f"Eau ({player.water_bottles})", emoji="💧", style=discord.ButtonStyle.primary, custom_id="drink_water"))
        if player.soda_cans > 0: self.add_item(ui.Button(label=f"Soda ({player.soda_cans})", emoji="🥤", style=discord.ButtonStyle.blurple, custom_id="drink_soda"))
        if player.wine_bottles > 0: self.add_item(ui.Button(label=f"Vin ({player.wine_bottles})", emoji="🍷", style=discord.ButtonStyle.danger, custom_id="drink_wine"))
        self.add_item(ui.Button(label="Retour", style=discord.ButtonStyle.grey, custom_id="nav_actions", row=1, emoji="⬅️"))

class SmokeView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=None)
        if player.cigarettes > 0: self.add_item(ui.Button(label=f"Cigarette ({player.cigarettes})", emoji="🚬", style=discord.ButtonStyle.danger, custom_id="smoke_cigarette"))
        if player.e_cigarettes > 0: self.add_item(ui.Button(label=f"Vapoteuse ({player.e_cigarettes})", emoji="💨", style=discord.ButtonStyle.primary, custom_id="smoke_ecigarette"))
        if player.joints > 0: self.add_item(ui.Button(label=f"Joint ({player.joints})", emoji="🌿", style=discord.ButtonStyle.secondary, custom_id="smoke_joint"))
        if player.has_bong: self.add_item(ui.Button(label="Utiliser le bong", emoji="🌊", style=discord.ButtonStyle.secondary, custom_id="use_bong"))
        self.add_item(ui.Button(label="Retour", style=discord.ButtonStyle.grey, custom_id="nav_actions", row=1, emoji="⬅️"))

class MainEmbed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def force_refresh_on_cooldown_end(self, interaction: discord.Interaction, duration: int):
        await asyncio.sleep(duration + 1)
        db = SessionLocal()
        try:
            player = db.query(PlayerProfile).filter_by(guild_id=str(interaction.guild.id)).first()
            state = db.query(ServerState).filter_by(guild_id=str(interaction.guild.id)).first()
            if not player or not state or not interaction.message: return
            if player.action_cooldown_end_time and datetime.datetime.utcnow() > player.action_cooldown_end_time:
                try:
                    game_message = await interaction.channel.fetch_message(state.game_message_id)
                    view = ActionsView(player, state) if player.is_working else DashboardView(player)
                    await game_message.edit(embed=self.generate_dashboard_embed(player, state, interaction.guild), view=view)
                except (discord.NotFound, discord.Forbidden): pass
        finally:
            db.close()

    # --- Willpower automation ---
    async def willpower_auto_actions(self, player, state, cooker_brain, db, interaction):
        # Only auto-perform if willpower > 70 and not on cooldown
        now = datetime.datetime.utcnow()
        if player.action_cooldown_end_time and now < player.action_cooldown_end_time:
            return False
        if player.willpower <= 70:
            return False
        # Only for eat, drink, sleep, go to work
        game_time = get_current_game_time(state)
        auto_performed = False
        # Eat if hunger > 70
        if player.hunger > 70 and player.food_servings > 0:
            message, _, duration = cooker_brain.perform_eat_food(player)
            if duration > 0:
                player.action_cooldown_end_time = now + datetime.timedelta(seconds=duration)
                self.bot.loop.create_task(self.force_refresh_on_cooldown_end(interaction, duration))
            auto_performed = True
        # Drink if thirst > 70
        elif player.thirst > 70 and player.water_bottles > 0:
            message, _, duration = cooker_brain.perform_drink_water(player)
            if duration > 0:
                player.action_cooldown_end_time = now + datetime.timedelta(seconds=duration)
                self.bot.loop.create_task(self.force_refresh_on_cooldown_end(interaction, duration))
            auto_performed = True
        # Sleep if fatigue > 80 and not working
        elif player.fatigue > 80 and not player.is_working and is_night(game_time):
            message, _, duration, *_ = cooker_brain.perform_sleep(player, game_time)
            if duration > 0:
                player.action_cooldown_end_time = now + datetime.timedelta(seconds=duration)
                self.bot.loop.create_task(self.force_refresh_on_cooldown_end(interaction, duration))
            auto_performed = True
        # Go to work if work time and not working
        elif is_work_time(game_time) and not player.is_working:
            message, _, duration, *_ = cooker_brain.perform_go_to_work(player, game_time)
            if duration > 0:
                player.action_cooldown_end_time = now + datetime.timedelta(seconds=duration)
                self.bot.loop.create_task(self.force_refresh_on_cooldown_end(interaction, duration))
            auto_performed = True
        if auto_performed:
            db.commit()
        return auto_performed

    def get_image_url(self, player: PlayerProfile) -> str | None:
        asset_cog = self.bot.get_cog("AssetManager")
        now = datetime.datetime.utcnow()
        if not asset_cog:
            return None

        # If the asset cache is empty, attempt to initialize it (non-blocking)
        if not getattr(asset_cog, 'asset_urls', None):
            try:
                # schedule initialization in background
                self.bot.loop.create_task(asset_cog.initialize_assets())
            except Exception:
                pass

        # Actions immédiates (cooldown ou action récente)
        is_on_cooldown = player.action_cooldown_end_time and now < player.action_cooldown_end_time
        
        # Vérifier si le joueur vient de se réveiller
        just_woke_up = (player.last_action == "action_sleep" and 
                       player.last_action_time and 
                       (now - player.last_action_time).total_seconds() < 5)
        
        if just_woke_up:
            return asset_cog.get_url("waking_up") or asset_cog.get_url("neutral")
            
        if player.last_action and player.last_action_time and ((now - player.last_action_time).total_seconds() < 2 or is_on_cooldown):
            # Mapping complet des actions et états vers les images
            action_to_asset = {
                # États de base
                "neutral": "neutral",                      # État neutre par défaut
                "sad": "sad",                             # État triste
                "sob": "sob",                             # État très triste/désespéré
                "confused": "confused",                    # État confus/perdu
                "waking_up": "waking_up",                 # État au réveil
                
                # Actions de repas
                "eat_sandwich": "eat_sandwich",           # Action de manger un sandwich
                "eat_tacos": "eat_tacos",                 # Action de manger des tacos
                "eat_salad": "eat_salad",                 # Action de manger une salade
                "hand_stomach": "hand_stomach",           # État d'avoir mal au ventre
                "hungry": "hungry",                       # État d'avoir faim
                
                # Actions de boisson
                "drink_water": "drink_water",             # Action de boire de l'eau
                "drink_soda": "drink_soda",               # Action de boire un soda
                "drink_wine": "drink_wine",               # Action de boire du vin
                "sad_drinking": "sad_drinking",           # Action de boire tristement
                "job_drinking": "job_drinking",           # Action de boire au travail
                
                # Actions de consommation de substances
                "smoke_cigarette": "smoke_cigarette",     # Action de fumer une cigarette
                "smoke_ecigarette": "smoke_ecigarette",   # Action de vapoter
                "smoke_joint": "smoke_joint",             # Action de fumer un joint
                "smoke_bang": "smoke_bang",               # Action d'utiliser le bang
                "rolling": "rolling",                     # Action de rouler
                "neutral_hold_e_cig": "neutral_hold_e_cig", # État tenant une e-cig
                "job_smoke_cig": "job_pause_cig",         # Action de fumer une cigarette au travail
                "job_smoke_joint": "job_pause_joint",     # Action de fumer un joint au travail
                
                # Actions physiologiques
                "sleep": "sleep",                         # Action de dormir
                "shower": "shower",                       # Action de se doucher
                "pooping": "pooping",                     # Action d'aller aux toilettes
                "need_pee": "need_pee",                   # État d'avoir envie
                "peed": "peed",                          # État après avoir uriné
                
                # États de santé/confort
                "scratch_eye": "scratch_eye",             # Action de se gratter les yeux (fatigue)
                "sporting": "sporting",                   # Action de faire du sport
                
                # Actions liées au travail
                "working": "working",                     # État de travail normal
                "leaving_for_work": "leaving_for_work",   # Action d'aller au travail
                "job_hungry": "job_hungry",               # État d'avoir faim au travail
                "job_pooping": "job_pooping",             # État d'avoir envie au travail
                
                # Activités diverses
                "on_phone": "on_phone",                   # Action d'être au téléphone

                # Mappings d'actions vers les états
                "neutral_eat_sandwich": "eat_sandwich",
                "neutral_eat_tacos": "eat_tacos",
                "neutral_eat_salad": "eat_salad",
                "neutral_drinking": "drink_water",
                "neutral_drinking_soda": "drink_soda",
                "neutral_drink_wine": "drink_wine",
                "neutral_smoke_cig": "smoke_cigarette",
                "neutral_smoke_joint": "smoke_joint",
                "vape_e_cig": "smoke_ecigarette",
                "neutral_shower": "shower",
                "neutral_sleep": "sleep",
                "action_urinate": "pooping",
                "neutral_pooping": "pooping",
                "jobbing": "leaving_for_work",
                "work_break_cig": "job_pause_cig",
                "work_break_joint": "job_pause_joint",
                "pause": "job_pause_cig",
                "action_go_to_work": "leaving_for_work"
            }
            asset_name = action_to_asset.get(player.last_action, player.last_action)
            return asset_cog.get_url(asset_name) or asset_cog.get_url("neutral")

        # États de travail
        if player.is_working:
            # Priorité aux besoins physiologiques urgents pendant le travail
            if player.bowels > 70 or player.bladder > 70:
                return asset_cog.get_url("job_pooping") or asset_cog.get_url("working")
            if player.hunger > 60 or player.thirst > 70 or player.stomachache > 50:
                return asset_cog.get_url("job_hungry") or asset_cog.get_url("working")

            # Ensuite gestion des pauses et actions au travail
            if player.is_on_break:
                # Vérifier les actions spécifiques pendant la pause
                if player.last_action in ("smoke_cigarette", "work_break_cig", "job_pause_cig", "action_take_smoke_break"):
                    return asset_cog.get_url("job_pause_cig") or asset_cog.get_url("working")
                elif player.last_action in ("smoke_joint", "work_break_joint", "job_pause_joint"):
                    return asset_cog.get_url("job_pause_joint") or asset_cog.get_url("working")
                elif player.last_action in ("drink_water", "drink_soda"):
                    return asset_cog.get_url("job_drinking") or asset_cog.get_url("working")
            else:
                # Vérifier les actions spécifiques pendant le travail
                if player.last_action in ("drink_water", "drink_soda"):
                    return asset_cog.get_url("job_drinking") or asset_cog.get_url("working")
                return asset_cog.get_url("working")

        # Départ au travail
        if player.last_action in ("jobbing", "action_go_to_work"):
            return asset_cog.get_url("leaving_for_work") or asset_cog.get_url("working")

        # États critiques physiologiques/mentaux
        if player.bladder >= 99:
            return asset_cog.get_url("peed") or asset_cog.get_url("neutral")
        if player.happiness < 10 and player.stress > 80:
            return asset_cog.get_url("sob") or asset_cog.get_url("neutral")
        if player.bowels > 85 or player.bladder > 85:
            return asset_cog.get_url("need_pee") or asset_cog.get_url("pooping") or asset_cog.get_url("neutral")
        if player.hunger > 85 or player.stomachache > 70:
            return asset_cog.get_url("hand_stomach") or asset_cog.get_url("hungry") or asset_cog.get_url("neutral")
        if player.fatigue > 90:
            return asset_cog.get_url("sleep") or asset_cog.get_url("neutral")
        if player.withdrawal_severity > 60:
            return asset_cog.get_url("neutral_hold_e_cig") or asset_cog.get_url("smoke_ecigarette") or asset_cog.get_url("neutral")
        if player.headache > 70:
            return asset_cog.get_url("scratch_eye") or asset_cog.get_url("neutral")
        if player.sanity < 40:
            return asset_cog.get_url("confused") or asset_cog.get_url("neutral")
        if player.stress > 70 or player.health < 40:
            return asset_cog.get_url("sad") or asset_cog.get_url("neutral")
        if player.hygiene < 20:
            return asset_cog.get_url("shower") or asset_cog.get_url("neutral")

        # Par défaut
        return asset_cog.get_url("neutral")

    @staticmethod
    def get_character_thoughts(player: PlayerProfile) -> str:
        if player.is_working:
            return "Au travail... il faut bien gagner sa vie."
        if player.hunger > 70 and player.stress > 60: return "J'ai l'estomac dans les talons et les nerfs à vif. Un rien pourrait me faire craquer."
        if player.withdrawal_severity > 60 and player.health < 40: return "Chaque partie de mon corps me fait souffrir. Le manque me ronge de l'intérieur, je suis à bout."
        if player.fatigue > 80 and player.boredom > 70: return "Je suis épuisé, mais je m'ennuie tellement que je n'arrive même pas à fermer l'œil."
        thoughts = { 95: (player.thirst > 85, "J'ai la gorge complètement sèche..."), 90: (player.hunger > 80, "Mon estomac gargouille si fort..."), 85: (player.withdrawal_severity > 60, "Ça tremble... il m'en faut une, vite."), 80: (player.fatigue > 85, "Mes paupières sont lourdes..."), 75: (player.bladder > 90, "J'ai une envie TRÈS pressante !"), 70: (player.stress > 70, "J'ai les nerfs à vif..."), 60: (player.hygiene < 20, "Je me sens vraiment sale..."), 50: (player.craving_nicotine > 40, "Une clope me calmerait, là."), 40: (player.health < 40, "Je... je ne me sens pas bien."), 30: (player.boredom > 60, "Je m'ennuie..."), 20: (player.craving_alcohol > 50, "Un verre me détendrait bien..."), }
        for priority in sorted(thoughts.keys(), reverse=True):
            if thoughts[priority][0]: return thoughts[priority][1]
        return "Pour l'instant, ça va à peu près."

    def generate_dashboard_embed(self, player: PlayerProfile, state: ServerState, guild: discord.Guild) -> discord.Embed:
        """Create the main dashboard embed, using the centralized time manager."""
        # Basic mode labels
        game_mode = state.game_mode.capitalize() if state.game_mode else "Normal"
        duration_key = state.duration_key or "real_time"
        duration_label = "Test Mode" if duration_key == "test" else "Temps Réel"

        # Get localized times for display
        localized_start = to_localized(state.game_start_time) if state.game_start_time else None
        start_time = localized_start.strftime('%H:%M') if localized_start else "??:??"
        game_time = get_current_game_time(state)
        current_game_time_str = game_time.strftime('%H:%M')

        embed = discord.Embed(title="👨‍🍳 Le Quotidien du Cuisinier", color=0x3498db)

        # Image selection
        if image_url := self.get_image_url(player):
            embed.set_image(url=image_url)

        embed.description = f"""**Pensées du Cuisinier :**
*"{self.get_character_thoughts(player)}"*"""

        # Inventory view
        if getattr(player, 'show_inventory_in_view', False):
            inventory_items = [
                ("food_servings", "🥪 Sandwichs"), ("tacos", "🌮 Tacos"), ("salad_servings", "🥗 Salades"),
                ("water_bottles", "💧 Eaux"), ("soda_cans", "🥤 Sodas"), ("wine_bottles", "🍷 Vins"),
                ("cigarettes", "🚬 Cigarettes"), ("e_cigarettes", "💨 Vapoteuses"), ("joints", "🌿 Joints")
            ]
            inventory_list = [f"{label}: **{getattr(player, attr, 0)}**" for attr, label in inventory_items if getattr(player, attr, 0) > 0]
            if inventory_list:
                mid_point = len(inventory_list) // 2 + (len(inventory_list) % 2)
                col1 = "\n".join(inventory_list[:mid_point])
                col2 = "\n".join(inventory_list[mid_point:])
                embed.add_field(name="🎒 Inventaire", value=col1, inline=True)
                if col2:
                    embed.add_field(name="", value=col2, inline=True)
            else:
                embed.add_field(name="🎒 Inventaire", value="*Vide*", inline=True)
            embed.add_field(name="💰 Argent", value=f"**{getattr(player, 'wallet', 0)}$**", inline=False)

        # Schedule view
        if getattr(player, 'show_schedule_in_view', False):
            schedule = """🔵 **Heures de travail:**
• Matin: 9h00 - 11h30
• Après-midi: 13h00 - 17h30

📆 **Jours travaillés:**
• Mardi: ✅
• Mercredi: ✅
• Jeudi: ✅
• Vendredi: ✅
• Samedi: ✅
• Dimanche: ❌ REPOS
• Lundi: ❌ REPOS

💡 Note: Les retards sont sanctionnés."""
            embed.add_field(name="📅 Emploi du temps", value=schedule, inline=False)

        # Stats view
        if getattr(player, 'show_stats_in_view', False):
            def stat_value_and_bar(value: float, high_is_bad: bool):
                return f"`{int(value)}%`\n{generate_progress_bar(value, high_is_bad=high_is_bad)}"

            embed.add_field(name="**🧬 Physique & Besoins**", value="", inline=True)
            embed.add_field(name="**🧠 Mental & Émotions**", value="", inline=True)
            embed.add_field(name="**🚬 Addiction & Symptômes**", value="", inline=True)

            stats_layout = [
                [('Santé', getattr(player, 'health', 0), False), ('Humeur', getattr(player, 'happiness', 0), False), ('Dépendance', getattr(player, 'substance_addiction_level', 0), True)],
                [('Énergie', getattr(player, 'energy', 0), False), ('Stress', getattr(player, 'stress', 0), True), ('Sevrage', getattr(player, 'withdrawal_severity', 0), True)],
                [('Hygiène', getattr(player, 'hygiene', 0), False), ('Volonté', getattr(player, 'willpower', 0), False), ('Envie', max(getattr(player, 'craving_nicotine', 0), getattr(player, 'craving_alcohol', 0), getattr(player, 'craving_cannabis', 0)), True)],
                [('Fatigue', getattr(player, 'fatigue', 0), True), ('S. Mentale', getattr(player, 'sanity', 0), False), ('Toxine', getattr(player, 'tox', 0), True)],
                [('Faim', getattr(player, 'hunger', 0), True), ('Culpabilité', getattr(player, 'guilt', 0), True), ('Douleur', getattr(player, 'pain', 0), True)],
                [('Soif', getattr(player, 'thirst', 0), True), ('Ennui', getattr(player, 'boredom', 0), True), ('Nausée', getattr(player, 'nausea', 0), True)],
            ]

            for row in stats_layout:
                for name, val, bad in row:
                    embed.add_field(name=name, value=stat_value_and_bar(val, bad), inline=True)

        # Timing footer and timestamp
        elapsed = datetime.datetime.utcnow() - state.game_start_time if state.game_start_time else datetime.timedelta()
        elapsed_mins = int(elapsed.total_seconds() / 60)
        embed.set_footer(text=f"LaFoncedalle.fr • Mode: {game_mode} ({duration_label}) • ⏰ {start_time} +{elapsed_mins}min • ⌚ {current_game_time_str}")
        embed.timestamp = get_utc_now()
        return embed

    def generate_work_embed(self, player: PlayerProfile, state: ServerState) -> discord.Embed:
        embed = discord.Embed(title="🏢 Informations sur le travail", color=0x71368a)
        if image_url := self.get_image_url(player):
            embed.set_image(url=image_url)
        embed.add_field(name="Horaires", value="9:00 - 11:30 / 13:00 - 17:30", inline=False)
        embed.add_field(name="Performance", value=f"`{int(player.job_performance)}%`\n{generate_progress_bar(player.job_performance, high_is_bad=False)}", inline=True)
        embed.add_field(name="Jours d'absence", value=player.missed_work_days, inline=True)
        return embed

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
            cooker_brain = self.bot.get_cog("CookerBrain")
            game_time = get_current_game_time(state) # Get current game time once for this interaction

            if custom_id.startswith("phone_") or custom_id.startswith("shop_buy_") or custom_id.startswith("ubereats_buy_"):
                phone_cog = self.bot.get_cog("Phone")
                await phone_cog.handle_interaction(interaction, db, player, state, self)
                return

            if not interaction.response.is_done(): await interaction.response.defer()

            # --- Willpower automation: before showing dashboard/actions, auto-perform if needed ---
            if custom_id in ["nav_toggle_stats", "nav_toggle_inventory", "nav_main_menu", "nav_actions"]:
                await self.willpower_auto_actions(player, state, cooker_brain, db, interaction)

            view = None
            embed = None
            if custom_id in ["nav_toggle_stats", "nav_toggle_inventory", "nav_main_menu"]:
                if custom_id == "nav_toggle_stats": player.show_stats_in_view = not player.show_stats_in_view
                elif custom_id == "nav_toggle_inventory": player.show_inventory_in_view = not player.show_inventory_in_view
                view = DashboardView(player)
            elif custom_id == "nav_actions":
                view = ActionsView(player, state)
            elif custom_id == "nav_work":
                view = WorkView(player, state)
                embed = self.generate_work_embed(player, state)
            elif custom_id in ["action_eat_menu", "action_drink_menu", "action_smoke_menu"]:
                views = {"action_eat_menu": EatView, "action_drink_menu": DrinkView, "action_smoke_menu": SmokeView}
                view = views[custom_id](player)
            else: 
                action_map = { 
                    "action_do_sport": cooker_brain.perform_sport,
                    "drink_wine": cooker_brain.perform_drink_wine, 
                    "smoke_joint": cooker_brain.perform_smoke_joint, 
                    "action_sleep": cooker_brain.perform_sleep, 
                    "action_shower": cooker_brain.perform_shower, 
                    "action_urinate": cooker_brain.perform_urinate, 
                    "action_defecate": cooker_brain.perform_defecate, 
                    "drink_water": cooker_brain.perform_drink_water, 
                    "drink_soda": cooker_brain.perform_drink_water,  # Pour l'instant utiliser drink_water 
                    "eat_sandwich": cooker_brain.perform_eat_food,
                    "eat_tacos": cooker_brain.perform_eat_food,     # Pour l'instant utiliser perform_eat_food
                    "eat_salad": cooker_brain.perform_eat_food,     # Pour l'instant utiliser perform_eat_food
                    "smoke_cigarette": cooker_brain.perform_smoke_cigarette, 
                    "smoke_ecigarette": cooker_brain.perform_smoke_cigarette, # Pour l'instant utiliser smoke_cigarette
                    "action_go_to_work": cooker_brain.perform_go_to_work,
                    "action_go_home": cooker_brain.perform_go_home,
                    "action_take_smoke_break": cooker_brain.perform_take_smoke_break,
                    "action_end_smoke_break": cooker_brain.perform_end_smoke_break
                }
                if custom_id in action_map:
                    # Correction: Gère tous les retours d'action correctement
                    if custom_id in ["action_sleep", "action_go_to_work", "action_go_home", "action_do_sport"]:
                        result = action_map[custom_id](player, game_time)
                        if isinstance(result, tuple) and len(result) >= 3:
                            message, states, duration, *_ = result
                        else:
                            message, states, duration = result
                    else:
                        message, states, duration = action_map[custom_id](player)

                    # Record last action + timestamp and states for image display
                    player.last_action = custom_id
                    player.last_action_time = datetime.datetime.utcnow()
                    # Store the states for image selection
                    if isinstance(states, dict):
                        player.current_state = next(iter(states))  # Get the first state key

                    if duration > 0:
                        player.action_cooldown_end_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=duration)
                        self.bot.loop.create_task(self.force_refresh_on_cooldown_end(interaction, duration))
                        await interaction.followup.send(f"✅ {message}", ephemeral=True)
                    else:
                        await interaction.followup.send(f"⚠️ {message}", ephemeral=True)
                
                # Correction: Affiche la bonne vue après chaque action
                if player.is_working:
                    view = ActionsView(player, state)
                else:
                    view = DashboardView(player)

            db.commit()
            if embed is None:
                embed = self.generate_dashboard_embed(player, state, interaction.guild)
            await interaction.edit_original_response(embed=embed, view=view)

        except Exception as e:
            logger.error(f"Erreur critique dans on_interaction: {e}", exc_info=True)
            if not interaction.response.is_done():
                try: await interaction.followup.send("Une erreur est survenue.", ephemeral=True)
                except: pass
            db.rollback()
        finally:
            if db.is_active: db.close()

async def setup(bot):
    await bot.add_cog(MainEmbed(bot))