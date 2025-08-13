# --- cogs/cooker_brain.py (UPDATED to handle new variables and timestamps) ---
from discord.ext import commands
from db.models import PlayerProfile
from utils.helpers import clamp # ou gardez la fonction clamp ici
import datetime

class CookerBrain(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def perform_eat(self, player: PlayerProfile) -> str:
        if player.food_servings <= 0: return "Vous n'avez plus rien à manger !"
        player.food_servings -= 1
        player.hunger = clamp(player.hunger - 50.0, 0, 100)
        player.nausea = clamp(player.nausea - 10.0, 0, 100)
        player.last_eaten_at = datetime.datetime.utcnow()
        return "Vous avez mangé une portion de nourriture."

    def perform_drink(self, player: PlayerProfile) -> str:
        if player.water_bottles <= 0 and player.beers <= 0: return "Vous n'avez plus rien à boire !"
        
        if player.water_bottles > 0:
            player.water_bottles -= 1
            player.thirst = clamp(player.thirst - 60.0, 0, 100)
            player.dry_mouth = clamp(player.dry_mouth - 70.0, 0, 100)
            player.last_drank_at = datetime.datetime.utcnow()
            return "Vous avez bu une bouteille d'eau."
        else:
            player.beers -= 1
            player.thirst = clamp(player.thirst - 35.0, 0, 100)
            player.tox = clamp(player.tox + 5.0, 0, 100)
            player.intoxication_level = clamp(player.intoxication_level + 10, 0, 100)
            player.last_drank_at = datetime.datetime.utcnow()
            return "À défaut d'eau, vous avez bu une bière..."

    def perform_sleep(self, player: PlayerProfile) -> str:
        sleep_quality = 1.0 - (player.pain / 200.0)
        player.energy = clamp(player.energy + 60.0 * sleep_quality, 0, 100)
        player.fatigue = clamp(player.fatigue - 70.0 * sleep_quality, 0, 100)
        player.health = clamp(player.health + 15.0 * sleep_quality, 0, 100)
        player.stress = clamp(player.stress - 30.0 * sleep_quality, 0, 100)
        player.last_slept_at = datetime.datetime.utcnow()
        return f"Vous avez dormi (qualité: {sleep_quality:.0%})."

    def perform_smoke(self, player: PlayerProfile) -> str:
        if player.cigarettes <= 0: return "Vous n'avez plus de cigarettes !"
        player.cigarettes -= 1
        player.stress = clamp(player.stress - 25.0, 0, 100)
        player.happiness = clamp(player.happiness + 15.0, 0, 100)
        player.withdrawal_severity = 0
        player.tox = clamp(player.tox + 8.0, 0, 100)
        player.dry_mouth = clamp(player.dry_mouth + 40.0, 0, 100)
        player.sore_throat = clamp(player.sore_throat + 15.0, 0, 100)
        player.substance_addiction_level = clamp(player.substance_addiction_level + 1.0, 0, 100)
        player.intoxication_level = clamp(player.intoxication_level + 20.0, 0, 100)
        player.last_smoked_at = datetime.datetime.utcnow()
        return "Vous avez fumé une cigarette."
        
    def perform_urinate(self, player: PlayerProfile) -> str:
        player.bladder = 0.0
        player.pain = clamp(player.pain - 5, 0, 100)
        player.last_urinated_at = datetime.datetime.utcnow()
        return "Ah... ça soulage !"

async def setup(bot):
    await bot.add_cog(CookerBrain(bot))