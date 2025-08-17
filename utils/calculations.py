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
    Applies chain reactions on the player's state dictionary.
    This is the core of the simulation, with non-linear effects and interdependencies.
    """
    logs = []

    # === 1. NATURAL RECOVERY & DECAY ===
    # Mental states naturally tend towards baseline
    state_dict['guilt'] = clamp(state_dict['guilt'] - 0.2, 0, 100)
    state_dict['shame'] = clamp(state_dict['shame'] - 0.15, 0, 100)
    state_dict['hopelessness'] = clamp(state_dict['hopelessness'] - 0.1, 0, 100)
    
    # Physical symptoms naturally improve
    state_dict['headache'] = clamp(state_dict['headache'] - 0.5, 0, 100)
    state_dict['muscle_tension'] = clamp(state_dict['muscle_tension'] - 0.3, 0, 100)
    state_dict['nausea'] = clamp(state_dict['nausea'] - 0.4, 0, 100)

    # === 2. ADDICTION MECHANICS ===
    # Calculate base withdrawal progression
    max_withdrawal = state_dict['physical_dependence'] * 0.8
    withdrawal_rate = (state_dict['substance_tolerance'] / 100.0) * 0.7
    state_dict['withdrawal_severity'] = clamp(
        state_dict['withdrawal_severity'] + withdrawal_rate,
        0,
        max_withdrawal
    )
    
    # Process withdrawal effects
    if state_dict['withdrawal_severity'] > 10:
        severity = state_dict['withdrawal_severity']
        severity_factor = severity / 100.0
        
        # Physical symptoms
        state_dict['tremors'] = clamp(state_dict['tremors'] + severity_factor * 0.8, 0, 100)
        state_dict['cold_sweats'] = clamp(state_dict['cold_sweats'] + severity_factor * 0.6, 0, 100)
        state_dict['headache'] = clamp(state_dict['headache'] + severity_factor * 0.5, 0, 100)
        
        # Mental effects
        state_dict['anxiety'] = clamp(state_dict['anxiety'] + severity_factor * 0.9, 0, 100)
        state_dict['concentration'] = clamp(state_dict['concentration'] - severity_factor * 1.2, 0, 100)
        state_dict['irritability'] = clamp(state_dict.get('irritability', 0) + severity_factor * 1.1, 0, 100)
        
        if severity > 60:
            logs.append("😖 Withdrawal symptoms are intense, affecting both body and mind.")

    # === 3. CRAVING DYNAMICS ===
    # Base craving calculation
    stress_impact = state_dict['stress'] * 0.3
    anxiety_impact = state_dict['anxiety'] * 0.2
    environmental_trigger = state_dict['environmental_stress'] * 0.15
    
    base_craving = (
        state_dict['withdrawal_severity'] * 0.4 +
        stress_impact +
        anxiety_impact +
        environmental_trigger +
        (time_since_last_smoke.total_seconds() / 400.0)
    )
    
    # Modify craving based on psychological factors
    if state_dict['mental_clarity'] < 50:
        base_craving *= 1.2
    if state_dict['social_trigger_level'] > 50:
        base_craving *= 1.3
    
    # Apply cravings to specific substances
    if state_dict['nicotine_addiction'] > 0:
        state_dict['craving_nicotine'] = clamp(base_craving * (state_dict['nicotine_addiction'] / 100), 0, 100)
    if state_dict['alcohol_addiction'] > 0:
        state_dict['craving_alcohol'] = clamp(base_craving * (state_dict['alcohol_addiction'] / 100), 0, 100)
    if state_dict['cannabis_addiction'] > 0:
        state_dict['craving_cannabis'] = clamp(base_craving * (state_dict['cannabis_addiction'] / 100), 0, 100)

    # === 4. PHYSICAL STATE INTERACTIONS ===
    # Fatigue effects
    if state_dict['fatigue'] > 70:
        fatigue_factor = (state_dict['fatigue'] - 70) / 30.0
        state_dict['energy'] = clamp(state_dict['energy'] - 1.2 * fatigue_factor, 0, 100)
        state_dict['mental_clarity'] = clamp(state_dict['mental_clarity'] - 1.0 * fatigue_factor, 0, 100)
        state_dict['concentration'] = clamp(state_dict['concentration'] - 1.5 * fatigue_factor, 0, 100)
        if state_dict['fatigue'] > 90:
            logs.append("😴 Extreme fatigue is affecting your mental performance.")

    # Comfort and environmental effects
    if state_dict['comfort'] < 40:
        comfort_factor = (40 - state_dict['comfort']) / 40.0
        state_dict['stress'] = clamp(state_dict['stress'] + 0.7 * comfort_factor, 0, 100)
        state_dict['muscle_tension'] = clamp(state_dict['muscle_tension'] + 0.5 * comfort_factor, 0, 100)

    # Temperature effects
    if abs(state_dict['temperature_comfort'] - 50) > 30:
        temp_discomfort = abs(state_dict['temperature_comfort'] - 50) - 30
        state_dict['stress'] = clamp(state_dict['stress'] + 0.3 * (temp_discomfort / 20), 0, 100)
        state_dict['concentration'] = clamp(state_dict['concentration'] - 0.4 * (temp_discomfort / 20), 0, 100)

    # === 5. VITAL NEEDS EFFECTS ===
    # Hunger effects
    if state_dict['hunger'] > 70:
        hunger_factor = (state_dict['hunger'] - 70) / 30.0
        state_dict['energy'] = clamp(state_dict['energy'] - hunger_factor * 1.0, 0, 100)
        state_dict['concentration'] = clamp(state_dict['concentration'] - hunger_factor * 1.2, 0, 100)
        state_dict['irritability'] = clamp(state_dict.get('irritability', 0) + hunger_factor * 1.5, 0, 100)

    # Thirst effects
    if state_dict['thirst'] > 60:
        thirst_factor = (state_dict['thirst'] - 60) / 40.0
        state_dict['headache'] = clamp(state_dict['headache'] + thirst_factor * 1.0, 0, 100)
        state_dict['mental_clarity'] = clamp(state_dict['mental_clarity'] - thirst_factor * 1.3, 0, 100)

    # Bladder effects
    if state_dict['bladder'] > 80:
        bladder_factor = (state_dict['bladder'] - 80) / 20.0
        state_dict['stress'] = clamp(state_dict['stress'] + bladder_factor * 1.2, 0, 100)
        state_dict['concentration'] = clamp(state_dict['concentration'] - bladder_factor * 1.0, 0, 100)
        if state_dict['bladder'] >= 100:
            state_dict['bladder'] = 0
            state_dict['hygiene'] = clamp(state_dict['hygiene'] - 50, 0, 100)
            state_dict['shame'] = clamp(state_dict['shame'] + 40, 0, 100)
            logs.append("� You couldn't hold it anymore...")

    # === 6. MENTAL STATE INTERACTIONS ===
    # Stress effects on physical symptoms
    if state_dict['stress'] > 60:
        stress_factor = (state_dict['stress'] - 60) / 40.0
        state_dict['muscle_tension'] = clamp(state_dict['muscle_tension'] + stress_factor * 0.8, 0, 100)
        state_dict['headache'] = clamp(state_dict['headache'] + stress_factor * 0.6, 0, 100)
        state_dict['blood_pressure'] = clamp(state_dict['blood_pressure'] + stress_factor * 10, 100, 160)

    # Anxiety effects
    if state_dict['anxiety'] > 50:
        anxiety_factor = (state_dict['anxiety'] - 50) / 50.0
        state_dict['concentration'] = clamp(state_dict['concentration'] - anxiety_factor * 1.0, 0, 100)
        state_dict['decision_making'] = clamp(state_dict['decision_making'] - anxiety_factor * 1.2, 0, 100)
        state_dict['social_anxiety'] = clamp(state_dict['social_anxiety'] + anxiety_factor * 0.8, 0, 100)
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