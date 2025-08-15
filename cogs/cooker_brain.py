# --- cogs/cooker_brain.py (REWORKED WITH NEW STATS & EFFECTS) ---
from discord.ext import commands
from typing import Tuple, Dict, Optional
import datetime
from db.models import PlayerProfile, ServerState
from utils.helpers import clamp
from utils.game_time import is_night, get_current_game_time, is_work_time, is_lunch_break
from functools import wraps

def get_attr_int(player: PlayerProfile, attr: str) -> int:
    """Helper function to safely get integer attribute values"""
    value = getattr(player, attr)
    return int(value) if value is not None else 0

def get_attr_float(player: PlayerProfile, attr: str) -> float:
    """Helper function to safely get float attribute values"""
    value = getattr(player, attr)
    return float(value) if value is not None else 0.0

def get_attr_bool(player: PlayerProfile, attr: str) -> bool:
    """Helper function to safely get boolean attribute values"""
    value = getattr(player, attr)
    return bool(value) if value is not None else False

def set_attr_int(player: PlayerProfile, attr: str, value: int) -> None:
    """Helper function to safely set integer attribute values"""
    try:
        setattr(player, attr, value)
    except (ValueError, TypeError):
        setattr(player, attr, 0)  # Default to 0 if there's an error

def check_inventory(player: PlayerProfile) -> dict:
    """Helper function to safely get inventory values"""
    return {
        'weed_grams': get_attr_int(player, 'weed_grams'),
        'hash_grams': get_attr_int(player, 'hash_grams'),
        'has_bong': get_attr_bool(player, 'has_bong'),
        'bong_uses': get_attr_int(player, 'bong_uses'),
    }

def check_not_working(func):
    @wraps(func)
    def wrapper(self, player: PlayerProfile, *args, **kwargs):
        if player.is_working:
            return "Vous ne pouvez pas faire ça pendant le travail !", {"confused": True}, 0
        return func(self, player, *args, **kwargs)
    return wrapper

class CookerBrain(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def perform_sport(self, player: PlayerProfile, server_state: ServerState) -> Tuple[str, Dict, int]:
        """
        Permet au joueur de faire du sport pendant ses jours de repos.
        Les avantages sont nombreux : santé physique et mentale, réduction de l'ennui.
        """
        if not server_state or not server_state.game_start_time:
            return "Erreur: La partie n'a pas encore commencé.", {"confused": True}, 0
            
        current_weekday = server_state.game_start_time.weekday()
        
        # Vérifier si c'est un jour de sport (dimanche ou lundi)
        if current_weekday not in [0, 6]:  # Lundi (0) ou Dimanche (6)
            return "🏃‍♂️ Le sport est réservé pour vos jours de repos (dimanche et lundi).", {"confused": True}, 0
            
        # Vérifier l'énergie
        if player.energy < 30:
            return "😫 Vous êtes trop fatigué pour faire du sport.", {"sob": True}, 0
            
        # Si la volonté est > 85%, le joueur peut s'auto-motiver
        can_self_motivate = player.willpower > 85
            
        # Vérifier qui initie l'action
        if not can_self_motivate and player.last_action_by == str(player.user_id):
            return "🏃‍♂️ Vous avez besoin de motivation ! Demandez à quelqu'un de vous accompagner.", {"confused": True}, 0

        # Appliquer les effets positifs
        player.energy = max(10, player.energy - 20)  # Fatigue mais pas trop
        player.physical_health = min(100, player.physical_health + 15)
        player.mental_health = min(100, player.mental_health + 10)
        player.stress = max(0, player.stress - 15)
        player.boredom = max(0, player.boredom - 25)
        player.willpower = min(100, player.willpower + 5)

        message = "🏃‍♂️ Excellente séance de sport ! Votre corps et votre esprit se sentent revigorés."
        if can_self_motivate:
            message += "\n💪 Votre forte volonté vous a permis de vous motiver seul !"
        else:
            message += "\n👥 L'encouragement des autres vous a aidé à vous dépasser !"
            
        return message, {"sporting": True}, 30  # 30 minutes de sport

    def perform_use_bong(self, player: PlayerProfile) -> Tuple[str, Dict, int]:
        """
        Utilise le bong pour consommer du cannabis.
        Impact plus fort qu'un joint mais consomme plus de produit.
        """
        inventory = check_inventory(player)
        
        if not inventory['has_bong']:
            return "🌊 Vous n'avez pas de bong.", {"confused": True}, 0
            
        weed_grams = get_attr_int(player, 'weed_grams')
        hash_grams = get_attr_int(player, 'hash_grams')
        
        if weed_grams < 1.5 and hash_grams < 1:
            return "🌊 Il vous faut au moins 1.5g de weed ou 1g de hash pour le bong.", {"confused": True}, 0
            
        # Utiliser weed en priorité, sinon hash
        if weed_grams >= 1.5:
            set_attr_int(player, 'weed_grams', max(0, int(weed_grams - 1.5)))
            substance = "weed"
        else:
            set_attr_int(player, 'hash_grams', max(0, hash_grams - 1))
            substance = "hash"
            
        # Effets plus forts qu'un joint
        intox = get_attr_float(player, 'intoxication_level')
        stress = get_attr_float(player, 'stress')
        mental = get_attr_float(player, 'mental_health')
        willpower = get_attr_float(player, 'willpower')
        bong_uses = get_attr_int(player, 'bong_uses')
        
        player.intoxication_level = min(100, intox + 40)
        player.stress = max(0, stress - 30)
        player.mental_health = max(0, mental - 15)
        player.willpower = max(0, willpower - 10)
        set_attr_int(player, 'bong_uses', bong_uses + 1)
        
        return f"🌊 Vous utilisez le bong avec du {substance}. L'effet est puissant !", {"smoke_bang": True}, 15

    def perform_go_to_work(self, player: PlayerProfile, server_state: ServerState) -> Tuple[str, Dict, int]:
        if not server_state or not server_state.game_start_time:
            return "Erreur: La partie n'a pas encore commencé.", {"confused": True}, 0
            
        current_time = get_current_game_time(server_state)
        current_weekday = server_state.game_start_time.weekday()

        # Vérifier si c'est un jour de repos
        if current_weekday in [0, 6]:  # Lundi (0) ou Dimanche (6)
            return "📅 C'est votre jour de repos ! Profitez-en pour faire du sport.", {"confused": True}, 0

        if not is_work_time(server_state):
            return "⏰ Les horaires de travail sont 9h-11h30 et 13h-17h30.", {"confused": True}, 0
            
        if player.is_working:
            return "👨‍🍳 Vous êtes déjà au travail !", {"confused": True}, 0

        if player.is_sleeping:
            return "😴 Vous ne pouvez pas aller travailler en dormant !", {"confused": True}, 0

        morning_start = datetime.time(hour=9, minute=0)
        afternoon_start = datetime.time(hour=13, minute=0)

        lateness = 0
        if morning_start <= current_time < datetime.time(hour=11, minute=30):
            lateness = (current_time.hour - morning_start.hour) * 60 + (current_time.minute - morning_start.minute)
        elif afternoon_start <= current_time < datetime.time(hour=17, minute=30):
            lateness = (current_time.hour - afternoon_start.hour) * 60 + (current_time.minute - afternoon_start.minute)

        if lateness > 5:
            # Pénalités pour retard
            player.performance = max(0, player.performance - lateness * 0.5)
            player.money = max(0, player.money - int(lateness * 2))  # 2$ par minute de retard
            msg = f"⏰ Vous arrivez en retard de {lateness} minutes ! (-{int(lateness * 2)}$)"
        else:
            msg = "👨‍🍳 Vous commencez votre journée de travail."

        player.is_working = True
        return msg, {"leaving_for_work": True}, 0

    def perform_go_home(self, player: PlayerProfile, server_state: ServerState) -> Tuple[str, Dict, int]:
        if not player.is_working:
            return "Vous n'êtes pas au travail.", {"confused": True}, 0

        if player.is_sleeping:
            return "😴 Impossible de rentrer en dormant !", {"confused": True}, 0

        current_time = get_current_game_time(server_state)
        if current_time < datetime.time(hour=11, minute=30) or (datetime.time(hour=13, minute=0) <= current_time < datetime.time(hour=17, minute=30)):
            player.performance = max(0, player.performance - 25)
            player.money = max(0, player.money - 50)
            msg = "🏃 Vous partez plus tôt ! (-50$, -25 performance)"
        else:
            msg = "🏠 Vous rentrez chez vous après une journée de travail."

        player.is_working = False
        return msg, {"neutral": True}, 0

    def perform_take_smoke_break(self, player: PlayerProfile) -> Tuple[str, Dict, int]:
        if not player.is_working:
            return "Vous n'êtes pas au travail.", {"confused": True}, 0

        if player.is_sleeping:
            return "😴 Impossible de faire une pause en dormant !", {"confused": True}, 0

        if player.is_on_break:
            return "Vous êtes déjà en pause.", {"confused": True}, 0

        player.is_on_break = True
        player.performance = max(0, player.performance - 5)  # Légère pénalité de performance
        return "☕ Vous prenez une pause.", {"job_pause_cig": True}, 0

    def perform_end_smoke_break(self, player: PlayerProfile) -> Tuple[str, Dict, int]:
        if not player.is_working:
            return "Vous n'êtes pas au travail.", {"confused": True}, 0

        if not player.is_on_break:
            return "Vous n'êtes pas en pause.", {"confused": True}, 0

        player.is_on_break = False
        return "👨‍🍳 Vous reprenez le travail.", {"working": True}, 0

    @check_not_working
    def perform_smoke_joint(self, player: PlayerProfile) -> Tuple[str, Dict, int]:
        if get_attr_bool(player, 'is_sleeping'):
            return "😴 Impossible de fumer en dormant !", {"confused": True}, 0

        joints = get_attr_int(player, 'joints')
        if joints <= 0:
            return "Vous n'avez pas de joint.", {"confused": True}, 0
            
        set_attr_int(player, 'joints', max(0, joints - 1))
        intox = get_attr_float(player, 'intoxication_level')
        stress = get_attr_float(player, 'stress')
        mental = get_attr_float(player, 'mental_health')
        willpower = get_attr_float(player, 'willpower')
        
        player.intoxication_level = min(100, intox + 25)
        player.stress = max(0, stress - 20)
        player.mental_health = max(0, mental - 10)
        player.willpower = max(0, willpower - 5)
        
        return "🌿 Vous fumez un joint.", {"smoke_joint": True}, 10

    @check_not_working
    def perform_smoke_cigarette(self, player: PlayerProfile) -> Tuple[str, Dict, int]:
        if get_attr_bool(player, 'is_sleeping'):
            return "😴 Impossible de fumer en dormant !", {"confused": True}, 0

        cigarettes = get_attr_int(player, 'cigarettes')
        if cigarettes <= 0:
            return "Vous n'avez plus de cigarettes.", {"confused": True}, 0
            
        set_attr_int(player, 'cigarettes', max(0, cigarettes - 1))
        stress = get_attr_float(player, 'stress')
        craving = get_attr_float(player, 'craving_nicotine')
        
        player.stress = max(0, stress - 15)
        player.craving_nicotine = max(0, craving - 50)
        
        return "🚬 Vous fumez une cigarette.", {"smoke_cigarette": True}, 5

    @check_not_working
    def use_ecigarette(self, player: PlayerProfile) -> Tuple[str, Dict, int]:
        if get_attr_bool(player, 'is_sleeping'):
            return "😴 Impossible de vapoter en dormant !", {"confused": True}, 0

        e_cigarettes = get_attr_int(player, 'e_cigarettes')
        if e_cigarettes <= 0:
            return "Vous n'avez plus de cigarette électronique.", {"confused": True}, 0
            
        set_attr_int(player, 'e_cigarettes', max(0, e_cigarettes - 1))
        stress = get_attr_float(player, 'stress')
        craving = get_attr_float(player, 'craving_nicotine')
        
        player.stress = max(0, stress - 10)
        player.craving_nicotine = max(0, craving - 30)
        
        return "💨 Vous utilisez votre vapoteuse.", {"smoke_ecigarette": True}, 3

    @check_not_working
    def perform_eat_food(self, player: PlayerProfile) -> Tuple[str, Dict, int]:
        if get_attr_bool(player, 'is_sleeping'):
            return "😴 Impossible de manger en dormant !", {"confused": True}, 0

        food_servings = get_attr_int(player, 'food_servings')
        if food_servings <= 0:
            return "Vous n'avez plus de nourriture.", {"confused": True}, 0

        set_attr_int(player, 'food_servings', max(0, food_servings - 1))
        hunger = get_attr_float(player, 'hunger')
        bowels = get_attr_float(player, 'bowels')
        energy = get_attr_float(player, 'energy')
        
        player.hunger = max(0, hunger - 40)
        player.bowels = min(100, bowels + 25)
        player.energy = min(100, energy + 5)

        return "🥪 Vous mangez un sandwich.", {"eat_sandwich": True}, 5

    @check_not_working
    def perform_eat_salad(self, player: PlayerProfile) -> Tuple[str, Dict, int]:
        if get_attr_bool(player, 'is_sleeping'):
            return "😴 Impossible de manger en dormant !", {"confused": True}, 0

        salad_servings = get_attr_int(player, 'salad_servings')
        if salad_servings <= 0:
            return "Vous n'avez plus de salade.", {"confused": True}, 0

        set_attr_int(player, 'salad_servings', max(0, salad_servings - 1))
        hunger = get_attr_float(player, 'hunger')
        health = get_attr_float(player, 'health')
        bowels = get_attr_float(player, 'bowels')
        
        player.hunger = max(0, hunger - 30)
        player.health = min(100, health + 5)
        player.bowels = min(100, bowels + 15)

        return "🥗 Vous mangez une salade.", {"eat_salad": True}, 5

    @check_not_working
    def perform_eat_tacos(self, player: PlayerProfile) -> Tuple[str, Dict, int]:
        if get_attr_bool(player, 'is_sleeping'):
            return "😴 Impossible de manger en dormant !", {"confused": True}, 0

        tacos = get_attr_int(player, 'tacos')
        if tacos <= 0:
            return "Vous n'avez plus de tacos.", {"confused": True}, 0

        player.tacos = max(0, tacos - 1)
        hunger = get_attr_float(player, 'hunger')
        bowels = get_attr_float(player, 'bowels')
        energy = get_attr_float(player, 'energy')
        
        player.hunger = max(0, hunger - 50)
        player.bowels = min(100, bowels + 35)
        player.energy = min(100, energy + 10)

        return "🌮 Vous mangez un tacos.", {"eat_tacos": True}, 5

    @check_not_working
    def perform_sleep(self, player: PlayerProfile, server_state: ServerState) -> Tuple[str, Dict, int, str]:
        if not is_night(server_state):
            return "Vous ne pouvez dormir que la nuit (22h-6h).", {"confused": True}, 0, ""

        if player.is_working:
            return "Vous ne pouvez pas dormir au travail !", {"confused": True}, 0, ""
            
        if player.energy >= 95:
            return "Vous n'êtes pas fatigué.", {"confused": True}, 0, ""
        
        # Dormir restaure l'énergie et autres stats
        energy_gain = min(95 - player.energy, 80)
        player.is_sleeping = True
        player.energy = min(100, player.energy + energy_gain)
        player.stress = max(0, player.stress - 30)
        player.mental_health = min(100, player.mental_health + 20)
        player.fatigue = max(0, player.fatigue - 40)
        
        hours_slept = energy_gain / 10
        return f"😴 Vous dormez pendant {hours_slept:.1f}h.", {"sleep": True}, int(hours_slept * 60), "sleep"

    def perform_wake_up(self, player: PlayerProfile) -> Tuple[str, Dict, int]:
        if not player.is_sleeping:
            return "Vous ne dormez pas.", {"confused": True}, 0

        player.is_sleeping = False
        return "🌅 Vous vous réveillez.", {"neutral": True}, 0

    def perform_shower(self, player: PlayerProfile) -> Tuple[str, Dict, int]:
        if player.is_sleeping:
            return "😴 Impossible de se doucher en dormant !", {"confused": True}, 0

        if player.hygiene >= 95:
            return "Vous êtes déjà très propre.", {"confused": True}, 0

        player.hygiene = min(100, player.hygiene + 60)
        player.stress = max(0, player.stress - 10)
        return "🚿 Vous prenez une douche rafraîchissante.", {"shower": True}, 10

    def perform_urinate(self, player: PlayerProfile) -> Tuple[str, Dict, int]:
        if player.is_sleeping:
            return "😴 Impossible d'uriner en dormant !", {"confused": True}, 0

        if player.bladder < 20:
            return "Vous n'avez pas besoin d'uriner.", {"confused": True}, 0
            
        player.bladder = max(0, player.bladder - 90)
        return "🚽 Vous urinez.", {"peed": True}, 2

    def perform_defecate(self, player: PlayerProfile) -> Tuple[str, Dict, int]:
        if player.is_sleeping:
            return "😴 Impossible d'aller aux toilettes en dormant !", {"confused": True}, 0

        if player.bowels < 50:
            return "Vous n'avez pas besoin d'aller à la selle.", {"confused": True}, 0
            
        player.bowels = max(0, player.bowels - 90)
        return "🚽 Vous allez à la selle.", {"pooping": True}, 5
    
    def perform_drink_water(self, player: PlayerProfile) -> Tuple[str, Dict, int]:
        if get_attr_bool(player, 'is_sleeping'):
            return "😴 Impossible de boire en dormant !", {"confused": True}, 0

        water_bottles = get_attr_int(player, 'water_bottles')
        if water_bottles <= 0:
            return "Vous n'avez plus d'eau !", {"confused": True}, 0
            
        player.water_bottles = max(0, water_bottles - 1)
        thirst = get_attr_float(player, 'thirst')
        bladder = get_attr_float(player, 'bladder')
        
        player.thirst = max(0, thirst - 40)
        player.bladder = min(100, bladder + 30)
        
        return "💧 Vous buvez de l'eau.", {"drink_water": True}, 1

    @check_not_working
    def use_soda(self, player: PlayerProfile) -> Tuple[str, Dict, int]:
        if get_attr_bool(player, 'is_sleeping'):
            return "😴 Impossible de boire en dormant !", {"confused": True}, 0

        soda_cans = get_attr_int(player, 'soda_cans')
        if soda_cans <= 0:
            return "Vous n'avez plus de soda !", {"confused": True}, 0
            
        player.soda_cans = max(0, soda_cans - 1)
        thirst = get_attr_float(player, 'thirst')
        bladder = get_attr_float(player, 'bladder')
        energy = get_attr_float(player, 'energy')
        
        player.thirst = max(0, thirst - 30)
        player.bladder = min(100, bladder + 25)
        player.energy = min(100, energy + 10)
        
        return "🥤 Vous buvez un soda.", {"drink_soda": True}, 1

    @check_not_working
    def perform_drink_wine(self, player: PlayerProfile) -> Tuple[str, Dict, int]:
        if get_attr_bool(player, 'is_sleeping'):
            return "😴 Impossible de boire en dormant !", {"confused": True}, 0

        wine_bottles = get_attr_int(player, 'wine_bottles')
        if wine_bottles <= 0:
            return "Vous n'avez pas de vin.", {}, 0
            
        player.wine_bottles = max(0, wine_bottles - 1)
        intox = get_attr_float(player, 'intoxication_level')
        stress = get_attr_float(player, 'stress')
        thirst = get_attr_float(player, 'thirst')
        bladder = get_attr_float(player, 'bladder')
        
        player.intoxication_level = min(100, intox + 20)
        player.stress = max(0, stress - 15)
        player.thirst = max(0, thirst - 10)
        player.bladder = min(100, bladder + 20)
        
        return "🍷 Vous buvez un verre de vin.", {"sad_drinking": True}, 5

async def setup(bot):
    await bot.add_cog(CookerBrain(bot))
