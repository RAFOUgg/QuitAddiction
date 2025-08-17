import datetime
import pytz
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from db.models import ServerState

# Centralized timezone for the entire application (UTC+2)
TARGET_TIMEZONE = pytz.timezone('Europe/Paris')

def get_utc_now() -> datetime.datetime:
    """Returns the current timezone-aware UTC datetime."""
    return datetime.datetime.now(datetime.timezone.utc)

def to_localized(dt: datetime.datetime) -> datetime.datetime:
    """Converts a naive UTC datetime or an aware UTC datetime to the target timezone."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    return dt.astimezone(TARGET_TIMEZONE)

def prepare_for_db(dt: datetime.datetime) -> datetime.datetime:
    """
    Prepares a datetime for storage in the database by converting to UTC and removing timezone info.
    SQLAlchemy stores datetimes as naive UTC by convention.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    return dt.astimezone(pytz.UTC).replace(tzinfo=None)

def get_current_game_time(state: 'ServerState') -> datetime.datetime:
    """
    Calculates the current in-game time based on the game mode.
    Returns a timezone-aware datetime object in the TARGET_TIMEZONE.
    
    Test Mode: 84 minutes real time = 7 days game time (1 minute real = 2 hours game)
    Real Time: Game time = Real time
    """
    now_utc = get_utc_now()

    # Vérifier si le jeu a démarré
    if not state.game_start_time:
        return now_utc.astimezone(TARGET_TIMEZONE)

    # Pour le mode temps réel
    if state.duration_key == 'real_time' or not state.game_minutes_per_day:
        # Calculer le temps écoulé depuis le début du jeu
        game_start = state.game_start_time
        if game_start.tzinfo is None:
            game_start = pytz.utc.localize(game_start)
        
        # Si on est en temps réel, on garde le même temps que la réalité
        # mais on commence à l'heure de début configurée
        start_hour = state.game_day_start_hour or 9
        base_time = game_start.astimezone(TARGET_TIMEZONE).replace(
            hour=start_hour, minute=0, second=0, microsecond=0
        )
        elapsed = now_utc - game_start
        return (base_time + elapsed).astimezone(TARGET_TIMEZONE)

    # Assurer que game_start_time a un timezone
    game_start_time = state.game_start_time
    if game_start_time.tzinfo is None:
        game_start_time = pytz.utc.localize(game_start_time)

    # En mode test :
    # - 84 minutes réelles = 1 semaine de jeu (7 jours)
    # - 1 minute réelle = 2 heures de jeu (120 minutes)
    elapsed_real_seconds = (now_utc - game_start_time).total_seconds()
    
    if state.duration_key == 'test':
        # 84 minutes réelles = 7 jours = 168 heures
        # Donc 1 minute réelle = 2 heures = 120 minutes de jeu
        game_minutes_elapsed = elapsed_real_seconds / 60 * 120
    else:
        real_seconds_per_game_day = state.game_minutes_per_day * 60
        game_minutes_elapsed = (elapsed_real_seconds / real_seconds_per_game_day) * (24 * 60)

    start_hour = state.game_day_start_hour or 9 # Default to 9 AM
    game_time_at_start_utc = state.game_start_time.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    current_game_time_utc = game_time_at_start_utc + datetime.timedelta(minutes=game_minutes_elapsed)
    
    return to_localized(current_game_time_utc)

# --- Time-based condition checks ---

def is_work_time(game_time: datetime.datetime) -> bool:
    """Checks if the given game_time is within working hours (9:00-11:30, 13:00-17:30)."""
    # Assurons-nous que le datetime est conscient du fuseau horaire
    if game_time.tzinfo is None:
        game_time = TARGET_TIMEZONE.localize(game_time)
    
    # Vérifions aussi que ce n'est pas le weekend
    if game_time.weekday() in [0, 6]:  # 0 = Lundi, 6 = Dimanche
        return False
        
    t = game_time.time()
    return (datetime.time(9, 0) <= t < datetime.time(11, 30)) or \
           (datetime.time(13, 0) <= t <= datetime.time(17, 30))  # Changé < à <= pour inclure 17:30

def is_lunch_break(game_time: datetime.datetime) -> bool:
    """Checks if the given game_time is during lunch break (11:30-13:00)."""
    return datetime.time(11, 30) <= game_time.time() < datetime.time(13, 0)

def is_night(game_time: datetime.datetime) -> bool:
    """Checks if the given game_time is at night (22:00-6:00)."""
    t = game_time.time()
    return t >= datetime.time(22, 0) or t < datetime.time(6, 0)
