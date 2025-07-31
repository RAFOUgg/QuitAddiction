# Ce fichier contiendra la logique métier pour la gestion des stats du cuisinier.
# Par exemple, les calculs de dégradation des stats, les effets des objets, etc.

from .models import Cook

def apply_stat_decay(cook: Cook):
    """
    Applique la dégradation naturelle des stats du cuisinier.
    Cette fonction sera appelée périodiquement par une tâche en arrière-plan.
    """
    # Logique de base pour l'instant
    if cook.thirst > 0:
        cook.thirst -= 1
    
    if cook.hunger > 0:
        cook.hunger -= 1

    # Plus tard, on ajoutera des logiques plus complexes:
    # if cook.sleep < 30:
    #     cook.energy -= 2
    
    return cook