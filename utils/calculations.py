# --- utils/calculations.py (REFACTORED WITH NEW STATS) ---

from .helpers import clamp

def chain_reactions(state_dict, time_since_last_smoke):
    """
    Applique les réactions en chaîne sur un dictionnaire d'état du joueur.
    C'est le cœur de la simulation de l'état de santé et mental.
    """
    logs = []

    if state_dict['health'] < 30:
        logs.append("❤️ Santé très faible !")
    if state_dict['hunger'] > 85:
        logs.append("🍔 Faim dévorante !")
    if state_dict['thirst'] > 85:
        logs.append("💧 Soif extrême !")
    if state_dict['stress'] > 75:
        logs.append("😨 Stress intense.")
    if state_dict['withdrawal_severity'] > 60:
        logs.append("🚬 En état de manque sévère.")
    if state_dict['fatigue'] > 90:
        logs.append("🥱 Au bord de l'épuisement.")
    if state_dict['bladder'] > 95:
        logs.append("🚽 Envie très urgente !")

    if not logs:
        logs.append("Tout semble calme...")


    # S'assurer que toutes les clés existent pour éviter les KeyErrors
    all_keys = [
        'health', 'energy', 'pain', 'tox', 'hunger', 'thirst', 'bladder', 'fatigue', 
        'sanity', 'stress', 'happiness', 'boredom', 'nausea', 'dizziness', 'headache',
        'dry_mouth', 'sore_throat', 'substance_addiction_level', 'withdrawal_severity',
        'intoxication_level', 'willpower', 'hygiene', 'immune_system', 'guilt', 'is_sick',
        'craving_nicotine', 'craving_alcohol', 'sex_drive', 'job_performance', 'stomachache',
        'urge_to_pee', 'craving'
    ]
    for key in all_keys:
        state_dict.setdefault(key, 0.0)

    # --- 1. EFFETS DE L'ÉTAT DE SANTÉ ACTUEL ---
    if state_dict['is_sick']:
        state_dict['energy'] = clamp(state_dict['energy'] - 0.5, 0, 100)
        state_dict['fatigue'] = clamp(state_dict['fatigue'] + 0.5, 0, 100)
        state_dict['pain'] = clamp(state_dict['pain'] + 0.2, 0, 100)
        state_dict['happiness'] = clamp(state_dict['happiness'] - 0.3, 0, 100)
        state_dict['headache'] = clamp(state_dict['headache'] + 0.3, 0, 100)
    
    if state_dict['tox'] > 40:
        state_dict['nausea'] = clamp(state_dict['nausea'] + state_dict['tox'] * 0.08, 0, 100)
        state_dict['immune_system'] = clamp(state_dict['immune_system'] - 0.1, 0, 100)

    if state_dict['thirst'] > 60:
        state_dict['headache'] = clamp(state_dict['headache'] + 0.1, 0, 100)
    if state_dict['hunger'] > 70:
        state_dict['stress'] = clamp(state_dict['stress'] + 0.1, 0, 100)
        state_dict['energy'] = clamp(state_dict['energy'] - 0.2, 0, 100)
    if state_dict['bladder'] > 80:
        state_dict['pain'] = clamp(state_dict['pain'] + 0.2, 0, 100)
        state_dict['stress'] = clamp(state_dict['stress'] + 0.3, 0, 100)
    if state_dict['fatigue'] > 75:
        state_dict['energy'] = clamp(state_dict['energy'] - 0.4, 0, 100)
        state_dict['willpower'] = clamp(state_dict['willpower'] - 0.3, 0, 100)

    # --- 2. EFFETS DE L'ÉTAT MENTAL ---
    if state_dict['stress'] > 50:
        state_dict['immune_system'] = clamp(state_dict['immune_system'] - 0.2, 0, 100)
        state_dict['happiness'] = clamp(state_dict['happiness'] - 0.1, 0, 100)
        state_dict['willpower'] = clamp(state_dict['willpower'] - 0.2, 0, 100)
        state_dict['headache'] = clamp(state_dict['headache'] + 0.1, 0, 100)

    if state_dict['withdrawal_severity'] > 10:
        severity = state_dict['withdrawal_severity']
        state_dict['stress'] = clamp(state_dict['stress'] + severity * 0.03, 0, 100)
        state_dict['happiness'] = clamp(state_dict['happiness'] - severity * 0.04, 0, 100)
        state_dict['willpower'] = clamp(state_dict['willpower'] - severity * 0.05, 0, 100)

    # L'envie de nicotine est maintenant directement liée au manque et au temps
    nicotine_craving = state_dict['withdrawal_severity'] + (time_since_last_smoke.total_seconds() / 360)
    state_dict['craving_nicotine'] = clamp(nicotine_craving, 0, 100)

    # NOUVEAU: Logique pour les autres envies
    # Envie d'alcool quand on est stressé ou malheureux
    if state_dict['stress'] > 50 or state_dict['happiness'] < 40:
        craving_bonus = (state_dict['stress'] - 50) * 0.05 + (40 - state_dict['happiness']) * 0.05
        state_dict['craving_alcohol'] = clamp(state_dict['craving_alcohol'] + craving_bonus, 0, 100)
    else: # L'envie baisse lentement
        state_dict['craving_alcohol'] = clamp(state_dict['craving_alcohol'] - 0.5, 0, 100)

    # NOUVEAU: Libido / Envie de sexe
    # Augmente avec l'ennui, le bonheur et le temps, diminue avec la grosse fatigue, la douleur ou le stress
    if state_dict['boredom'] > 50 and state_dict['happiness'] > 40:
        state_dict['sex_drive'] = clamp(state_dict['sex_drive'] + 0.2, 0, 100)
    if state_dict['fatigue'] > 80 or state_dict['pain'] > 70 or state_dict['stress'] > 60:
        state_dict['sex_drive'] = clamp(state_dict['sex_drive'] - 1.0, 0, 100)

    # Effets de la CULPABILITÉ (Guilt)
    if state_dict['guilt'] > 0:
        state_dict['stress'] = clamp(state_dict['stress'] + state_dict['guilt'] * 0.01, 0, 100)
        state_dict['guilt'] = clamp(state_dict['guilt'] - 0.1, 0, 100) # La culpabilité s'estompe lentement

    # --- 3. EFFETS DES STATS DE VIE ---

    # Effets de l'HYGIÈNE
    if state_dict['hygiene'] < 40:
        state_dict['stress'] = clamp(state_dict['stress'] + 0.1, 0, 100)
        state_dict['happiness'] = clamp(state_dict['happiness'] - 0.05, 0, 100)
        state_dict['immune_system'] = clamp(state_dict['immune_system'] - 0.05, 0, 100) # Mauvaise hygiène -> plus de risques
        
    # Régénération de la SANTÉ et de la VOLONTÉ (si les conditions sont bonnes)
    is_healthy = state_dict['stress'] < 30 and state_dict['hunger'] < 50 and state_dict['thirst'] < 50
    if is_healthy:
        state_dict['immune_system'] = clamp(state_dict['immune_system'] + 0.1, 0, 100)
        state_dict['health'] = clamp(state_dict['health'] + 0.05, 0, 100)
        state_dict['willpower'] = clamp(state_dict['willpower'] + 0.2, 0, 100) # Le calme et le repos restaurent la volonté

    # La PERFORMANCE AU TRAVAIL est une conséquence de l'état général
    # Note : Le calcul du gain se fera dans le scheduler, ici on met juste à jour la stat pour l'affichage
    perf = 100
    perf -= state_dict['fatigue'] * 0.4
    perf -= state_dict['stress'] * 0.3
    perf -= state_dict['pain'] * 0.2
    perf -= state_dict['withdrawal_severity'] * 0.5
    if state_dict['is_sick']: perf -= 40
    state_dict['job_performance'] = clamp(perf, 0, 100)

    # --- NEW: Visual states calculation ---
    state_dict['stomachache'] = clamp((state_dict['hunger'] + state_dict['nausea']) / 2, 0, 100)
    state_dict['urge_to_pee'] = clamp(state_dict['bladder'], 0, 100)
    state_dict['craving'] = clamp((state_dict['withdrawal_severity'] + state_dict['substance_addiction_level']) / 2, 0, 100)
    state_dict['headache'] = clamp(state_dict['headache'] + (state_dict['thirst'] > 60) * 5 + (state_dict['stress'] > 70) * 5, 0, 100)

    
    return state_dict, logs