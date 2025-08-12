# --- cogs/cooker_brain.py (UPDATED to handle new variables and timestamps) ---
from discord.ext import commands
from db.models import PlayerProfile
from utils.helpers import clamp # ou gardez la fonction clamp ici
import datetime

class CookerBrain(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def perform_eat(self, player: PlayerProfile) -> str:
        player.hunger = clamp(player.hunger - 50.0, 0, 100)
        player.nausea = clamp(player.nausea - 10.0, 0, 100) # Manger peut calmer une légère nausée
        player.last_eaten_at = datetime.datetime.utcnow()
        return "Vous avez mangé."

    def perform_drink(self, player: PlayerProfile) -> str:
        player.thirst = clamp(player.thirst - 60.0, 0, 100)
        player.dry_mouth = clamp(player.dry_mouth - 70.0, 0, 100)
        player.headache = clamp(player.headache - 15.0, 0, 100)
        player.last_drank_at = datetime.datetime.utcnow()
        return "Vous avez bu de l'eau."

    def perform_sleep(self, player: PlayerProfile) -> str:
        # La qualité du sommeil dépend de la douleur
        sleep_quality = 1.0 - (player.pain / 200.0) # 100 de douleur = 50% de qualité
        
        player.energy = clamp(player.energy + 60.0 * sleep_quality, 0, 100)
        player.fatigue = clamp(player.fatigue - 70.0 * sleep_quality, 0, 100)
        player.health = clamp(player.health + 15.0 * sleep_quality, 0, 100)
        player.stress = clamp(player.stress - 30.0 * sleep_quality, 0, 100)
        player.last_slept_at = datetime.datetime.utcnow()
        return f"Vous avez dormi (qualité: {sleep_quality:.0%})."

    def perform_smoke(self, player: PlayerProfile, smoke_type: str = "leger") -> str:
        player.stress = clamp(player.stress - 25.0, 0, 100)
        player.happiness = clamp(player.happiness + 15.0, 0, 100)
        player.withdrawal_severity = 0 # Fumer calme le manque IMMÉDIATEMENT
        
        # Effets négatifs
        player.tox = clamp(player.tox + 8.0, 0, 100)
        player.dry_mouth = clamp(player.dry_mouth + 40.0, 0, 100)
        player.sore_throat = clamp(player.sore_throat + 15.0, 0, 100)
        player.substance_addiction_level = clamp(player.substance_addiction_level + 1.0, 0, 100)
        player.intoxication_level = clamp(player.intoxication_level + 20.0, 0, 100)
        player.last_smoked_at = datetime.datetime.utcnow()
        return "Vous avez fumé une cigarette."
        
    def perform_urinate(self, player: PlayerProfile) -> str:
        player.bladder = 0.0
        player.pain = clamp(player.pain - 5, 0, 100) # Soulage la douleur liée à la vessie
        player.last_urinated_at = datetime.datetime.utcnow()
        return "Ah... ça soulage !"

async def setup(bot):
    await bot.add_cog(CookerBrain(bot))