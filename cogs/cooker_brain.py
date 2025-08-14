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
        # Le sommeil est réparateur, mais sa qualité dépend du stress et de la douleur.
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
        player.thirst = clamp(player.thirst - 25, 0, 100) # Le sucre, ça n'hydrate pas vraiment.
        player.happiness = clamp(player.happiness + 15, 0, 100) # Un petit plaisir coupable.
        player.energy = clamp(player.energy + 5, 0, 100) # Un léger coup de fouet.
        player.hunger = clamp(player.hunger - 5, 0, 100) # Coupe un peu la faim.
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
        player.happiness = clamp(player.happiness + 5, 0, 100) # C'est mieux que rien.
        player.last_eaten_at = datetime.datetime.utcnow()
        player.last_action = "neutral_eat_sandwich"
        player.last_action_time = datetime.datetime.utcnow()
        return "Vous mangez un sandwich basique. Ça cale l'estomac.", {}

    def use_tacos(self, player: PlayerProfile) -> (str, dict):
        # Note : Ajoutez `tacos: int` à votre modèle PlayerProfile pour que ça marche.
        if player.tacos <= 0: return "Vous n'avez pas de tacos !", {}
        player.tacos -= 1
        player.hunger = clamp(player.hunger - 45, 0, 100)
        player.happiness = clamp(player.happiness + 20, 0, 100) # Un vrai réconfort !
        player.stress = clamp(player.stress - 5, 0, 100)
        player.last_eaten_at = datetime.datetime.utcnow()
        player.last_action = "neutral_eat_tacos"
        player.last_action_time = datetime.datetime.utcnow()
        return "Un tacos bien garni ! Un vrai moment de plaisir qui remonte le moral.", {}

    # --- FUMER ---

    def perform_smoke_cigarette(self, player: PlayerProfile) -> (str, dict):
        if player.cigarettes <= 0: return "Vous n'avez plus de cigarettes !", {}
        player.cigarettes -= 1
        player.stress = clamp(player.stress - 30.0, 0, 100) # Le "fix" le plus puissant.
        player.happiness = clamp(player.happiness + 5.0, 0, 100) # Un plaisir chimique, pas un vrai bonheur.
        player.withdrawal_severity = 0 # Annule complètement le manque.
        player.tox = clamp(player.tox + 10.0, 0, 100) # Contrepartie: très toxique.
        player.dry_mouth = clamp(player.dry_mouth + 40.0, 0, 100)
        player.hunger = clamp(player.hunger - 10, 0, 100) # Coupe-faim.
        player.last_smoked_at = datetime.datetime.utcnow()
        player.last_action = "smoke_cig"
        player.last_action_time = datetime.datetime.utcnow()
        return "Vous allumez une cigarette. Le stress s'envole... pour l'instant.", {}

    def use_ecigarette(self, player: PlayerProfile) -> (str, dict):
        if player.ecigarettes <= 0: return "Votre e-cigarette est vide.", {}
        player.stress = clamp(player.stress - 15, 0, 100) # Moins efficace contre le stress.
        player.withdrawal_severity = clamp(player.withdrawal_severity - 25, 0, 100) # Calme le manque, mais ne l'annule pas.
        player.tox = clamp(player.tox + 2.0, 0, 100) # Beaucoup moins toxique.
        player.dry_mouth = clamp(player.dry_mouth + 15.0, 0, 100)
        player.last_smoked_at = datetime.datetime.utcnow()
        player.last_action = "vapote_e_cig"
        player.last_action_time = datetime.datetime.utcnow()
        return "Vous tirez sur votre vapoteuse. Ce n'est pas aussi satisfaisant, mais ça aide à tenir.", {}

async def setup(bot):
    await bot.add_cog(CookerBrain(bot))