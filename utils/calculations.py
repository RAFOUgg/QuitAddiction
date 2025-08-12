# --- utils/calculations.py ---

import math
import datetime
from .helpers import clamp
# Assurez-vous que les types de données des modèles correspondent à ce que vous attendez ici
# (par exemple, certains taux sont Float, d'autres peuvent être Int).

# --- Fonctions d'aide ---

def clamp(value, min_val, max_val):
    """
    Limite une valeur à rester dans une plage spécifiée [min_val, max_val].
    Utile pour s'assurer que les jauges ne dépassent pas 100% ou ne tombent pas en dessous de 0.
    """
    return max(min_val, min(max_val, value))

# --- Fonction principale pour les réactions en chaîne ---
def chain_reactions(state_dict):
    """Applique les réactions en chaîne sur un dictionnaire d'état du joueur."""
    # S'assurer que toutes les clés existent avec setdefault pour éviter les KeyErrors
    for key in ['health', 'energy', 'pain', 'tox', 'hunger', 'thirst', 'bladder', 'fatigue', 
                'sanity', 'stress', 'happiness', 'boredom', 'nausea', 'dizziness', 
                'headache', 'dry_mouth', 'sore_throat', 'substance_addiction_level', 
                'withdrawal_severity', 'intoxication_level']:
        state_dict.setdefault(key, 0.0)

    # --- EFFETS DE L'INTOXICATION ("TRIP") ---
    if state_dict['intoxication_level'] > 30:
        state_dict['dizziness'] = clamp(state_dict['dizziness'] + state_dict['intoxication_level'] * 0.1, 0, 100)
        state_dict['sanity'] = clamp(state_dict['sanity'] - state_dict['intoxication_level'] * 0.05, 0, 100)
    
    # --- EFFETS DES TOXINES ET DE LA SANTÉ ---
    if state_dict['tox'] > 40:
        state_dict['nausea'] = clamp(state_dict['nausea'] + state_dict['tox'] * 0.08, 0, 100)
        state_dict['headache'] = clamp(state_dict['headache'] + state_dict['tox'] * 0.05, 0, 100)
        state_dict['health'] = clamp(state_dict['health'] - 1, 0, 100)

    if state_dict['health'] < 50:
        state_dict['fatigue'] = clamp(state_dict['fatigue'] + 5, 0, 100)
        state_dict['pain'] = clamp(state_dict['pain'] + 2, 0, 100)

    # --- EFFETS DES BESOINS VITAUX ---
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

    # --- EFFETS DES SYMPTÔMES SUR L'ÉTAT GÉNÉRAL ---
    if state_dict['pain'] > 30:
        state_dict['stress'] = clamp(state_dict['stress'] + state_dict['pain'] * 0.1, 0, 100)
        state_dict['happiness'] = clamp(state_dict['happiness'] - 5, 0, 100)
        
    if state_dict['nausea'] > 50:
        state_dict['hunger'] = clamp(state_dict['hunger'] - 20, 0, 100) # Coupe la faim
        state_dict['happiness'] = clamp(state_dict['happiness'] - 10, 0, 100)

    # --- EFFETS DU MANQUE (SEVRAGE) ---
    # La logique pour déclencher 'withdrawal_severity' sera dans le scheduler
    if state_dict['withdrawal_severity'] > 10:
        severity = state_dict['withdrawal_severity']
        state_dict['stress'] = clamp(state_dict['stress'] + severity * 0.3, 0, 100)
        state_dict['nausea'] = clamp(state_dict['nausea'] + severity * 0.2, 0, 100)
        state_dict['headache'] = clamp(state_dict['headache'] + severity * 0.25, 0, 100)
        state_dict['happiness'] = clamp(state_dict['happiness'] - severity * 0.4, 0, 100)

    return state_dict

# --- Fonction pour appliquer les effets immédiats des actions ---
# Cette fonction est appelée quand le joueur FAIT une action (manger, boire, fumer)
def apply_action_effects(state_dict, action_type):
    """
    Applique les effets immédiats d'une action sur l'état du joueur.
    Retourne un dictionnaire des changements à appliquer.
    """
    effects = {}
    if action_type == "manger":
        effects = {"FOOD": 50, "HAPPY": 10, "STRESS": -5}
    elif action_type == "boire":
        effects = {"WATER": 50, "PHYS": 5, "BLADDER": 20}
    elif action_type == "fumer_leger":
        effects = {"HAPPY": 20, "STRESS": -10, "ENERGY": -2, "MENT": -1, "TOX": 1, "ADDICTION": 0.05}
    elif action_type == "fumer_lourd":
        effects = {"HAPPY": 25, "STRESS": -15, "ENERGY": -5, "MENT": -3, "TOX": 5, "ADDICTION": 0.08}
    elif action_type == "dab":
        effects = {"HAPPY": 30, "STRESS": -20, "ENERGY": -10, "MENT": -5, "TOX": 10, "TRIP": 40, "ADDICTION": 0.1}
    
    # Il faudrait appliquer ces effets avec un clamping (min/max) et potentiellement des effets différés
    # Ici on retourne juste les effets immédiats pour que le code appelant les gère
    return effects

# La fonction apply_delayed_effects est utile pour gérer les effets qui se produisent APRES un certain délai.
# Elle n'est pas directement appelée par chain_reactions mais serait appelée par le scheduler
# ou par les callbacks des actions qui calculent ces effets différés.
# def apply_delayed_effects(state, pending_effects, current_hour): ...