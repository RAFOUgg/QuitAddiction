# --- utils/calculations.py (REFACTORED WITH NEW STATS) ---

from .helpers import clamp
from datetime import datetime
from typing import Tuple

def update_work_stats(player, game_time) -> Tuple[float, str]:
    """
    Met à jour les statistiques de travail du joueur et calcule l'impact sur la performance
    """
    perf_impact = 0
    message = ""

    # Vérification des retards
    if game_time.hour == 9 and game_time.minute > 0:
        minutes_late = game_time.minute
        player.total_minutes_late += minutes_late
        perf_impact -= (minutes_late / 60) * 10  # -10% par heure de retard
        if minutes_late > 15:
            message = "Retard important ! Impact négatif sur la performance."

    # Gestion des pauses
    if player.last_break_start:
        break_duration = (datetime.now() - player.last_break_start).total_seconds() / 60
        if break_duration > 15:  # Pause standard de 15 minutes
            excess_time = break_duration - 15
            player.total_break_time += excess_time
            perf_impact -= (excess_time / 60) * 5  # -5% par heure de pause excessive

    # Impact du temps de travail perdu sur la performance
    total_lost_time = player.total_minutes_late + player.total_break_time
    work_day_minutes = (2.5 + 4.5) * 60  # 7h de travail par jour
    lost_productivity = (total_lost_time / work_day_minutes) * 100

    if lost_productivity > 20:
        message = "Temps de travail perdu important. Votre performance est affectée."
        perf_impact -= lost_productivity / 2

    return perf_impact, message

def chain_reactions(state_dict: dict, time_since_last_smoke) -> Tuple[dict, list]:
    """
    Applique les réactions en chaîne sur un dictionnaire d'état du joueur.
    C'est le cœur de la simulation, avec des effets non-linéaires et des interdépendances.
    """
    logs = []

    
    # --- 0. DECAY & REGENERATION NATURELS ---
    # La culpabilité s'estompe avec le temps
    state_dict['guilt'] = clamp(state_dict['guilt'] - 0.2, 0, 100) 
    # Le mal de tête s'estompe aussi, s'il n'est pas entretenu
    state_dict['headache'] = clamp(state_dict['headache'] - 0.5, 0, 100) 

    # --- 1. MÉCANISMES D'ADDICTION & DE MANQUE ---
    base_withdrawal_increase = (state_dict['substance_addiction_level'] / 100.0) * 0.5
    state_dict['withdrawal_severity'] = clamp(state_dict['withdrawal_severity'] + base_withdrawal_increase, 0, 100)
    
    if state_dict['withdrawal_severity'] > 10:
        severity = state_dict['withdrawal_severity']
        # Le manque génère du stress, et ce de plus en plus fort.
        state_dict['stress'] = clamp(state_dict['stress'] + (severity / 100.0) * 0.7, 0, 100)
        # Le manque pèse sur le moral
        state_dict['happiness'] = clamp(state_dict['happiness'] - (severity / 100.0) * 0.4, 0, 100)
        # Le manque sape la volonté
        state_dict['willpower'] = clamp(state_dict['willpower'] - (severity / 100.0) * 1.2, 0, 100)
        # Le manque cause des symptômes physiques
        state_dict['nausea'] = clamp(state_dict['nausea'] + (severity / 100.0) * 0.3, 0, 100)
        if severity > 60:
            logs.append("😖 Le manque vous ronge, votre volonté s'effrite.")
    
    # Calcul de l'envie (craving) basé sur le manque, le temps, et la volonté faible
    craving_factor = state_dict['withdrawal_severity'] + (time_since_last_smoke.total_seconds() / 400.0)
    if state_dict['willpower'] < 30:
        craving_factor *= 1.5 # Une volonté faible rend l'envie obsédante
    state_dict['craving_nicotine'] = clamp(craving_factor, 0, 100)

    # --- 2. CONSÉQUENCES DES ÉTATS PHYSIQUES ---
    if state_dict['fatigue'] > 70:
        # La fatigue dégrade la performance, la volonté et l'énergie
        fatigue_effect = (state_dict['fatigue'] - 70) / 30.0 # scale from 0 to 1
        state_dict['energy'] = clamp(state_dict['energy'] - 1.0 * fatigue_effect, 0, 100)
        state_dict['willpower'] = clamp(state_dict['willpower'] - 0.8 * fatigue_effect, 0, 100)
        state_dict['job_performance'] = clamp(state_dict['job_performance'] - 1.5 * fatigue_effect, 0, 100)
        if state_dict['fatigue'] > 90: logs.append("😴 L'épuisement vous paralyse.")

    if state_dict['hygiene'] < 30:
        hygiene_effect = (30 - state_dict['hygiene']) / 30.0 # scale de 0 à 1
        state_dict['immune_system'] = clamp(state_dict['immune_system'] - 0.5 * hygiene_effect, 0, 100)
        state_dict['happiness'] = clamp(state_dict['happiness'] - 0.4 * hygiene_effect, 0, 100)
        if state_dict['hygiene'] < 10: logs.append("🚿 Vous vous sentez vraiment sale, ça pèse sur le moral.")
    
    if state_dict['hunger'] > 80: state_dict['stress'] += 0.5
    if state_dict['thirst'] > 70: state_dict['headache'] += 0.8
    if state_dict['bladder'] > 85: state_dict['stress'] += 0.6; state_dict['pain'] += 0.2
    if state_dict.get('bladder', 0) >= 100:
        state_dict['bladder'] = 0 # L'accident vide la vessie
        state_dict['hygiene'] = clamp(state_dict.get('hygiene', 100) - 50, 0, 100)
        state_dict['happiness'] = clamp(state_dict.get('happiness', 50) - 30, 0, 100) # C'est humiliant
        state_dict['stress'] = clamp(state_dict.get('stress', 0) + 15, 0, 100)
        logs.append(" humiliant... Vous n'avez pas pu vous retenir à temps.")
    if state_dict['bowels'] > 80:
        state_dict['stress'] = clamp(state_dict['stress'] + 0.4, 0, 100)
        state_dict['pain'] = clamp(state_dict['pain'] + 0.5, 0, 100) # C'est plus douloureux
        if state_dict['bowels'] > 95:
            logs.append("💩 Une crampe douloureuse vous rappelle une urgence intestinale !")
    # --- 3. CONSÉQUENCES DE L'ÉTAT MENTAL ---
    if state_dict['stress'] > 50:
        stress_effect = (state_dict['stress'] - 50) / 50.0 # scale
        state_dict['happiness'] = clamp(state_dict['happiness'] - 0.6 * stress_effect, 0, 100)
        state_dict['immune_system'] = clamp(state_dict['immune_system'] - 0.7 * stress_effect, 0, 100)
        state_dict['headache'] = clamp(state_dict['headache'] + 0.5 * stress_effect, 0, 100)
        # Cercle vicieux : le stress donne envie de solutions rapides
        state_dict['craving_alcohol'] = clamp(state_dict['craving_alcohol'] + 1.0 * stress_effect, 0, 100)
        if state_dict['stress'] > 80: logs.append("😨 Le stress devient insupportable.")

    # --- 4. RÉGÉNÉRATION ET ÉQUILIBRE ---
    if state_dict['stress'] < 40 and state_dict['happiness'] > 50 and state_dict['fatigue'] < 50:
        state_dict['willpower'] = clamp(state_dict['willpower'] + 0.5, 0, 100)
        state_dict['health'] = clamp(state_dict['health'] + 0.1, 0, 100)

    # --- 5. STATS COMPOSITES POUR L'AFFICHAGE ---
    state_dict['stomachache'] = clamp((state_dict['hunger'] * 0.5 + state_dict['nausea']), 0, 100)
    
    return state_dict, logs

def update_job_performance(player, game_time=None):
    performance_modifier = 0

    # Impact des stats de travail
    if game_time:
        work_impact, message = update_work_stats(player, game_time)
        performance_modifier += work_impact

    # Impact des stats du joueur
    # Volonté (plus importante maintenant)
    performance_modifier += (player.willpower - 50) / 75  # -0.67 à +0.67
    
    # Santé
    performance_modifier += (player.health - 50) / 100  # -0.5 à +0.5
    
    # Stress (impact plus important)
    stress_impact = player.stress / 100  # 0 à 1
    performance_modifier -= stress_impact * 2  # jusqu'à -2
    
    # Fatigue
    if hasattr(player, 'fatigue'):
        fatigue_impact = player.fatigue / 100  # 0 à 1
        performance_modifier -= fatigue_impact * 1.5  # jusqu'à -1.5

    # Intoxication
    if hasattr(player, 'intoxication_level'):
        intox_impact = player.intoxication_level / 100  # 0 à 1
        performance_modifier -= intox_impact * 3  # jusqu'à -3
        
        if player.intoxication_level > 50:
            performance_modifier -= 5  # Pénalité supplémentaire pour forte intoxication

    # Application des modifications avec un système de momentum
    # La performance change plus lentement pour plus de réalisme
    current_perf = player.job_performance
    target_perf = clamp(current_perf + performance_modifier, 0, 100)
    
    # La performance change de maximum 5 points par mise à jour
    max_change = 5
    actual_change = clamp(target_perf - current_perf, -max_change, max_change)
    
    player.job_performance = clamp(current_perf + actual_change, 0, 100)