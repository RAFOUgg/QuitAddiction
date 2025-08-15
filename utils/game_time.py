# utils/game_time.py
import datetime
from db.models import ServerState

def get_current_game_time(server_state: ServerState) -> datetime.time:
    """
    Calcule l'heure actuelle dans le jeu.
    En mode temps réel (real_time), renvoie l'heure réelle actuelle.
    """
    if server_state.duration_key == 'real_time':
        # En mode temps réel, on utilise l'heure actuelle directement
        return datetime.datetime.utcnow().time()
    
    if not server_state.game_start_time:
        # Retourne une heure par défaut si le jeu n'a pas encore commencé
        return datetime.time(hour=server_state.game_day_start_hour)

    # Temps réel écoulé en minutes
    real_minutes_elapsed = (datetime.datetime.utcnow() - server_state.game_start_time).total_seconds() / 60

    # Nombre total de minutes dans une journée de jeu
    game_minutes_in_day = 24 * 60

    # Calcule le nombre total de minutes de jeu écoulées
    # Le ratio est (temps réel écoulé / durée d'un jour de jeu en temps réel)
    game_minutes_elapsed = (real_minutes_elapsed / server_state.game_minutes_per_day) * game_minutes_in_day

    # Calcule l'heure de départ en minutes
    start_hour_in_minutes = server_state.game_day_start_hour * 60

    # Heure actuelle totale en minutes dans le jeu (avec modulo pour rester dans une journée)
    current_total_minutes = (start_hour_in_minutes + game_minutes_elapsed) % game_minutes_in_day

    # Conversion en heures et minutes
    current_hour = int(current_total_minutes // 60)
    current_minute = int(current_total_minutes % 60)

    return datetime.time(hour=current_hour, minute=current_minute)

def is_night(server_state: ServerState, night_start: int = 22, day_start: int = 6) -> bool:
    """
    Vérifie s'il fait nuit dans le jeu.
    La nuit est définie comme la période entre night_start et day_start.
    """
    current_time = get_current_game_time(server_state)
    
    # Cas simple : si la période de nuit ne traverse pas minuit (ex: 22h à 6h)
    if night_start > day_start:
        return current_time.hour >= night_start or current_time.hour < day_start
    # Cas où la période de nuit traverse minuit (ex: 1h à 6h, peu probable mais géré)
    else:
        return day_start > current_time.hour >= night_start

def is_work_time(server_state: ServerState) -> bool:
    """
    Vérifie si c'est l'heure de travailler dans le jeu.
    (9:00 - 11:30 et 13:00 - 17:30)
    Fermeture le dimanche et le lundi.
    """
    # Vérifier d'abord le jour de la semaine
    if not server_state.game_start_time:
        return False
    
    current_weekday = server_state.game_start_time.weekday()
    if current_weekday in [0, 6]:  # 0 = Lundi, 6 = Dimanche
        return False
        
    current_time = get_current_game_time(server_state)
    morning_start = datetime.time(hour=9, minute=0)
    morning_end = datetime.time(hour=11, minute=30)
    afternoon_start = datetime.time(hour=13, minute=0)
    afternoon_end = datetime.time(hour=17, minute=30)

    is_morning_work = morning_start <= current_time < morning_end
    is_afternoon_work = afternoon_start <= current_time < afternoon_end

    return is_morning_work or is_afternoon_work

def is_lunch_break(server_state: ServerState) -> bool:
    """
    Vérifie si c'est l'heure de la pause déjeuner.
    (11:30 - 13:00)
    """
    current_time = get_current_game_time(server_state)
    lunch_start = datetime.time(hour=11, minute=30)
    lunch_end = datetime.time(hour=13, minute=0)

    return lunch_start <= current_time < lunch_end