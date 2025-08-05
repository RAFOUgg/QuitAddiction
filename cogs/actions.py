# --- cogs/actions.py ---

from discord.ext import commands
import discord
from discord import app_commands 
from utils.calculations import apply_action_effects
from db.database import SessionLocal
from db.models import ServerState, PlayerProfile

class Actions(commands.Cog):
    """Gestion des actions du joueur (manger, boire, fumer...)."""

    def __init__(self, bot):
        self.bot = bot
        self.pending_effects = []

    @commands.command()
    async def manger(self, ctx):
        """Le cuisinier mange un repas de base."""
        db = SessionLocal()
        player = db.query(PlayerProfile).filter_by(guild_id=str(ctx.guild.id), user_id=str(ctx.author.id)).first()
        
        if not player:
            await ctx.send("Tu n'as pas encore de profil de cuisinier. Commence par la commande `!startgame` (si disponible) ou assure-toi d'être prêt.")
            db.close()
            return

        # On applique l'effet de base, mais il faudrait synchroniser avec le dictionnaire d'état réel du joueur.
        # Ici, on simule l'effet, mais pour un vrai impact, il faudrait mettre à jour 'player'.
        # Pour l'instant, le dictionnaire retourné par apply_action_effects n'est pas utilisé pour modifier le joueur.
        effects = apply_action_effects({"HUNGER": player.hunger}, "manger") # Ex: Appliquer un effet sur la faim

        # Exemple de mise à jour manuelle (à faire de manière plus structurée avec les effets retournés)
        player.hunger = max(0.0, player.hunger - 30.0) # Réduit la faim
        player.energy = min(100.0, player.energy + 10.0) # Augmente l'énergie
        player.happiness = min(100.0, player.happiness + 15.0) # Augmente le bonheur
        player.stress = max(0.0, player.stress - 5.0) # Réduit le stress

        db.commit()
        await ctx.send(f"🍽️ {ctx.author.mention} a mangé et se sent mieux ! (Faim réduite, énergie et bonheur augmentés)")
        db.close()

    @commands.command()
    async def fumer(self, ctx, type_fumette: str):
        """
        Permet au cuisinier de fumer différents types de substances.
        Types possibles : leger, lourd, dab
        """
        db = SessionLocal()
        player = db.query(PlayerProfile).filter_by(guild_id=str(ctx.guild.id), user_id=str(ctx.author.id)).first()
        
        if not player:
            await ctx.send("Tu n'as pas encore de profil de cuisinier. Commence par la commande `!startgame` (si disponible) ou assure-toi d'être prêt.")
            db.close()
            return

        if type_fumette.lower() not in ["leger", "lourd", "dab"]:
            await ctx.send("Type de fumette invalide. Choix possibles : `leger`, `lourd`, `dab`.")
            db.close()
            return

        action_key = f"fumer_{type_fumette.lower()}"
        effects = apply_action_effects({"player_state": player.__dict__}, action_key) # Passer l'état du joueur pour un calcul plus précis si nécessaire

        # Appliquer les effets (exemple basique, les clés d'effets doivent correspondre aux attributs du joueur)
        player.happiness = min(100.0, player.happiness + effects.get("HAPPY", 0))
        player.stress = max(0.0, player.stress + effects.get("STRESS", 0))
        player.energy = max(0.0, player.energy + effects.get("ENERGY", 0))
        player.sanity = max(0.0, player.sanity + effects.get("MENT", 0)) # Assumer que MENT dans effects correspond à sanity
        player.tox = min(100.0, player.tox + effects.get("TOX", 0))
        player.addiction = min(100.0, player.addiction + effects.get("ADDICTION", 0.0))

        # Si l'effet `TRIP` est présent, on pourrait l'appliquer
        if "TRIP" in effects:
            player.intoxication_level = min(100.0, player.intoxication_level + effects["TRIP"])

        db.commit()
        await ctx.send(f"💨 {ctx.author.mention} a fumé du {type_fumette.lower()}. Effets ressentis...")
        db.close()

async def setup(bot):
    await bot.add_cog(Actions(bot))