# cogs/scheduler.py
from discord.ext import commands, tasks
from utils.calculations import apply_delayed_effects, chain_reactions

class Scheduler(commands.Cog):
    """Tâches automatiques pour la dégradation et les effets différés."""

    def __init__(self, bot):
        self.bot = bot
        self.pending_effects = []
        # self.tick.start() # Laisser le démarrage des tâches au bot.py si possible, ou s'assurer que le bot est bien prêt.
        # Pour le moment, on commente ceci pour tester le chargement des cogs.
        # Vous devrez gérer le démarrage des tâches plus tard.

    # Définir la tâche ici mais ne pas la démarrer automatiquement dans __init__ si cela pose problème.
    # Le démarrage pourrait être fait dans setup() ou via une commande.
    @tasks.loop(hours=1)
    async def tick(self):
        # Décrément des jauges FOOD/WATER/ENER/PHYS/MENT et application des réactions
        print("[Tick] Mise à jour des jauges et vérification de l'état du cuisinier")
        # Placeholder: à relier à la DB
        state = {
            "FOOD": 100,
            "WATER": 100,
            "PHYS": 100,
            "MENT": 100,
            "ENER": 100,
            "STRESS": 20,
            "HAPPY": 80,
            "ADDICTION": 0,
            "PAIN": 0,
            "BLADDER": 0,
            "TRIP": 0,
            "TOX": 0
        }
        chain_reactions(state)

async def setup(bot):
    await bot.add_cog(Scheduler(bot))