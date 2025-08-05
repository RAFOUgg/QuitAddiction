# --- cogs/scheduler.py ---

from discord.ext import commands, tasks
from db.database import SessionLocal
from db.models import ServerState, PlayerProfile # Assurez-vous que ces imports sont corrects
import datetime
import math

# Importez vos fonctions de calcul
from utils.calculations import apply_action_effects, chain_reactions 

class Scheduler(commands.Cog):
    """Tâches automatiques pour la dégradation des statistiques et les effets différés."""

    def __init__(self, bot):
        self.bot = bot
        self.pending_effects = [] # Peut être utilisé pour des effets différés spécifiques à un joueur/serveur

    async def cog_load(self):
        """Se lance quand le cog est chargé."""
        # Démarrer la tâche loopée si elle n'est pas déjà en cours
        if not self.tick.is_running():
            self.tick.start()
        print("Scheduler tick started.")

    def cog_unload(self):
        """Annule la tâche quand le cog est déchargé."""
        if self.tick.is_running():
            self.tick.cancel()
        print("Scheduler tick cancelled.")

    # La boucle s'exécute toutes les minutes. La logique interne décide quand appliquer les dégradations.
    @tasks.loop(minutes=1) 
    async def tick(self):
        current_time = datetime.datetime.utcnow()
        db = SessionLocal()
        try:
            # 1. Chercher tous les 'ServerState' où une partie est activement lancée
            server_states = db.query(ServerState).filter(ServerState.game_started == True).all()
            
            for server_state in server_states:
                # S'assurer que last_update est défini, sinon initialiser pour éviter des dégradations massives au premier démarrage
                if not server_state.last_update:
                    server_state.last_update = current_time

                # Calculer le temps écoulé depuis la dernière mise à jour de ce serveur (en minutes)
                time_since_last_update = current_time - server_state.last_update
                
                # Déterminer combien d'intervalles de 'game_tick_interval_minutes' se sont écoulés
                interval_minutes = server_state.game_tick_interval_minutes
                if not interval_minutes or interval_minutes <= 0:
                    interval_minutes = 30 # Valeur par défaut si elle est manquante ou invalide

                # Calculer le nombre de "ticks" de dégradation complets à appliquer
                # Ex: si intervalle=30min, et il s'est passé 95min, on applique floor(95/30) = 3 ticks.
                num_ticks_to_apply = math.floor(time_since_last_update.total_seconds() / 60 / interval_minutes)
                
                if num_ticks_to_apply > 0:
                    # Charger tous les joueurs de ce serveur
                    player_profiles = db.query(PlayerProfile).filter_by(guild_id=server_state.guild_id).all()
                    
                    for player in player_profiles:
                        # On applique la dégradation pour CHAQUE tick calculé
                        for _ in range(num_ticks_to_apply):
                            # --- Appliquer les dégradations de base ---
                            # Les taux sont par TICK. Pour les appliquer sur une période plus courte (comme chaque minute),
                            # il faut diviser le taux par le nombre de minutes dans un tick.
                            # Ex: Si TauxHunger = 10/tick et intervalle=30min, alors par minute c'est 10/30.
                            
                            hunger_change = server_state.degradation_rate_hunger / interval_minutes
                            thirst_change = server_state.degradation_rate_thirst / interval_minutes
                            bladder_change = server_state.degradation_rate_bladder / interval_minutes
                            energy_change = -(server_state.degradation_rate_energy / interval_minutes)
                            stress_change = server_state.degradation_rate_stress / interval_minutes
                            boredom_change = server_state.degradation_rate_boredom / interval_minutes
                            
                            # Appliquer les changements aux attributs du joueur, en clampant les valeurs
                            player.hunger = self.clamp(player.hunger + hunger_change, 0.0, 100.0)
                            player.thirst = self.clamp(player.thirst + thirst_change, 0.0, 100.0)
                            player.bladder = self.clamp(player.bladder + bladder_change, 0.0, 100.0)
                            player.energy = self.clamp(player.energy + energy_change, 0.0, 100.0)
                            player.stress = self.clamp(player.stress + stress_change, 0.0, 100.0)
                            player.boredom = self.clamp(player.boredom + boredom_change, 0.0, 100.0)

                            # --- Effets de Sevrage (si addiction > 0 et sevrage actif) ---
                            # Ceci doit être calculé en fonction de player.substance_addiction_level et player.withdrawal_severity
                            # et potentiellement de la dernière consommation.
                            # Simplification : si sevrage actif, appliquer malus.
                            if player.withdrawal_severity > 0: # Ceci sera peut-être mis à jour par d'autres logiques
                                # Utiliser player.sanity pour MENT et player.stress pour STRESS
                                player.stress = self.clamp(player.stress + player.withdrawal_severity * 0.5, 0.0, 100.0) 
                                player.sanity = self.clamp(player.sanity - player.withdrawal_severity * 0.2, 0.0, 100.0) 
                                player.pain = self.clamp(player.pain + player.withdrawal_severity * 0.3, 0.0, 100.0)
                                player.energy = self.clamp(player.energy - player.withdrawal_severity * 0.4, 0.0, 100.0)
                                player.happiness = self.clamp(player.happiness - player.withdrawal_severity * 0.6, -100.0, 100.0) # Humeur négative

                            # --- Taux de dégradation base Addiction/Toxines ---
                            # Ces taux sont souvent plus liés aux actions (consommation) qu'au temps pur,
                            # mais si on veut une lente dégradation naturelle, on l'applique ici.
                            # player.substance_addiction_level = self.clamp(player.substance_addiction_level + server_state.degradation_rate_addiction_base, 0.0, 100.0)
                            # player.intoxication_level = self.clamp(player.intoxication_level + server_state.degradation_rate_toxins_base, 0.0, 100.0)
                            
                            # --- Appliquer les réactions en chaîne via les utilitaires ---
                            # Construire le dictionnaire d'état pour les calculs externes.
                            # Les CLÉS doivent correspondre à ce qu'attend la fonction chain_reactions.
                            state_for_calc = {
                                "HEALTH": player.health,
                                "HUNGER": player.hunger,
                                "THIRST": player.thirst,
                                "ENERGY": player.energy,
                                "PAIN": player.pain,
                                "BLADDER": player.bladder,
                                "STRESS": player.stress,
                                "MENT": player.sanity, # Mapper player.sanity à MENT
                                "HAPPY": player.happiness,
                                "BORDEOM": player.boredom,
                                "ADDICTION": player.substance_addiction_level,
                                "TOX": player.intoxication_level, # Mapper player.intoxication_level à TOX
                                "TRIP": player.intoxication_level, # Mapper player.intoxication_level à TRIP
                                # Assurez-vous que toutes les clés utilisées dans chain_reactions sont présentes ici.
                            }
                            
                            # Appel de la fonction qui calcule les conséquences (et modifie state_for_calc)
                            chain_reactions(state_for_calc) 

                            # --- MAJ les attributs du PlayerProfile AVEC les résultats de chain_reactions ---
                            # Assurez-vous que les clés utilisées dans chain_reactions correspondent aux attributs du joueur
                            player.health = self.clamp(state_for_calc.get("HEALTH", player.health), 0.0, 100.0)
                            player.pain = self.clamp(state_for_calc.get("PAIN", player.pain), 0.0, 100.0)
                            player.stress = self.clamp(state_for_calc.get("STRESS", player.stress), 0.0, 100.0)
                            player.sanity = self.clamp(state_for_calc.get("MENT", player.sanity), 0.0, 100.0)
                            player.happiness = self.clamp(state_for_calc.get("HAPPY", player.happiness), -100.0, 100.0)
                            player.boredom = self.clamp(state_for_calc.get("BORDEOM", player.boredom), 0.0, 100.0)
                            player.intoxication_level = self.clamp(state_for_calc.get("TRIP", player.intoxication_level), 0.0, 100.0)
                            # Mettre à jour TOX et ADDICTION si elles sont modifiées par chain_reactions
                            player.tox = self.clamp(state_for_calc.get("TOX", player.tox), 0.0, 100.0)
                            player.substance_addiction_level = self.clamp(state_for_calc.get("ADDICTION", player.substance_addiction_level), 0.0, 100.0)
                            
                            # Mettre à jour le last_update du joueur pour le prochain calcul
                            player.last_update = current_time
                        
                    # Après avoir traité tous les joueurs pour ce serveur, MAJ le last_update du serveur
                    # Cela permet de savoir quand la prochaine évaluation globale doit commencer.
                    server_state.last_update = current_time

            db.commit() # Sauvegarder les changements globaux

        except ImportError as ie:
            print(f"Scheduler Error: ImportError - {ie}. Assurez-vous que les imports de cogs/scheduler.py sont corrects.")
            if self.tick.is_running(): self.tick.cancel()
        except NameError as ne:
            print(f"Scheduler Error: NameError - {ne}. Vérifiez que toutes les variables et fonctions sont définies.")
            if self.tick.is_running(): self.tick.cancel()
        except Exception as e:
            print(f"Erreur critique dans Scheduler.tick : {e}")
            db.rollback() # Annuler les transactions en cours en cas d'erreur
        finally:
            db.close() # Toujours fermer la session DB

    # Fonction d'aide pour le clampage des valeurs
    def clamp(self, value, min_val, max_val):
        return max(min_val, min(max_val, value))

    # La méthode `before_loop` est essentielle
    @tick.before_loop
    async def before_tick(self):
        """Attend que le bot soit prêt avant de démarrer la boucle de tick."""
        await self.bot.wait_until_ready()
        print("Scheduler prêt pour le tick.")

async def setup(bot):
    await bot.add_cog(Scheduler(bot))