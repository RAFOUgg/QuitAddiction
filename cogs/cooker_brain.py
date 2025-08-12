# --- cogs/cooker_brain.py (REFACTORED as the Game Engine) ---
from discord.ext import commands
from db.models import PlayerProfile
from utils.calculations import clamp

class CookerBrain(commands.Cog):
    """
    Le moteur de jeu. Contient toute la logique pour modifier l'état du personnage.
    N'interagit pas directement avec Discord, mais est appelé par d'autres cogs.
    """
    def __init__(self, bot):
        self.bot = bot

    def perform_eat(self, player: PlayerProfile) -> str:
        """Logique pour l'action de manger."""
        player.hunger = clamp(player.hunger - 40.0, 0, 100)
        player.happiness = clamp(player.happiness + 5.0, 0, 100)
        return "Vous avez mangé. Votre faim est apaisée."

    def perform_drink(self, player: PlayerProfile) -> str:
        """Logique pour l'action de boire."""
        player.thirst = clamp(player.thirst - 50.0, 0, 100)
        return "Vous avez bu de l'eau. Vous vous sentez hydraté."

    def perform_sleep(self, player: PlayerProfile) -> str:
        """Logique pour l'action de dormir."""
        player.health = clamp(player.health + 25.0, 0, 100)
        player.energy = clamp(player.energy + 50.0, 0, 100)
        player.stress = clamp(player.stress - 20.0, 0, 100)
        return "Une bonne nuit de sommeil ! Vous vous sentez reposé."

    def perform_smoke(self, player: PlayerProfile, smoke_type: str = "leger") -> str:
        """Logique pour l'action de fumer."""
        # On pourrait avoir une logique plus complexe ici en fonction du type
        player.stress = clamp(player.stress - 15.0, 0, 100)
        player.happiness = clamp(player.happiness + 10.0, 0, 100)
        player.tox = clamp(player.tox + 5.0, 0, 100)
        player.substance_addiction_level = clamp(player.substance_addiction_level + 1.5, 0, 100)
        return "Une cigarette pour décompresser... mais à quel prix ?"

async def setup(bot):
    await bot.add_cog(CookerBrain(bot))