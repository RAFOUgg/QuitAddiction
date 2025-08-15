# utils/game_time.py
import datetime
import os
from db.models import ServerState

# Allow configuring a timezone offset (hours) for display. Defaults to +2 (CEST) as requested.
TIMEZONE_OFFSET_HOURS = int(os.getenv("GAME_TIME_OFFSET_HOURS", 2))

def _apply_offset(dt: datetime.datetime) -> datetime.datetime:
    """Treat naive datetimes as UTC and apply configured offset, return naive local datetime."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # treat stored times as UTC
        dt_utc = dt
    else:
        dt_utc = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    return dt_utc + datetime.timedelta(hours=TIMEZONE_OFFSET_HOURS)
def get_current_game_time(server_state: ServerState) -> datetime.time:
    """
    Calcule l'heure actuelle dans le jeu.
    En mode temps réel (real_time), renvoie l'heure réelle actuelle.
    """
    if server_state.duration_key == 'real_time':
        if not server_state.game_start_time:
            return datetime.time(hour=server_state.game_day_start_hour)
            
        # En mode temps réel, on calcule le temps écoulé depuis le démarrage
        elapsed = datetime.datetime.utcnow() - server_state.game_start_time
        start_minutes = server_state.game_day_start_hour * 60
        total_minutes = (start_minutes + elapsed.total_seconds() / 60) % (24 * 60)
        current_hour = int(total_minutes // 60)
        current_minute = int(total_minutes % 60)
        return datetime.time(hour=current_hour, minute=current_minute)
    
    if not server_state.game_start_time:
        # Retourne une heure par défaut si le jeu n'a pas encore commencé
        return datetime.time(hour=server_state.game_day_start_hour)

    # Temps réel écoulé en minutes
    real_minutes_elapsed = (datetime.datetime.utcnow() - server_state.game_start_time).total_seconds() / 60

    # Nombre total de minutes dans une journée de jeu
    # Temps réel écoulé en minutes (tous les calculs considèrent game_start_time comme UTC)
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

def localize_datetime(dt: datetime.datetime) -> datetime.datetime | None:
    """Return a naive datetime shifted by configured timezone offset (treating input as UTC)."""
    if not dt:
        return None
    return _apply_offset(dt)

def is_night(server_state: ServerState, night_start: int = 22, day_start: int = 6) -> bool:
    """
    Vérifie s'il fait nuit dans le jeu.
    La nuit est définie comme la période entre night_start et day_start.
    """
    # Localize the calculated game time for comparisons
    current_time_utc = get_current_game_time(server_state)
    if current_time_utc is None:
        return False
    now_dt_utc = datetime.datetime.utcnow().replace(hour=current_time_utc.hour, minute=current_time_utc.minute, second=0, microsecond=0)
    now_local = _apply_offset(now_dt_utc)
    current_hour = now_local.hour

    # Cas simple : si la période de nuit ne traverse pas minuit (ex: 22h à 6h)
    if night_start > day_start:
        return current_hour >= night_start or current_hour < day_start
    # Cas où la période de nuit traverse minuit (ex: 1h à 6h, peu probable mais géré)
    else:
        return day_start > current_hour >= night_start

def is_work_time(server_state: ServerState) -> bool:
    """
    Vérifie si c'est l'heure de travailler dans le jeu.
    (9:00 - 11:30 et 13:00 - 17:30)
    Fermeture le dimanche et le lundi.
    """
    # Vérifier d'abord le jour de la semaine
    if not server_state.game_start_time:
        return False

    # Determine weekday from localized start time to reflect server's local day
    localized_start = localize_datetime(server_state.game_start_time)
    current_weekday = localized_start.weekday() if localized_start else server_state.game_start_time.weekday()
    if current_weekday in [0, 6]:  # 0 = Lundi, 6 = Dimanche
        return False
        
    # Localize the current game time for comparisons
    current_time_utc = get_current_game_time(server_state)
    if current_time_utc is None:
        return False
    now_dt_utc = datetime.datetime.utcnow().replace(hour=current_time_utc.hour, minute=current_time_utc.minute, second=0, microsecond=0)
    now_local = _apply_offset(now_dt_utc)
    current_time = now_local.time()

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
    current_time_utc = get_current_game_time(server_state)
    if current_time_utc is None:
        return False
    now_dt_utc = datetime.datetime.utcnow().replace(hour=current_time_utc.hour, minute=current_time_utc.minute, second=0, microsecond=0)
    now_local = _apply_offset(now_dt_utc)
    current_time = now_local.time()

    lunch_start = datetime.time(hour=11, minute=30)
    lunch_end = datetime.time(hour=13, minute=0)

    return lunch_start <= current_time < lunch_end