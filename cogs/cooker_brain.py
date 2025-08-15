# --- cogs/cooker_brain.py (REWORKED WITH NEW STATS & EFFECTS) ---
from discord.ext import commands
from db.models import PlayerProfile, ServerState
from utils.helpers import clamp
import datetime
from utils.game_time import is_night, get_current_game_time, is_work_time, is_lunch_break
from functools import wraps

def check_not_working(func):
    @wraps(func)
    def wrapper(self, player: PlayerProfile, *args, **kwargs):
        if player.is_working and not player.is_on_break:
            return "Vous êtes au travail, vous ne pouvez pas faire ça maintenant.", {}, 0
        return func(self, player, *args, **kwargs)
    return wrapper

class CookerBrain(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def perform_sport(self, player: PlayerProfile, server_state: ServerState) -> (str, dict, int):
        """
        Permet au joueur de faire du sport pendant ses jours de repos.
        Les avantages sont nombreux : santé physique et mentale, réduction de l'ennui.
        """
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

    def perform_use_bong(self, player: PlayerProfile) -> (str, dict, int):
        """
        Utilise le bong pour consommer du cannabis.
        Impact plus fort qu'un joint mais consomme plus de produit.
        """
        inventory = self.check_inventory(player)
        
        if not inventory['has_bong']:
            return "🌊 Vous n'avez pas de bong.", {"confused": True}, 0
            
        if player.weed_grams < 1.5 and player.hash_grams < 1:
            return "🌊 Il vous faut au moins 1.5g de weed ou 1g de hash pour le bong.", {"confused": True}, 0
            
        # Utiliser weed en priorité, sinon hash
        if player.weed_grams >= 1.5:
            player.weed_grams -= 1.5
            substance = "weed"
        else:
            player.hash_grams -= 1
            substance = "hash"
            
        # Effets plus forts qu'un joint
        player.intoxication = min(100, player.intoxication + 40)
        player.stress = max(0, player.stress - 30)
        player.mental_health = max(0, player.mental_health - 15)
        player.willpower = max(0, player.willpower - 10)
        player.bong_uses += 1
        
        return f"🌊 Vous utilisez le bong avec du {substance}. L'effet est puissant !", {"smoke_bang": True}, 15

    def perform_go_to_work(self, player: PlayerProfile, server_state: ServerState) -> (str, dict, int):
        current_time = get_current_game_time(server_state)
        current_weekday = server_state.game_start_time.weekday()  # 0 = Lundi, 6 = Dimanche

        # Vérifier si c'est un jour de repos
        if current_weekday in [0, 6]:  # Lundi (0) ou Dimanche (6)
            return "📅 C'est votre jour de repos ! Revenez demain.", {"leaving_for_work": False}, 0

        if not is_work_time(server_state):
            return "⏰ Les horaires de travail sont 9h-11h30 et 13h-17h30.", {"confused": True}, 0
            
        if player.is_working:
            return "👨‍🍳 Vous êtes déjà au travail !", {"confused": True}, 0

        current_time = get_current_game_time(server_state)
        morning_start = datetime.time(hour=9, minute=0)
        afternoon_start = datetime.time(hour=13, minute=0)

        # Emploi du temps hebdomadaire
        schedule = """📅 Emploi du temps:
        Lundi: REPOS
        Mardi: 9h-11h30 | 13h-17h30
        Mercredi: 9h-11h30 | 13h-17h30
        Jeudi: 9h-11h30 | 13h-17h30
        Vendredi: 9h-11h30 | 13h-17h30
        Samedi: 9h-11h30 | 13h-17h30
        Dimanche: REPOS"""

        lateness = 0
        if morning_start <= current_time < datetime.time(hour=11, minute=30):
            
        elif afternoon_start <= current_time < datetime.time(hour=17, minute=30):

    def perform_go_home(self, player: PlayerProfile, server_state: ServerState) -> (str, dict, int):
        if not player.is_working:
            return "Vous n'êtes pas au travail.", {}, 0
        
        player.is_working = False
        player.is_on_break = False
        player.last_action = "neutral"
        player.last_action_time = datetime.datetime.utcnow()
        return "Vous rentrez à la maison.", {}, 0

    def perform_take_smoke_break(self, player: PlayerProfile) -> (str, dict, int):
        if not player.is_working:
            return "Vous devez être au travail pour prendre une pause.", {}, 0
        if player.is_on_break:
            return "Vous êtes déjà en pause.", {}, 0

        player.is_on_break = True
        duration = 15 
        player.job_performance = clamp(player.job_performance - 2, 0, 100)
        return "Vous prenez une pause cigarette.", {}, duration

    @check_not_working
    def perform_drink_wine(self, player: PlayerProfile) -> (str, dict, int):
        if player.wine_bottles <= 0: return "Vous n'avez pas de vin.", {}, 0
        player.wine_bottles -= 1
        player.thirst = clamp(player.thirst - 15, 0, 100)
        player.stress = clamp(player.stress - 40.0, 0, 100)
        player.happiness = clamp(player.happiness + 20, 0, 100)
        player.tox = clamp(player.tox + 12.0, 0, 100)
        player.dizziness = clamp(player.dizziness + 25.0, 0, 100)
        player.guilt = clamp(player.guilt + 10.0, 0, 100)
        player.last_drank_at = datetime.datetime.utcnow()
        player.last_action = "neutral_drink_wine"
        player.last_action_time = datetime.datetime.utcnow()
        return "Vous buvez une bouteille de vin bon marché. Le stress s'efface dans une douce torpeur.", {}, 15

    def perform_smoke_joint(self, player: PlayerProfile) -> (str, dict, int):
        if player.is_on_break:
            player.job_performance = clamp(player.job_performance - 15, 0, 100)
            player.last_action = "job_pause_joint"
        else:
            player.last_action = "neutral_smoke_joint"
        if player.joints <= 0: return "Vous n'avez pas de joint.", {}, 0
        player.joints -= 1
        player.stress = clamp(player.stress - 60.0, 0, 100)
        player.happiness = clamp(player.happiness + 30, 0, 100)
        player.sanity = clamp(player.sanity - 5.0, 0, 100)
        player.hunger = clamp(player.hunger + 30, 0, 100)
        player.tox = clamp(player.tox + 5.0, 0, 100)
        player.job_performance = clamp(player.job_performance - 20, 0, 100)
        player.guilt = clamp(player.guilt + 20.0, 0, 100)
        player.last_smoked_at = datetime.datetime.utcnow()
        player.last_action = "neutral_smoke_joint"
        player.last_action_time = datetime.datetime.utcnow()
        player.is_on_break = False
        return "Vous allumez un joint. Le monde semble plus lent, plus doux... et la faim vous tenaille.", {}, 25
    
    @check_not_working
    def perform_sleep(self, player: PlayerProfile, server_state: ServerState) -> (str, dict, int, str):
        game_time = get_current_game_time(server_state)
        night_time = is_night(server_state)

        if night_time:
            sleep_quality = 1.0 - (player.pain / 150.0) - (player.stress / 200.0)
            energy_gain = 85.0 * sleep_quality
            fatigue_loss = 95.0 * sleep_quality
            stress_loss = 50.0 * sleep_quality
            willpower_gain = 40.0 * sleep_quality

            player.energy = clamp(player.energy + energy_gain, 0, 100)
            player.fatigue = clamp(player.fatigue - fatigue_loss, 0, 100)
            player.stress = clamp(player.stress - stress_loss, 0, 100)
            player.willpower = clamp(player.willpower + willpower_gain, 0, 100)
            player.last_slept_at = datetime.datetime.utcnow()
            player.last_action = "neutral_sleep"
            player.last_action_time = datetime.datetime.utcnow()
            
            duration = 300
            return f"Vous avez dormi profondément jusqu'au matin (qualité: {sleep_quality:.0%}). L'énergie et la volonté rechargées.", {}, duration, "night"

        else:
            if player.fatigue > 60:
                nap_quality = 1.0 - (player.stress / 250.0)
                energy_gain = 30.0 * nap_quality
                fatigue_loss = 40.0 * nap_quality
                stress_loss = 10.0 * nap_quality

                player.energy = clamp(player.energy + energy_gain, 0, 100)
                player.fatigue = clamp(player.fatigue - fatigue_loss, 0, 100)
                player.stress = clamp(player.stress - stress_loss, 0, 100)
                player.last_slept_at = datetime.datetime.utcnow()
                player.last_action = "neutral_sleep"
                player.last_action_time = datetime.datetime.utcnow()
                
                duration = 90
                return f"Vous avez fait une sieste réparatrice (qualité: {nap_quality:.0%}).", {}, duration, "nap"
            else:
                return "Vous n'êtes pas assez fatigué pour faire une sieste maintenant.", {}, 0, "none"

    @check_not_working
    def perform_shower(self, player: PlayerProfile) -> (str, dict, int):
        hygiene_gain = 70.0
        stress_loss = 15.0
        happiness_gain = 5.0
        player.hygiene = clamp(player.hygiene + hygiene_gain, 0, 100)
        player.stress = clamp(player.stress - stress_loss, 0, 100)
        player.happiness = clamp(player.happiness + happiness_gain, 0, 100)
        player.last_shower_at = datetime.datetime.utcnow()
        player.last_action = "neutral_shower"
        player.last_action_time = datetime.datetime.utcnow()
        return "Une bonne douche. Vous vous sentez propre, détendu et un peu plus optimiste.", {}, 60

    def perform_urinate(self, player: PlayerProfile) -> (str, dict, int):
        bladder_relief = player.bladder
        player.bladder = 0
        player.last_urinated_at = datetime.datetime.utcnow()
        player.last_action = "neutral"
        player.last_action_time = datetime.datetime.utcnow()
        return f"Ahhh... ça va mieux. Vous avez soulagé une envie pressante ({bladder_relief:.0f}%).", {}, 5

    def perform_defecate(self, player: PlayerProfile) -> (str, dict, int):
        bowel_relief = player.bowels
        player.bowels = 0
        player.last_defecated_at = datetime.datetime.utcnow()
        player.last_action = "neutral_pooping"
        player.last_action_time = datetime.datetime.utcnow()
        return f"Vous vous sentez plus léger après ce passage aux toilettes. (Soulagement: {bowel_relief:.0f}%)", {}, 15
    
    def perform_drink_water(self, player: PlayerProfile) -> (str, dict, int):
        if player.water_bottles <= 0: return "Vous n'avez plus d'eau !", {}, 0
        player.water_bottles -= 1
        player.thirst = clamp(player.thirst - 60.0, 0, 100)
        player.dry_mouth = clamp(player.dry_mouth - 70.0, 0, 100)
        player.tox = clamp(player.tox - 2.0, 0, 100)
        player.last_drank_at = datetime.datetime.utcnow()
        player.last_action = "sad_drinking" if player.stress > 50 else "neutral_drinking"
        player.last_action_time = datetime.datetime.utcnow()
        return "Vous buvez une bouteille d'eau. Simple, pur, efficace.", {}, 5

    @check_not_working
    def use_soda(self, player: PlayerProfile) -> (str, dict, int):
        if player.soda_cans <= 0: return "Vous n'avez plus de soda !", {}, 0
        player.soda_cans -= 1
        player.thirst = clamp(player.thirst - 25, 0, 100)
        player.happiness = clamp(player.happiness + 15, 0, 100)
        player.energy = clamp(player.energy + 5, 0, 100)
        player.last_drank_at = datetime.datetime.utcnow()
        player.last_action = "neutral_drinking_soda"
        player.last_action_time = datetime.datetime.utcnow()
        return "Un soda bien frais. Le sucre pétille agréablement.", {}, 5

    @check_not_working
    def perform_eat_sandwich(self, player: PlayerProfile) -> (str, dict, int):
        if player.food_servings <= 0: return "Vous n'avez plus de sandwich !", {}, 0
        player.food_servings -= 1
        player.hunger = clamp(player.hunger - 50.0, 0, 100)
        player.nausea = clamp(player.nausea - 10.0, 0, 100)
        player.happiness = clamp(player.happiness + 5, 0, 100)
        player.bowels = clamp(player.bowels + 15, 0, 100)
        player.last_eaten_at = datetime.datetime.utcnow()
        player.last_action = "neutral_eat_sandwich"
        player.last_action_time = datetime.datetime.utcnow()
        return "Vous mangez un sandwich basique. Ça cale l'estomac.", {}, 20

    @check_not_working
    def use_tacos(self, player: PlayerProfile) -> (str, dict, int):
        if player.tacos <= 0: return "Vous n'avez pas de tacos !", {}, 0
        player.tacos -= 1
        player.hunger = clamp(player.hunger - 45, 0, 100)
        player.happiness = clamp(player.happiness + 20, 0, 100)
        player.bowels = clamp(player.bowels + 25, 0, 100)
        player.last_eaten_at = datetime.datetime.utcnow()
        player.last_action = "neutral_eat_tacos"
        player.last_action_time = datetime.datetime.utcnow()
        return "Un tacos bien garni ! Un vrai moment de plaisir.", {}, 25

    @check_not_working
    def use_salad(self, player: PlayerProfile) -> (str, dict, int):
        if player.salad_servings <= 0: return "Vous n'avez pas de salade !", {}, 0
        player.salad_servings -= 1
        player.hunger = clamp(player.hunger - 25, 0, 100)
        player.health = clamp(player.health + 5, 0, 100)
        player.happiness = clamp(player.happiness + 10, 0, 100)
        player.tox = clamp(player.tox - 4.0, 0, 100)
        player.bowels = clamp(player.bowels + 30, 0, 100)
        player.last_eaten_at = datetime.datetime.utcnow()
        player.last_action = "neutral_eat_salad"
        player.last_action_time = datetime.datetime.utcnow()
        return "Une salade fraîche et saine. C'est bon pour le corps et l'esprit.", {}, 20

    def perform_smoke_cigarette(self, player: PlayerProfile) -> (str, dict, int):
        if player.is_on_break:
            player.job_performance = clamp(player.job_performance - 5, 0, 100)
            player.last_action = "job_pause_cig"
        else:
            player.last_action = "neutral_smoke_cig"
        if player.cigarettes <= 0: return "Vous n'avez plus de cigarettes !", {}, 0
        player.cigarettes -= 1
        
        tolerance_factor = 1.0 - (player.substance_tolerance / 200.0)
        stress_relief = 30.0 * tolerance_factor
        
        player.stress = clamp(player.stress - stress_relief, 0, 100)
        player.withdrawal_severity = 0
        player.craving_nicotine = 0
        player.tox = clamp(player.tox + 8.0, 0, 100)
        player.dry_mouth = clamp(player.dry_mouth + 40.0, 0, 100)
        player.sore_throat = clamp(player.sore_throat + 10.0, 0, 100)
        player.guilt = clamp(player.guilt + 15.0, 0, 100)
        player.substance_addiction_level = clamp(player.substance_addiction_level + 0.5, 0, 100)
        player.substance_tolerance = clamp(player.substance_tolerance + 1.0, 0, 100)
        
        player.last_smoked_at = datetime.datetime.utcnow()
        player.last_action_time = datetime.datetime.utcnow()
        player.is_on_break = False
        return "Vous allumez une cigarette. Le stress s'envole, mais à quel prix... La culpabilité vous pèse déjà.", {}, 10

    def use_ecigarette(self, player: PlayerProfile) -> (str, dict, int):
        if player.is_on_break:
            player.job_performance = clamp(player.job_performance - 2, 0, 100)
        if player.e_cigarettes <= 0: return "Votre e-cigarette est vide.", {}, 0
        player.stress = clamp(player.stress - 15, 0, 100)
        player.withdrawal_severity = clamp(player.withdrawal_severity - 40, 0, 100)
        player.tox = clamp(player.tox + 2.0, 0, 100)
        player.guilt = clamp(player.guilt + 2.0, 0, 100)
        player.last_smoked_at = datetime.datetime.utcnow()
        player.last_action = "vape_e_cig"
        player.last_action_time = datetime.datetime.utcnow()
        player.is_on_break = False
        return "Vous tirez sur votre vapoteuse. Moins satisfaisant, mais ça aide à tenir.", {}, 5

    def perform_end_smoke_break(self, player: PlayerProfile) -> (str, dict, int):
        """
        Termine la pause cigarette et remet le joueur en mode travail normal.
        """
        if not player.is_working:
            return "Vous n'êtes pas au travail.", {}, 0
        if not player.is_on_break:
            return "Vous n'êtes pas en pause.", {}, 0
        player.is_on_break = False
        player.last_action = "working"
        player.last_action_time = datetime.datetime.utcnow()
        return "Vous retournez au travail après la pause.", {}, 0

async def setup(bot):
    await bot.add_cog(CookerBrain(bot))