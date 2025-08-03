# --- utils/calculations.py ---
# Contient la logique des effets différés et des interactions entre variables

def apply_action_effects(state, action_type):
    """Applique les effets immédiats d'une action sur l'état du cuisinier."""
    effects = {
        "manger": {"FOOD": +50, "HAPPY": +10, "STRESS": -5},
        "boire": {"WATER": +50, "PHYS": +5, "BLADDER": +20},
        "fumer_leger": {"HAPPY": +20, "STRESS": -10, "PHYS_d": -2, "MENT_d": -1, "TOX": +1, "ADDICTION": +0.05},
        "fumer_lourd": {"HAPPY": +25, "STRESS": -15, "PHYS_d": -5, "MENT_d": -3, "TOX": +5, "ADDICTION": +0.08},
        "dab": {"HAPPY": +30, "STRESS": -20, "PHYS_d": -10, "MENT_d": -5, "TOX": +10, "TRIP": +40, "ADDICTION": +0.1}
    }
    return effects.get(action_type, {})

def apply_delayed_effects(state, pending_effects, current_hour):
    """Déclenche les effets différés à l'heure donnée."""
    for eff in pending_effects[:]:
        if eff[0] == current_hour:
            var, val = eff[1], eff[2]
            state[var] = max(0, state.get(var, 0)+val)
            pending_effects.remove(eff)


def chain_reactions(state):
    """Gestion des réactions en chaîne (ex: TOX ↑ -> PAIN ↑ -> STRESS ↑)."""
    if state["TOX"] > 50:
        state["PAIN"] += 2
    if state["PAIN"] > 30:
        state["STRESS"] += 5
        state["MENT"] -= 2
    if state["BLADDER"] > 70:
        state["STRESS"] += 2
    if state["FOOD"] <= 0 or state["WATER"] <= 0:
        state["PHYS"] -= 2