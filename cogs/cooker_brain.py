# --- cogs/cooker_brain.py (REWORKED WITH UNIQUE & IMAGE-LINKED EFFECTS) ---
from discord.ext import commands
from db.models import PlayerProfile
from utils.helpers import clamp
import datetime

class CookerBrain(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- ACTIONS DE BASE ---

    def perform_sleep(self, player: PlayerProfile) -> (str, dict):
        sleep_quality = 1.0 - (player.pain / 200.0) - (player.stress / 300.0)
        energy_gain = 70.0 * sleep_quality
        fatigue_loss = 80.0 * sleep_quality
        health_gain = 10.0 * sleep_quality
        stress_loss = 40.0 * sleep_quality
        
        player.energy = clamp(player.energy + energy_gain, 0, 100)
        player.fatigue = clamp(player.fatigue - fatigue_loss, 0, 100)
        player.health = clamp(player.health + health_gain, 0, 100)
        player.stress = clamp(player.stress - stress_loss, 0, 100)
        player.last_slept_at = datetime.datetime.utcnow()
        player.last_action = "neutral_sleep"
        player.last_action_time = datetime.datetime.utcnow()
        return f"Vous avez dormi (qualité: {sleep_quality:.0%}). L'énergie revient peu à peu.", {}

    def perform_shower(self, player: PlayerProfile) -> (str, dict):
        hygiene_gain = 70.0
        stress_loss = 15.0
        player.hygiene = clamp(player.hygiene + hygiene_gain, 0, 100)
        player.stress = clamp(player.stress - stress_loss, 0, 100)
        player.last_shower_at = datetime.datetime.utcnow()
        player.last_action = "neutral_shower"
        player.last_action_time = datetime.datetime.utcnow()
        return "Vous prenez une douche. Vous vous sentez propre et un peu plus détendu.", {}

    def perform_urinate(self, player: PlayerProfile) -> (str, dict):
        bladder_relief = player.bladder
        player.bladder = 0
        player.last_urinated_at = datetime.datetime.utcnow()
        player.last_action = "neutral"
        player.last_action_time = datetime.datetime.utcnow()
        return f"Ahhh... ça va mieux. Vous avez soulagé une envie pressante ({bladder_relief:.0f}%).", {}

    # --- BOISSONS ---

    def perform_drink_water(self, player: PlayerProfile) -> (str, dict):
        if player.water_bottles <= 0: return "Vous n'avez plus d'eau !", {}
        player.water_bottles -= 1
        player.thirst = clamp(player.thirst - 60.0, 0, 100)
        player.dry_mouth = clamp(player.dry_mouth - 70.0, 0, 100)
        player.last_drank_at = datetime.datetime.utcnow()
        player.last_action = "sad_drinking" if player.stress > 50 or player.happiness < 40 else "neutral_drinking"
        player.last_action_time = datetime.datetime.utcnow()
        return "Vous buvez une bouteille d'eau. Simple, pur, efficace.", {}

    def use_soda(self, player: PlayerProfile) -> (str, dict):
        if player.soda_cans <= 0: return "Vous n'avez plus de soda !", {}
        player.soda_cans -= 1
        player.thirst = clamp(player.thirst - 25, 0, 100)
        player.happiness = clamp(player.happiness + 15, 0, 100)
        player.energy = clamp(player.energy + 5, 0, 100)
        player.hunger = clamp(player.hunger - 5, 0, 100)
        player.last_drank_at = datetime.datetime.utcnow()
        player.last_action = "neutral_drinking_soda"
        player.last_action_time = datetime.datetime.utcnow()
        return "Vous buvez un soda bien frais. Le sucre pétille agréablement.", {}

    # --- NOURRITURE ---

    def perform_eat_sandwich(self, player: PlayerProfile) -> (str, dict):
        if player.food_servings <= 0: return "Vous n'avez plus de sandwich !", {}
        player.food_servings -= 1
        player.hunger = clamp(player.hunger - 50.0, 0, 100)
        player.nausea = clamp(player.nausea - 10.0, 0, 100)
        player.happiness = clamp(player.happiness + 5, 0, 100)
        player.last_eaten_at = datetime.datetime.utcnow()
        player.last_action = "neutral_eat_sandwich"
        player.last_action_time = datetime.datetime.utcnow()
        return "Vous mangez un sandwich basique. Ça cale l'estomac.", {}

    def use_tacos(self, player: PlayerProfile) -> (str, dict):
        if player.tacos <= 0: return "Vous n'avez pas de tacos !", {}
        player.tacos -= 1
        player.hunger = clamp(player.hunger - 45, 0, 100)
        player.happiness = clamp(player.happiness + 20, 0, 100)
        player.stress = clamp(player.stress - 5, 0, 100)
        player.last_eaten_at = datetime.datetime.utcnow()
        player.last_action = "neutral_eat_tacos"
        player.last_action_time = datetime.datetime.utcnow()
        return "Un tacos bien garni ! Un vrai moment de plaisir qui remonte le moral.", {}

    def use_salad(self, player: PlayerProfile) -> (str, dict):
        if player.salad_servings <= 0: return "Vous n'avez pas de salade !", {}
        player.salad_servings -= 1
        player.hunger = clamp(player.hunger - 25, 0, 100)
        player.health = clamp(player.health + 5, 0, 100)
        player.happiness = clamp(player.happiness + 10, 0, 100)
        player.last_eaten_at = datetime.datetime.utcnow()
        player.last_action = "neutral_eat_salad"
        player.last_action_time = datetime.datetime.utcnow()
        return "Une salade fraîche et saine. C'est bon pour le corps et l'esprit.", {}

    # --- FUMER ---

    def perform_smoke_cigarette(self, player: PlayerProfile) -> (str, dict):
        if player.cigarettes <= 0: return "Vous n'avez plus de cigarettes !", {}
        player.cigarettes -= 1
        player.stress = clamp(player.stress - 30.0, 0, 100)
        player.happiness = clamp(player.happiness + 5.0, 0, 100)
        player.withdrawal_severity = 0
        player.tox = clamp(player.tox + 10.0, 0, 100)
        player.dry_mouth = clamp(player.dry_mouth + 40.0, 0, 100)
        player.hunger = clamp(player.hunger - 10, 0, 100)
        player.last_smoked_at = datetime.datetime.utcnow()
        player.last_action = "neutral_smoke_cig" # CORRECTED
        player.last_action_time = datetime.datetime.utcnow()
        return "Vous allumez une cigarette. Le stress s'envole... pour l'instant.", {}

    def use_ecigarette(self, player: PlayerProfile) -> (str, dict):
        if player.e_cigarettes <= 0: return "Votre e-cigarette est vide.", {}
        player.stress = clamp(player.stress - 15, 0, 100)
        player.withdrawal_severity = clamp(player.withdrawal_severity - 25, 0, 100)
        player.tox = clamp(player.tox + 2.0, 0, 100)
        player.dry_mouth = clamp(player.dry_mouth + 15.0, 0, 100)
        player.last_smoked_at = datetime.datetime.utcnow()
        player.last_action = "vape_e_cig" # CORRECTED
        player.last_action_time = datetime.datetime.utcnow()
        return "Vous tirez sur votre vapoteuse. Ce n'est pas aussi satisfaisant, mais ça aide à tenir.", {}

async def setup(bot):
    await bot.add_cog(CookerBrain(bot))