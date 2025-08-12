# --- utils/calculations.py (FINAL VERSION) ---

from .helpers import clamp

def chain_reactions(state_dict):
    """Applique les réactions en chaîne sur un dictionnaire d'état du joueur."""
    for key in ['health', 'energy', 'pain', 'tox', 'hunger', 'thirst', 'bladder', 'fatigue', 
                'sanity', 'stress', 'happiness', 'boredom', 'nausea', 'dizziness', 
                'headache', 'dry_mouth', 'sore_throat', 'substance_addiction_level', 
                'withdrawal_severity', 'intoxication_level']:
        state_dict.setdefault(key, 0.0)

    # EFFETS DE L'INTOXICATION
    if state_dict['intoxication_level'] > 30:
        state_dict['dizziness'] = clamp(state_dict['dizziness'] + state_dict['intoxication_level'] * 0.1, 0, 100)
        state_dict['sanity'] = clamp(state_dict['sanity'] - state_dict['intoxication_level'] * 0.05, 0, 100)
    
    # EFFETS DES TOXINES
    if state_dict['tox'] > 40:
        state_dict['nausea'] = clamp(state_dict['nausea'] + state_dict['tox'] * 0.08, 0, 100)
        state_dict['headache'] = clamp(state_dict['headache'] + state_dict['tox'] * 0.05, 0, 100)
        state_dict['health'] = clamp(state_dict['health'] - 1, 0, 100)

    # EFFETS DES BESOINS VITAUX
    if state_dict['thirst'] > 60:
        state_dict['dry_mouth'] = clamp(state_dict['dry_mouth'] + state_dict['thirst'] * 0.2, 0, 100)
        state_dict['headache'] = clamp(state_dict['headache'] + 3, 0, 100)
    if state_dict['hunger'] > 70:
        state_dict['stress'] = clamp(state_dict['stress'] + 4, 0, 100)
        state_dict['energy'] = clamp(state_dict['energy'] - 5, 0, 100)
    if state_dict['bladder'] > 80:
        state_dict['pain'] = clamp(state_dict['pain'] + 5, 0, 100)
        state_dict['stress'] = clamp(state_dict['stress'] + 8, 0, 100)
    if state_dict['fatigue'] > 75:
        state_dict['energy'] = clamp(state_dict['energy'] - 10, 0, 100)
        state_dict['dizziness'] = clamp(state_dict['dizziness'] + 5, 0, 100)

    # EFFETS DES SYMPTÔMES
    if state_dict['pain'] > 30:
        state_dict['stress'] = clamp(state_dict['stress'] + state_dict['pain'] * 0.1, 0, 100)
        state_dict['happiness'] = clamp(state_dict['happiness'] - 5, 0, 100)
    if state_dict['nausea'] > 50:
        state_dict['happiness'] = clamp(state_dict['happiness'] - 10, 0, 100)

    # EFFETS DU MANQUE
    if state_dict['withdrawal_severity'] > 10:
        severity = state_dict['withdrawal_severity']
        state_dict['stress'] = clamp(state_dict['stress'] + severity * 0.3, 0, 100)
        state_dict['nausea'] = clamp(state_dict['nausea'] + severity * 0.2, 0, 100)
        state_dict['headache'] = clamp(state_dict['headache'] + severity * 0.25, 0, 100)
        state_dict['happiness'] = clamp(state_dict['happiness'] - severity * 0.4, 0, 100)

    return state_dict

