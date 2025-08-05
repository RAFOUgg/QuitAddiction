# --- utils/calculations.py ---

import math
import datetime

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
    """
    Applique les réactions en chaîne sur un dictionnaire d'état du joueur.
    MODIFIE LE DICTIONNAIRE D'ÉTAT PASSÉ EN ARGUMENT DIRECTEMENT.
    Les clés du dictionnaire DOIVENT correspondre aux noms utilisés ici.
    """
    # --- Assurer que toutes les clés nécessaires existent dans le dictionnaire ---
    # Utilise setdefault pour définir une valeur par défaut si la clé n'existe pas.
    # Ces valeurs par défaut devraient idéalement correspondre aux valeurs par défaut des champs PlayerProfile.

    # Jauges vitales (0-100)
    state_dict.setdefault("HEALTH", 100.0)
    state_dict["HEALTH"] = clamp(state_dict.get("HEALTH", 100.0), 0.0, 100.0)

    state_dict.setdefault("ENERGY", 100.0)
    state_dict["ENERGY"] = clamp(state_dict["ENERGY"], 0.0, 100.0)

    state_dict.setdefault("HUNGER", 0.0) # 0 = Plein, 100 = Faim
    state_dict["HUNGER"] = clamp(state_dict["HUNGER"], 0.0, 100.0)
    
    state_dict.setdefault("THIRST", 0.0) # 0 = Plein, 100 = Soif
    state_dict["THIRST"] = clamp(state_dict["THIRST"], 0.0, 100.0)
    
    state_dict.setdefault("BLADDER", 0.0) # 0 = Vide, 100 = Urgent
    state_dict["BLADDER"] = clamp(state_dict["BLADDER"], 0.0, 100.0)
    
    # Jauges mentales / Émotionnelles
    state_dict.setdefault("MENT", 100.0) # Représente la Sanity
    state_dict["MENT"] = clamp(state_dict["MENT"], 0.0, 100.0)
    
    state_dict.setdefault("STRESS", 0.0) # 0 = Calme, 100 = Panique
    state_dict["STRESS"] = clamp(state_dict["STRESS"], 0.0, 100.0)
    
    state_dict.setdefault("HAPPY", 0.0) # Bonheur
    state_dict["HAPPY"] = clamp(state_dict["HAPPY"], -100.0, 100.0) # Permet des valeurs négatives
    
    state_dict.setdefault("IRRITABILITY", 0.0)
    state_dict["IRRITABILITY"] = clamp(state_dict["IRRITABILITY"], 0.0, 100.0)
    
    state_dict.setdefault("FEAR", 0.0) # Peur
    state_dict["FEAR"] = clamp(state_dict["FEAR"], 0.0, 100.0)
    
    state_dict.setdefault("LONELINESS", 0.0) # Solitude
    state_dict["LONELINESS"] = clamp(state_dict["LONELINESS"], 0.0, 100.0)
    
    state_dict.setdefault("BORDEOM", 0.0) # Ennui
    state_dict["BORDEOM"] = clamp(state_dict["BORDEOM"], 0.0, 100.0)
    
    state_dict.setdefault("CONCENTRATION", 100.0)
    state_dict["CONCENTRATION"] = clamp(state_dict["CONCENTRATION"], 0.0, 100.0)

    # Addiction et Consommation
    state_dict.setdefault("ADDICTION", 0.0) # Niveau d'addiction
    state_dict["ADDICTION"] = clamp(state_dict["ADDICTION"], 0.0, 100.0)
    
    state_dict.setdefault("WITHDRAWAL_SEVERITY", 0.0) # Gravité du sevrage
    
    state_dict.setdefault("INTOXICATION_LEVEL", 0.0) # Niveau d'intoxication / TRIP
    state_dict["INTOXICATION_LEVEL"] = clamp(state_dict["INTOXICATION_LEVEL"], 0.0, 100.0)
    
    state_dict.setdefault("TOX", 0.0) # Toxines
    state_dict["TOX"] = clamp(state_dict["TOX"], 0.0, 100.0)
    
    state_dict.setdefault("PAIN", 0.0) # Douleur
    state_dict["PAIN"] = clamp(state_dict["PAIN"], 0.0, 100.0)

    # --- Logique des Réactions en Chaîne ---
    # Les conditions sont basées sur les valeurs ACTUELLES des jauges dans state_dict

    # Effets du TOX : douleur et stress
    if state_dict.get("TOX", 0) > 50:
        state_dict["PAIN"] = clamp(state_dict.get("PAIN", 0) + 2.0, 0.0, 100.0)
    if state_dict.get("PAIN", 0) > 30:
        state_dict["STRESS"] = clamp(state_dict.get("STRESS", 0) + 5.0, 0.0, 100.0)
        state_dict["MENT"] = clamp(state_dict.get("MENT", 0) - 2.0, 0.0, 100.0) # Santé mentale affectée

    # Effets de la Faim / Soif / Vessie critiques
    if state_dict.get("HUNGER", 0) >= 90 or state_dict.get("THIRST", 0) >= 90:
        state_dict["HEALTH"] = clamp(state_dict.get("HEALTH", 0) - 3.0, 0.0, 100.0) # Gravement affaibli
        state_dict["STRESS"] = clamp(state_dict.get("STRESS", 0) + 3.0, 0.0, 100.0) # Stress augmente

    if state_dict.get("BLADDER", 0) > 70:
        state_dict["STRESS"] = clamp(state_dict.get("STRESS", 0) + 2.0, 0.0, 100.0) # Stress pour besoin pressant

    # Effets du STRESS et de l'IRRITABILITÉ
    if state_dict.get("STRESS", 0) > 60:
        state_dict["IRRITABILITY"] = clamp(state_dict.get("IRRITABILITY", 0) + 3.0, 0.0, 100.0) # Augmente l'irritabilité
        state_dict["MENT"] = clamp(state_dict.get("MENT", 0) - 1.0, 0.0, 100.0) # Santé mentale baisse
    if state_dict.get("IRRITABILITY", 0) > 40:
        state_dict["HAPPY"] = clamp(state_dict.get("HAPPY", 0) - 2.0, -100.0, 100.0) # Bonheur baisse si très irritable

    # Effets de l'Ennui et de la Solitude
    if state_dict.get("BORDEOM", 0) > 50 and state_dict.get("LONELINESS", 0) > 30:
         state_dict["MOOD"] = clamp(state_dict.get("MOOD", 0) - 1.0, -100.0, 100.0) # Humeur dégradée

    # Effets de l'Addiction et du Sevrage (logique principale gérée par scheduler, mais ici pour les effets PERMANENTS si besoin)
    # Si l'addiction monte, elle peut augmenter le sevrage, la tolérance, etc.
    # Si le sevrage est actif (par exemple, si withdrawal_severity > 0), on peut appliquer des malus :
    if state_dict.get("ADDICTION", 0) > 20 and state_dict.get("WITHDRAWAL_SEVERITY", 0) > 0:
        # Les effets de sevrage sont souvent liés à la sévérité du sevrage
        state_dict["STRESS"] = clamp(state_dict.get("STRESS", 0) + state_dict.get("WITHDRAWAL_SEVERITY", 0) * 0.5, 0.0, 100.0)
        state_dict["MENT"] = clamp(state_dict.get("MENT", 0) - state_dict.get("WITHDRAWAL_SEVERITY", 0) * 0.2, 0.0, 100.0)
        state_dict["PAIN"] = clamp(state_dict.get("PAIN", 0) + state_dict.get("WITHDRAWAL_SEVERITY", 0) * 0.3, 0.0, 100.0)
        state_dict["ENERGY"] = clamp(state_dict.get("ENERGY", 0) - state_dict["WITHDRAWAL_SEVERITY"] * 0.4, 0.0, 100.0)
        state_dict["HAPPY"] = clamp(state_dict.get("HAPPY", 0) - state_dict.get("WITHDRAWAL_SEVERITY", 0) * 0.6, -100.0, 100.0)
    
    # Effets de l'Intoxication ("TRIP")
    if state_dict.get("TRIP", 0) > 50: # Si état "trip" haut
         state_dict["SANITY"] = clamp(state_dict.get("MENT", 0) - 1.5, 0.0, 100.0) # Diminue la lucidité (MENT)
         state_dict["CONCENTRATION"] = clamp(state_dict.get("CONCENTRATION", 0) - 2.0, 0.0, 100.0) # Diminue la concentration
         state_dict["STRESS"] = clamp(state_dict.get("STRESS", 0) + 1.0, 0.0, 100.0) # Le trip peut aussi être stressant

    # Note: Ici, nous n'avons pas encore les `degradation_rate_*` du ServerState qui sont gérés directement par le scheduler.
    # Ces rates s'ajoutent AU TEMPS PASSÉ, tandis que les réactions en chaîne sont des EFFETS DE SEUIL basés sur l'état ACTUEL.
    # Le scheduler prend les taux de ServerState pour faire les dégradations, puis chain_reactions applique les conséquences.

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