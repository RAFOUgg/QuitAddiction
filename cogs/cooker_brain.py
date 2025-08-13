# --- cogs/cooker_brain.py (FINAL VERSION WITH ACTION FEEDBACK) ---
from discord.ext import commands
from db.models import PlayerProfile
from utils.helpers import clamp
import datetime

class CookerBrain(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def perform_eat(self, player: PlayerProfile) -> (str, dict):
        if player.food_servings <= 0: return "Vous n'avez plus rien à manger !", {}
        player.food_servings -= 1
        player.hunger = clamp(player.hunger - 50.0, 0, 100)
        player.nausea = clamp(player.nausea - 10.0, 0, 100)
        player.last_eaten_at = datetime.datetime.utcnow()
        changes = {"🍔 Faim": "-50", "🤢 Nausée": "-10"}
        return "Vous avez mangé une portion.", changes

    def perform_drink(self, player: PlayerProfile) -> (str, dict):
        if player.water_bottles <= 0 and player.beers <= 0: return "Vous n'avez plus rien à boire !", {}
        
        if player.water_bottles > 0:
            player.water_bottles -= 1
            player.thirst = clamp(player.thirst - 60.0, 0, 100)
            player.dry_mouth = clamp(player.dry_mouth - 70.0, 0, 100)
            player.last_drank_at = datetime.datetime.utcnow()
            changes = {"💧 Soif": "-60", "👄 Bouche Sèche": "-70"}
            return "Vous avez bu une bouteille d'eau.", changes
        else:
            player.beers -= 1
            player.thirst = clamp(player.thirst - 35.0, 0, 100)
            player.tox = clamp(player.tox + 5.0, 0, 100)
            player.intoxication_level = clamp(player.intoxication_level + 10, 0, 100)
            player.last_drank_at = datetime.datetime.utcnow()
            changes = {"💧 Soif": "-35", "☠️ Toxines": "+5", "😵 Défonce": "+10"}
            return "À défaut d'eau, vous avez bu une bière...", changes

    def perform_sleep(self, player: PlayerProfile) -> (str, dict):
        sleep_quality = 1.0 - (player.pain / 200.0)
        energy_gain = 60.0 * sleep_quality
        fatigue_loss = 70.0 * sleep_quality
        health_gain = 15.0 * sleep_quality
        stress_loss = 30.0 * sleep_quality
        
        player.energy = clamp(player.energy + energy_gain, 0, 100)
        player.fatigue = clamp(player.fatigue - fatigue_loss, 0, 100)
        player.health = clamp(player.health + health_gain, 0, 100)
        player.stress = clamp(player.stress - stress_loss, 0, 100)
        player.last_slept_at = datetime.datetime.utcnow()
        changes = {"⚡ Énergie": f"+{energy_gain:.0f}", "🥱 Fatigue": f"-{fatigue_loss:.0f}", "❤️ Santé": f"+{health_gain:.0f}", "😨 Stress": f"-{stress_loss:.0f}"}
        return f"Vous avez dormi (qualité: {sleep_quality:.0%}).", changes

    def perform_smoke(self, player: PlayerProfile) -> (str, dict):
        if player.cigarettes <= 0: return "Vous n'avez plus de cigarettes !", {}
        player.cigarettes -= 1
        player.stress = clamp(player.stress - 25.0, 0, 100)
        player.happiness = clamp(player.happiness + 15.0, 0, 100)
        player.withdrawal_severity = 0
        player.tox = clamp(player.tox + 8.0, 0, 100)
        player.dry_mouth = clamp(player.dry_mouth + 40.0, 0, 100)
        player.last_smoked_at = datetime.datetime.utcnow()
        changes = {"😨 Stress": "-25", "😊 Humeur": "+15", "☠️ Toxines": "+8", "👄 Bouche Sèche": "+40"}
        return "Vous avez fumé une cigarette.", changes
        
    def perform_urinate(self, player: PlayerProfile) -> (str, dict):
        player.bladder = 0.0
        player.pain = clamp(player.pain - 5, 0, 100)
        player.last_urinated_at = datetime.datetime.utcnow()
        changes = {"🚽 Vessie": "Vidée", "🤕 Douleur": "-5"}
        return "Ah... ça soulage !", changes

async def setup(bot):
    await bot.add_cog(CookerBrain(bot))