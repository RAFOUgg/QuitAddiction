# --- utils/calculations.py (REFACTORED WITH NEW STATS) ---

from .helpers import clamp

def chain_reactions(state_dict: dict, time_since_last_smoke) -> (dict, list):
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