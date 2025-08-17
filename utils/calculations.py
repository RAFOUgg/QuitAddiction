# --- utils/calculations.py (REFACTORED WITH NEW STATS) ---

from .helpers import clamp
from datetime import datetime
from typing import Tuple
import random  # Pour la variabilité de l'humeur

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

def calculate_overall_mood(player) -> Tuple[float, str, str]:
    """
    Calcule l'humeur générale du personnage basée sur tous les facteurs émotionnels.
    Retourne un tuple: (score_humeur, emoji_humeur, description_humeur)
    """
    # Facteurs positifs
    positive_factors = [
        player.happiness * 1.2,      # Plus fort impact
        player.joy * 1.1,
        player.satisfaction * 1.0,
        player.enthusiasm * 0.9,
        player.serenity * 0.8
    ]
    
    # Facteurs négatifs
    negative_factors = [
        player.anxiety * 1.2,        # Plus fort impact
        player.depression * 1.3,     # Impact très fort
        player.stress * 1.1,
        player.anger * 1.0,
        player.fear * 0.9,
        player.frustration * 0.8,
        player.irritability * 0.7
    ]

    # Calculer les moyennes pondérées
    positive_score = sum(positive_factors) / (5 * 1.2)  # Normalisé à 100
    negative_score = sum(negative_factors) / (7 * 1.3)  # Normalisé à 100

    # Facteurs de stabilité
    stability_factor = (player.emotional_stability / 100) * 0.8
    resilience_factor = (player.emotional_resilience / 100) * 0.2
    stability_score = (stability_factor + resilience_factor) * 100

    # Calcul du score final (0-100)
    mood_score = (
        (positive_score * 0.4) +         # 40% impact positif
        ((100 - negative_score) * 0.4) + # 40% impact négatif (inversé)
        (stability_score * 0.2)          # 20% stabilité
    )

    # Déterminer l'humeur basée sur le score et la volatilité
    volatility = player.mood_volatility / 100
    mood_variance = (100 - mood_score) * volatility

    # Ajuster le score avec la variance
    final_score = max(0, min(100, mood_score + ((-mood_variance/2) + (mood_variance * random.random()))))

    # Définir l'emoji et la description
    if final_score >= 90:
        return final_score, "🤩", "Euphorique"
    elif final_score >= 80:
        return final_score, "😊", "Très Heureux"
    elif final_score >= 70:
        return final_score, "😌", "Content"
    elif final_score >= 60:
        return final_score, "🙂", "Plutôt Bien"
    elif final_score >= 50:
        return final_score, "😐", "Neutre"
    elif final_score >= 40:
        return final_score, "🙁", "Morose"
    elif final_score >= 30:
        return final_score, "😔", "Triste"
    elif final_score >= 20:
        return final_score, "😢", "Déprimé"
    else:
        return final_score, "😭", "Au plus bas"


def process_activity_impact(player, activity_type: str, duration_minutes: int) -> list:
    """
    Traite l'impact d'une activité sur les stats du joueur
    """
    messages = []
    
    # Base de modification pour chaque activité
    activity_impacts = {
        "sport": {
            "energy": -15,
            "stamina": +5,
            "health": +3,
            "stress": -10,
            "mood_volatility": -5,
            "emotional_stability": +2,
            "physical_fitness": +4,
            "mental_clarity": +8,
        },
        "meditation": {
            "stress": -15,
            "emotional_stability": +4,
            "mental_clarity": +10,
            "concentration": +8,
            "mood_volatility": -8,
            "anxiety": -12,
            "serenity": +10,
        },
        "social": {
            "social_energy": -10,
            "loneliness": -20,
            "social_anxiety": -5,
            "happiness": +8,
            "emotional_stability": +2,
            "stress": -5,
        },
        "work": {
            "mental_clarity": -5,
            "energy": -10,
            "stress": +8,
            "cognitive_load": +15,
            "decision_making": +2,
        },
        "rest": {
            "energy": +15,
            "fatigue": -20,
            "stress": -8,
            "mental_clarity": +5,
            "cognitive_load": -10,
        }
    }

    if activity_type in activity_impacts:
        # Calculer le facteur de durée (1 pour 30 minutes)
        duration_factor = duration_minutes / 30.0
        
        # Appliquer les modifications avec le facteur de durée
        for stat, value in activity_impacts[activity_type].items():
            if hasattr(player, stat):
                current_value = getattr(player, stat)
                new_value = clamp(current_value + (value * duration_factor), 0, 100)
                setattr(player, stat, new_value)
                
                # Générer des messages pour les changements significatifs
                if abs(new_value - current_value) > 15:
                    if value > 0:
                        messages.append(f"📈 {stat.replace('_', ' ').title()} s'améliore significativement")
                    else:
                        messages.append(f"📉 {stat.replace('_', ' ').title()} diminue notablement")

        # Effets spéciaux selon la durée
        if duration_minutes > 120:  # Activité longue
            messages.append("⚠️ Cette longue activité vous a particulièrement fatigué")
            player.fatigue = clamp(player.fatigue + 20, 0, 100)
            player.energy = clamp(player.energy - 15, 0, 100)

    return messages

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

    # === 4. PHYSICAL & MENTAL STATE INTERACTIONS ===
    # Fatigue effects
    if state_dict['fatigue'] > 70:
        fatigue_factor = (state_dict['fatigue'] - 70) / 30.0
        state_dict['energy'] = clamp(state_dict['energy'] - 1.2 * fatigue_factor, 0, 100)
        state_dict['mental_clarity'] = clamp(state_dict['mental_clarity'] - 1.0 * fatigue_factor, 0, 100)
        state_dict['concentration'] = clamp(state_dict['concentration'] - 1.5 * fatigue_factor, 0, 100)
        state_dict['cognitive_load'] = clamp(state_dict['cognitive_load'] + 1.0 * fatigue_factor, 0, 100)
        if state_dict['fatigue'] > 90:
            logs.append("😴 Extreme fatigue is affecting your mental performance.")

    # Comfort and environmental effects
    if state_dict['comfort'] < 40:
        comfort_factor = (40 - state_dict['comfort']) / 40.0
        state_dict['stress'] = clamp(state_dict['stress'] + 0.7 * comfort_factor, 0, 100)
        state_dict['muscle_tension'] = clamp(state_dict['muscle_tension'] + 0.5 * comfort_factor, 0, 100)
        state_dict['environmental_stress'] = clamp(state_dict['environmental_stress'] + 0.6 * comfort_factor, 0, 100)

    # === 5. SOCIAL & COGNITIVE INTERACTIONS ===
    # Social anxiety effects
    if state_dict['social_anxiety'] > 60:
        social_factor = (state_dict['social_anxiety'] - 60) / 40.0
        state_dict['social_energy'] = clamp(state_dict['social_energy'] - 1.0 * social_factor, 0, 100)
        state_dict['environmental_stress'] = clamp(state_dict['environmental_stress'] + 0.8 * social_factor, 0, 100)
        state_dict['emotional_stability'] = clamp(state_dict['emotional_stability'] - 0.5 * social_factor, 0, 100)
        if state_dict['social_anxiety'] > 80:
            logs.append("😰 High social anxiety is draining your social energy.")

    # Cognitive load effects
    if state_dict['cognitive_load'] > 70:
        cognitive_factor = (state_dict['cognitive_load'] - 70) / 30.0
        state_dict['mental_clarity'] = clamp(state_dict['mental_clarity'] - 1.0 * cognitive_factor, 0, 100)
        state_dict['decision_making'] = clamp(state_dict['decision_making'] - 0.8 * cognitive_factor, 0, 100)
        state_dict['memory_function'] = clamp(state_dict['memory_function'] - 0.7 * cognitive_factor, 0, 100)
        if state_dict['cognitive_load'] > 85:
            logs.append("🤯 High cognitive load is affecting your mental functions.")

    # Loneliness and social interaction effects
    if state_dict['loneliness'] > 50:
        loneliness_factor = (state_dict['loneliness'] - 50) / 50.0
        state_dict['emotional_stability'] = clamp(state_dict['emotional_stability'] - 0.6 * loneliness_factor, 0, 100)
        state_dict['contentment'] = clamp(state_dict['contentment'] - 0.8 * loneliness_factor, 0, 100)
        state_dict['social_anxiety'] = clamp(state_dict['social_anxiety'] + 0.4 * loneliness_factor, 0, 100)
        if state_dict['loneliness'] > 75:
            logs.append("😔 Feelings of loneliness are affecting your emotional well-being.")

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
    messages = []

    # === 1. IMPACT DES STATS DE BASE ===
    if game_time:
        work_impact, message = update_work_stats(player, game_time)
        performance_modifier += work_impact
        if message:
            messages.append(message)

    # === 2. IMPACT DES CAPACITÉS MENTALES ===
    # Concentration et clarté mentale
    cognitive_performance = (
        (player.concentration * 0.4) +
        (player.mental_clarity * 0.3) +
        (player.decision_making * 0.3)
    ) / 100.0
    performance_modifier += (cognitive_performance - 0.5) * 3  # -1.5 à +1.5

    if player.cognitive_load > 80:
        performance_modifier -= 1.0
        messages.append("🤯 La surcharge cognitive affecte votre performance")

    # === 3. IMPACT DES ÉTATS PHYSIQUES ===
    # Santé et Énergie
    physical_state = (
        (player.health * 0.4) +
        (player.energy * 0.4) +
        (player.stamina * 0.2)
    ) / 100.0
    performance_modifier += (physical_state - 0.5) * 2  # -1.0 à +1.0

    # Fatigue et Confort
    if player.fatigue > 70:
        fatigue_impact = ((player.fatigue - 70) / 30) * 2
        performance_modifier -= fatigue_impact
        if player.fatigue > 85:
            messages.append("😫 La fatigue nuit sérieusement à votre travail")

    # === 4. IMPACT DES ÉTATS ÉMOTIONNELS ===
    # Stress et Stabilité Émotionnelle
    emotional_impact = (
        (100 - player.stress) * 0.4 +
        (player.emotional_stability * 0.3) +
        (player.emotional_resilience * 0.3)
    ) / 100.0
    performance_modifier += (emotional_impact - 0.5) * 2  # -1.0 à +1.0

    if player.stress > 80:
        messages.append("😰 Le stress intense diminue votre efficacité")

    # === 5. IMPACT SOCIAL ET ENVIRONNEMENTAL ===
    # Anxiété sociale et environnement
    if player.social_anxiety > 60:
        social_penalty = ((player.social_anxiety - 60) / 40) * 1.5
        performance_modifier -= social_penalty
        if player.social_anxiety > 80:
            messages.append("😨 L'anxiété sociale impacte vos interactions professionnelles")

    # Impact environnemental
    if player.environmental_stress > 70:
        env_penalty = ((player.environmental_stress - 70) / 30)
        performance_modifier -= env_penalty

    # === 6. IMPACT DES ADDICTIONS ===
    # Sevrage et Envies
    withdrawal_impact = 0
    if player.withdrawal_severity > 40:
        withdrawal_impact = ((player.withdrawal_severity - 40) / 60) * 2
        performance_modifier -= withdrawal_impact
        messages.append("🚬 Les symptômes de sevrage affectent votre concentration")

    # === 7. ADAPTATIONS ET RÉSILIENCE ===
    # Bonus de résilience si le joueur maintient une bonne performance malgré les difficultés
    if player.job_performance > 70 and (player.stress > 60 or player.fatigue > 60):
        player.emotional_resilience = clamp(player.emotional_resilience + 0.2, 0, 100)
        messages.append("💪 Votre résilience s'améliore face aux défis")

    # === 8. APPRENTISSAGE ET PROGRESSION ===
    # Amélioration des compétences avec l'expérience
    if player.job_performance > 80:
        player.decision_making = clamp(player.decision_making + 0.1, 0, 100)
        player.emotional_stability = clamp(player.emotional_stability + 0.1, 0, 100)

    # === 9. APPLICATION DES MODIFICATIONS ===
    # Système de momentum pour des changements graduels
    current_perf = player.job_performance
    target_perf = clamp(50 + performance_modifier * 10, 0, 100)  # Échelle plus nuancée
    
    # Changement progressif avec inertie
    max_change = 5 * (1 + (player.emotional_stability / 200))  # La stabilité permet des adaptations plus rapides
    actual_change = clamp(target_perf - current_perf, -max_change, max_change)
    
    # Application finale avec feedback
    new_performance = clamp(current_perf + actual_change, 0, 100)
    if abs(new_performance - current_perf) > 10:
        if new_performance > current_perf:
            messages.append("📈 Votre performance s'améliore significativement")
        else:
            messages.append("📉 Votre performance se dégrade notablement")
    
    player.job_performance = new_performance
    return messages  # Retourne les messages pour le feedback