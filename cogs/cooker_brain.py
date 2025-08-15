# --- cogs/cooker_brain.py (REWORKED WITH NEW STATS & EFFECTS) ---
from discord.ext import commands
from db.models import PlayerProfile, ServerState
from utils.helpers import clamp
import datetime
from utils.game_time import is_night, get_current_game_time

class CookerBrain(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    def perform_drink_wine(self, player: PlayerProfile) -> (str, dict, int):
        if player.wine_bottles <= 0: return "Vous n'avez pas de vin.", {}, 0
        player.wine_bottles -= 1
        player.thirst = clamp(player.thirst - 15, 0, 100)
        player.stress = clamp(player.stress - 40.0, 0, 100) # Très efficace contre le stress
        player.happiness = clamp(player.happiness + 20, 0, 100)
        player.tox = clamp(player.tox + 12.0, 0, 100) # ...mais très toxique
        player.dizziness = clamp(player.dizziness + 25.0, 0, 100) # Rend vaseux
        player.guilt = clamp(player.guilt + 10.0, 0, 100)
        player.last_drank_at = datetime.datetime.utcnow()
        player.last_action = "neutral_drink_wine"
        player.last_action_time = datetime.datetime.utcnow()
        return "Vous buvez une bouteille de vin bon marché. Le stress s'efface dans une douce torpeur.", {}, 15

    def perform_smoke_joint(self, player: PlayerProfile) -> (str, dict, int):
        if player.joints <= 0: return "Vous n'avez pas de joint.", {}, 0
        player.joints -= 1
        player.stress = clamp(player.stress - 60.0, 0, 100) # Effet anti-stress radical
        player.happiness = clamp(player.happiness + 30, 0, 100)
        player.sanity = clamp(player.sanity - 5.0, 0, 100) # Mais affecte la santé mentale
        player.hunger = clamp(player.hunger + 30, 0, 100) # Défonce !
        player.tox = clamp(player.tox + 5.0, 0, 100)
        player.job_performance = clamp(player.job_performance - 20, 0, 100) # Incompatible avec le travail
        player.guilt = clamp(player.guilt + 20.0, 0, 100)
        player.last_smoked_at = datetime.datetime.utcnow()
        player.last_action = "neutral_smoke_joint"
        player.last_action_time = datetime.datetime.utcnow()
        return "Vous allumez un joint. Le monde semble plus lent, plus doux... et la faim vous tenaille.", {}, 25
    
    def perform_sleep(self, player: PlayerProfile, server_state: ServerState) -> (str, dict, int, str):
        game_time = get_current_game_time(server_state)
        night_time = is_night(server_state)

        if night_time:
            # Nuit complète
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
            
            duration = 300 # 5 minutes for a full night
            return f"Vous avez dormi profondément jusqu'au matin (qualité: {sleep_quality:.0%}). L'énergie et la volonté rechargées.", {}, duration, "night"

        else: # C'est la journée
            if player.fatigue > 60:
                # Sieste possible
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
                
                duration = 90 # 1.5 minutes for a nap
                return f"Vous avez fait une sieste réparatrice (qualité: {nap_quality:.0%}).", {}, duration, "nap"
            else:
                # Pas assez fatigué pour une sieste
                return "Vous n'êtes pas assez fatigué pour faire une sieste maintenant.", {}, 0, "none"}

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
        player.last_action = "neutral_pooping" # Lie l'action à l'image
        player.last_action_time = datetime.datetime.utcnow()
        return f"Vous vous sentez plus léger après ce passage aux toilettes. (Soulagement: {bowel_relief:.0f}%)", {}, 15
    
    def perform_drink_water(self, player: PlayerProfile) -> (str, dict, int):
        if player.water_bottles <= 0: return "Vous n'avez plus d'eau !", {}, 0
        player.water_bottles -= 1
        player.thirst = clamp(player.thirst - 60.0, 0, 100)
        player.dry_mouth = clamp(player.dry_mouth - 70.0, 0, 100)
        # L'eau aide à nettoyer le corps
        player.tox = clamp(player.tox - 2.0, 0, 100)
        player.last_drank_at = datetime.datetime.utcnow()
        player.last_action = "sad_drinking" if player.stress > 50 else "neutral_drinking"
        player.last_action_time = datetime.datetime.utcnow()
        return "Vous buvez une bouteille d'eau. Simple, pur, efficace.", {}, 5

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

    def perform_eat_sandwich(self, player: PlayerProfile) -> (str, dict, int):
        if player.food_servings <= 0: return "Vous n'avez plus de sandwich !", {}, 0
        player.food_servings -= 1
        player.hunger = clamp(player.hunger - 50.0, 0, 100)
        player.nausea = clamp(player.nausea - 10.0, 0, 100)
        player.happiness = clamp(player.happiness + 5, 0, 100)
        player.bowels = clamp(player.bowels + 15, 0, 100) # EFFET AJOUTE
        player.last_eaten_at = datetime.datetime.utcnow()
        player.last_action = "neutral_eat_sandwich"
        player.last_action_time = datetime.datetime.utcnow()
        return "Vous mangez un sandwich basique. Ça cale l'estomac.", {}, 20

    def use_tacos(self, player: PlayerProfile) -> (str, dict, int):
        if player.tacos <= 0: return "Vous n'avez pas de tacos !", {}, 0
        player.tacos -= 1
        player.hunger = clamp(player.hunger - 45, 0, 100)
        player.happiness = clamp(player.happiness + 20, 0, 100)
        player.bowels = clamp(player.bowels + 25, 0, 100) # EFFET AJOUTE (plus consistant !)
        player.last_eaten_at = datetime.datetime.utcnow()
        player.last_action = "neutral_eat_tacos"
        player.last_action_time = datetime.datetime.utcnow()
        return "Un tacos bien garni ! Un vrai moment de plaisir.", {}, 25

    def use_salad(self, player: PlayerProfile) -> (str, dict, int):
        if player.salad_servings <= 0: return "Vous n'avez pas de salade !", {}, 0
        player.salad_servings -= 1
        player.hunger = clamp(player.hunger - 25, 0, 100)
        player.health = clamp(player.health + 5, 0, 100)
        player.happiness = clamp(player.happiness + 10, 0, 100)
        player.tox = clamp(player.tox - 4.0, 0, 100)
        player.bowels = clamp(player.bowels + 30, 0, 100) # EFFET AJOUTE (riche en fibres !)
        player.last_eaten_at = datetime.datetime.utcnow()
        player.last_action = "neutral_eat_salad"
        player.last_action_time = datetime.datetime.utcnow()
        return "Une salade fraîche et saine. C'est bon pour le corps et l'esprit.", {}, 20

    def perform_smoke_cigarette(self, player: PlayerProfile) -> (str, dict, int):
        if player.cigarettes <= 0: return "Vous n'avez plus de cigarettes !", {}, 0
        player.cigarettes -= 1
        
        # Effet basé sur la tolérance
        tolerance_factor = 1.0 - (player.substance_tolerance / 200.0) # plus de tolérance, moins d'effet
        stress_relief = 30.0 * tolerance_factor
        
        player.stress = clamp(player.stress - stress_relief, 0, 100)
        player.withdrawal_severity = 0 # Le manque est instantanément comblé
        player.craving_nicotine = 0
        player.tox = clamp(player.tox + 8.0, 0, 100) # Fumer est toxique
        player.dry_mouth = clamp(player.dry_mouth + 40.0, 0, 100)
        player.sore_throat = clamp(player.sore_throat + 10.0, 0, 100)
        player.guilt = clamp(player.guilt + 15.0, 0, 100) # Craquer => Culpabilité
        player.substance_addiction_level = clamp(player.substance_addiction_level + 0.5, 0, 100)
        player.substance_tolerance = clamp(player.substance_tolerance + 1.0, 0, 100)
        
        player.last_smoked_at = datetime.datetime.utcnow()
        player.last_action = "neutral_smoke_cig"
        player.last_action_time = datetime.datetime.utcnow()
        return "Vous allumez une cigarette. Le stress s'envole, mais à quel prix... La culpabilité vous pèse déjà.", {}, 10

    def use_ecigarette(self, player: PlayerProfile) -> (str, dict, int):
        if player.e_cigarettes <= 0: return "Votre e-cigarette est vide.", {}, 0
        #... Logique similaire mais avec des effets moindres (moins de tox, moins de culpabilité)...
        player.stress = clamp(player.stress - 15, 0, 100)
        player.withdrawal_severity = clamp(player.withdrawal_severity - 40, 0, 100) # Calme bien le manque
        player.tox = clamp(player.tox + 2.0, 0, 100)
        player.guilt = clamp(player.guilt + 2.0, 0, 100)
        player.last_smoked_at = datetime.datetime.utcnow()
        player.last_action = "vape_e_cig"
        player.last_action_time = datetime.datetime.utcnow()
        return "Vous tirez sur votre vapoteuse. Moins satisfaisant, mais ça aide à tenir.", {}, 5

async def setup(bot):
    await bot.add_cog(CookerBrain(bot))