# --- utils/calculations.py ---
import math

# Fonction d'aide pour clamp (limiter) une valeur entre min_val et max_val
def clamp(value, min_val, max_val):
    return max(min_val, min(max_val, value))

def chain_reactions(state_dict):
    """
    Applique les réactions en chaîne sur un dictionnaire d'état du joueur.
    MODIFIE le dictionnaire d'état directement.
    """
    # DÉCLARATIONS INITIALES DES VALEURS SI ELLES SONT ABSENTES (sécurité)
    # Ces valeurs sont prises depuis le state_dict, mais on s'assure qu'elles existent.
    # Les valeurs par défaut viennent de PlayerProfile.
    state_dict.setdefault("HEALTH", 100.0)
    state_dict.setdefault("PAIN", 0.0)
    state_dict["PAIN"] = clamp(state_dict["PAIN"], 0.0, 100.0)
    
    state_dict.setdefault("STRESS", 0.0)
    state_dict["STRESS"] = clamp(state_dict["STRESS"], 0.0, 100.0)
    
    state_dict.setdefault("MENT", 100.0) # Sanity
    state_dict["MENT"] = clamp(state_dict["MENT"], 0.0, 100.0)
    
    state_dict.setdefault("HUNGER", 0.0) # 0 = plein, 100 = faim
    state_dict["HUNGER"] = clamp(state_dict["HUNGER"], 0.0, 100.0)
    
    state_dict.setdefault("THIRST", 0.0) # 0 = plein, 100 = soif
    state_dict["THIRST"] = clamp(state_dict["THIRST"], 0.0, 100.0)
    
    state_dict.setdefault("BLADDER", 0.0) # 0 = vide, 100 = urgent
    state_dict["BLADDER"] = clamp(state_dict["BLADDER"], 0.0, 100.0)
    
    state_dict.setdefault("ENERGY", 100.0)
    state_dict["ENERGY"] = clamp(state_dict["ENERGY"], 0.0, 100.0)
    
    state_dict.setdefault("HAPPY", 0.0) # Bonheur, peut aller sous zéro
    state_dict.setdefault("BORDEOM", 0.0) # 0 = Stimulé, 100 = Ennuyé
    state_dict["BORDEOM"] = clamp(state_dict["BORDEOM"], 0.0, 100.0)
    
    state_dict.setdefault("TOX", 0.0) # Toxines
    state_dict["TOX"] = clamp(state_dict["TOX"], 0.0, 100.0)
    
    state_dict.setdefault("ADDICTION", 0.0) # Addiction
    state_dict["ADDICTION"] = clamp(state_dict["ADDICTION"], 0.0, 100.0)
    
    state_dict.setdefault("WITHDRAWAL_SEVERITY", 0.0) # Gravité du sevrage
    
    state_dict.setdefault("TRIP", 0.0) # État psychédélique

    # --- Logique des Réactions en Chaîne ---

    # Effets du TOX : douleur et stress
    if state_dict.get("TOX", 0) > 50:
        state_dict["PAIN"] = clamp(state_dict.get("PAIN", 0) + 2.0, 0.0, 100.0)
    if state_dict.get("PAIN", 0) > 30:
        state_dict["STRESS"] = clamp(state_dict.get("STRESS", 0) + 5.0, 0.0, 100.0)
        state_dict["MENT"] = clamp(state_dict.get("MENT", 0) - 2.0, 0.0, 100.0) # Santé mentale affectée

    # Effets de la Faim / Soif et Vessie
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

    # Effets de l'Addiction et du Sevrage
    if state_dict.get("ADDICTION", 0) > 50: # Si l'addiction est présente
        # Diminution du temps avant la prochaine envie, augmentation du stress en cas de manque
        # Ceci est plus une "logique de déclenchement" qu'une modification directe de jauge ici,
        # mais si le sevrage est géré, il faut le représenter.
        pass # Les effets du sevrage sont gérés par le scheduler/actions, basé sur withdrawal_severity.
        # Si on voulait un effet direct :
        # if state_dict.get("WITHDRAWAL_SEVERITY", 0) > 0:
        #     state_dict["STRESS"] = clamp(state_dict.get("STRESS", 0) + state_dict["WITHDRAWAL_SEVERITY"] * 0.5, 0.0, 100.0)
        #     state_dict["MENT"] = clamp(state_dict.get("MENT", 0) - state_dict["WITHDRAWAL_SEVERITY"] * 0.2, 0.0, 100.0)
        #     state_dict["PAIN"] = clamp(state_dict.get("PAIN", 0) + state_dict["WITHDRAWAL_SEVERITY"] * 0.3, 0.0, 100.0)
        #     state_dict["ENERGY"] = clamp(state_dict.get("ENERGY", 0) - state_dict["WITHDRAWAL_SEVERITY"] * 0.4, 0.0, 100.0)
        #     state_dict["HAPPY"] = clamp(state_dict.get("HAPPY", 0) - state_dict["WITHDRAWAL_SEVERITY"] * 0.6, -100.0, 100.0)
    
    # Effets de l'Intoxication ("TRIP")
    if state_dict.get("TRIP", 0) > 50: # Si état "trip" haut
         state_dict["SANITY"] = clamp(state_dict.get("MENT", 0) - 1.5, 0.0, 100.0) # Diminue la lucidité (MENT)
         state_dict["CONCENTRATION"] = clamp(state_dict.get("CONCENTRATION", 0) - 2.0, 0.0, 100.0) # Diminue la concentration
         # D'autres effets visuels, auditifs etc. peuvent être ajoutés ici.
         state_dict["STRESS"] = clamp(state_dict.get("STRESS", 0) + 1.0, 0.0, 100.0) # Le trip peut aussi être stressant

    # Réactions aux besoins vitaux critiques (déjà géré dans le scheduler, mais peut être redéfini ici si besoin)
    # if state_dict.get("HUNGER", 0) >= 90 or state_dict.get("THIRST", 0) >= 90:
    #     state_dict["HEALTH"] = clamp(state_dict.get("HEALTH", 0) - 3.0, 0.0, 100.0)
    
# La fonction apply_delayed_effects est utile pour gérer les effets qui se produisent APRES un certain délai.
# Elle n'est pas directement appelée par chain_reactions mais serait appelée par le scheduler
# ou par les callbacks des actions qui calculent ces effets différés.
# def apply_delayed_effects(state, pending_effects, current_hour): ...