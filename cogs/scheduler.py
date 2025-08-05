# --- cogs/scheduler.py ---

from discord.ext import commands, tasks
from db.database import SessionLocal # Assurez-vous que c'est le bon import
from db.models import ServerState, PlayerProfile # Nécessaire pour accéder aux données des joueurs et serveurs
import datetime
import math # Pour les calculs de temps

# Importer les utilitaires de calcul qui seront utilisés par le scheduler
from utils.calculations import apply_action_effects, chain_reactions # Supposons que ces fonctions existent

class Scheduler(commands.Cog):
    """Tâches automatiques pour la dégradation des statistiques et les effets différés."""

    def __init__(self, bot):
        self.bot = bot
        self.pending_effects = [] # Peut-être utile pour des effets différés plus complexes

    async def cog_load(self):
        """Se lance quand le cog est chargé."""
        # Démarre la tâche de tick si elle n'est pas déjà en cours
        if not self.tick.is_running():
            self.tick.start()
        print("Scheduler tick started.")

    def cog_unload(self):
        """Annule la tâche quand le cog est déchargé."""
        if self.tick.is_running():
            self.tick.cancel()
        print("Scheduler tick cancelled.")

    # La tâche principale qui s'exécute périodiquement
    @tasks.loop(minutes=1) # On vérifie chaque minute, mais la logique interne déterminera quand agir
    async def tick(self):
        current_time = datetime.datetime.utcnow()
        db = SessionLocal()
        try:
            # 1. Récupérer tous les états de serveurs où le jeu est lancé
            server_states = db.query(ServerState).filter(ServerState.game_started == True).all()
            
            for server_state in server_states:
                # Si le dernier_update n'est pas défini (première partie), on l'initialise à current_time
                # pour éviter une dégradation massive au tout premier tick.
                if not server_state.last_update:
                    server_state.last_update = current_time

                # Calculer le temps écoulé depuis la dernière mise à jour pour ce serveur
                time_since_last_update = current_time - server_state.last_update
                
                # Déterminer combien d'intervalles de 'game_tick_interval_minutes' se sont écoulés
                interval_minutes = server_state.game_tick_interval_minutes
                # S'assurer qu'on a un intervalle valide, sinon utiliser une valeur par défaut
                if not interval_minutes or interval_minutes <= 0:
                    interval_minutes = 30 # Valeur par défaut si elle est manquante ou invalide

                # Calculer le nombre de ticks de dégradation à appliquer
                # Ex: si intervalle=30min, et il s'est passé 95min, on applique 95/30 = 3.16 ticks. On prend floor pour les ticks entiers.
                num_ticks_to_apply = math.floor(time_since_last_update.total_seconds() / 60 / interval_minutes)
                
                if num_ticks_to_apply > 0:
                    # Charger tous les joueurs actifs de ce serveur
                    player_profiles = db.query(PlayerProfile).filter_by(guild_id=server_state.guild_id).all()
                    
                    for player in player_profiles:
                        # Pour chaque tick, appliquer les dégradations et les conséquences
                        # On répète la logique pour chaque tick calculé pour être plus précis sur les effets cumulés
                        for _ in range(num_ticks_to_apply):
                            # --- Appliquer les dégradations de base ---
                            player.hunger = min(100.0, player.hunger + (server_state.degradation_rate_hunger / interval_minutes * 60)) # Taux par minute, pas par tick.
                            player.thirst = min(100.0, player.thirst + (server_state.degradation_rate_thirst / interval_minutes * 60))
                            player.bladder = min(100.0, player.bladder + (server_state.degradation_rate_bladder / interval_minutes * 60))
                            player.energy = max(0.0, player.energy - (server_state.degradation_rate_energy / interval_minutes * 60))
                            player.stress = min(100.0, player.stress + (server_state.degradation_rate_stress / interval_minutes * 60))
                            player.boredom = min(100.0, player.boredom + (server_state.degradation_rate_boredom / interval_minutes * 60))
                            
                            # Effets de sevrage (simplifié : si addiction > seuil et sevrage actif)
                            if player.substance_addiction_level > 10 and player.withdrawal_severity > 0:
                                # Ces effets dépendent de player.withdrawal_severity, qui lui-même pourrait augmenter avec l'addiction ou les manques.
                                player.stress = min(100.0, player.stress + player.withdrawal_severity * 0.5) 
                                player.sanity = max(0.0, min(100.0, player.sanity - player.withdrawal_severity * 0.2)) 
                                player.pain = max(0.0, min(100.0, player.pain + player.withdrawal_severity * 0.3))
                                player.energy = max(0.0, player.energy - player.withdrawal_severity * 0.4)
                                player.happiness = max(-100.0, player.happiness - player.withdrawal_severity * 0.6) # Humeur négative

                            # Application des taux de dégradation de base pour addiction et toxines (peut-être liés aux actions plutôt qu'au temps)
                            # Pour l'instant, on peut garder une petite dégradation si nécessaire
                            # player.substance_addiction_level = min(100.0, player.substance_addiction_level + server_state.degradation_rate_addiction_base)
                            # player.intoxication_level = min(100.0, player.intoxication_level + server_state.degradation_rate_toxins_base)

                            # --- Utiliser chain_reactions pour les effets complexes ---
                            # Préparer un dictionnaire d'état pour les calculs. LES NOMS DES CLÉS DOIVENT ÊTRE CEUX ATTENDUS PAR chain_reactions
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
                                "ADDICTION": player.substance_addiction_level,
                                "TOX": player.intoxication_level, # Mapper player.intoxication_level à TOX
                                "TRIP": player.intoxication_level, # mapper player.intoxication_level à TRIP
                                "BORDEOM": player.boredom,
                                # Assurez-vous que toutes les clés utilisées dans chain_reactions correspondent à ce dictionnaire
                            }

                            chain_reactions(state_for_calc) # Applique les réactions en chaîne au dictionnaire

                            # --- MAJ les attributs du PlayerProfile AVEC les valeurs calculées ---
                            # Appliquer les changements retournés par chain_reactions, en clampant les valeurs
                            player.health = max(0.0, min(100.0, state_for_calc.get("HEALTH", player.health)))
                            player.pain = max(0.0, min(100.0, state_for_calc.get("PAIN", player.pain)))
                            player.stress = max(0.0, min(100.0, state_for_calc.get("STRESS", player.stress)))
                            player.sanity = max(0.0, min(100.0, state_for_calc.get("MENT", player.sanity))) # Mapper MENT ici
                            player.happiness = max(-100.0, min(100.0, state_for_calc.get("HAPPY", player.happiness)))
                            player.boredom = max(0.0, min(100.0, state_for_calc.get("BORDEOM", player.boredom)))
                            player.intoxication_level = max(0.0, min(100.0, state_for_calc.get("TRIP", player.intoxication_level))) # Mapper TRIP et TOX

                            # Mettre à jour le last_update du joueur pour le prochain calcul
                            player.last_update = current_time
                        
                    # Après avoir traité tous les joueurs pour ce serveur, mettre à jour last_update du serveur
                    # pour refléter le moment où le dernier tick a été appliqué.
                    server_state.last_update = current_time

            db.commit() # Sauvegarde des changements pour tous les serveurs/joueurs

        except ImportError as ie:
            print(f"Scheduler Error: ImportError during cog load/tick - {ie}")
            # Si un cog ou une bibliothèque essentielle n'est pas trouvé, on peut arrêter la tâche
            if self.tick.is_running():
                self.tick.cancel()
        except NameError as ne:
            print(f"Scheduler Error: NameError - {ne}")
            # Problème avec des variables non définies, peut-être dans les modèles ou les utilitaires
            if self.tick.is_running():
                self.tick.cancel()
        except Exception as e:
            print(f"Erreur critique dans Scheduler.tick : {e}")
            db.rollback() # Annuler les transactions en cours en cas d'erreur
        finally:
            db.close() # Toujours fermer la session DB

    @tick.before_loop
    async def before_tick(self):
        """Attend que le bot soit prêt avant de démarrer la boucle."""
        await self.bot.wait_until_ready()
        print("Scheduler prêt pour le tick.")

async def setup(bot):
    await bot.add_cog(Scheduler(bot))