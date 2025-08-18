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
    
    Modes:
    - real_time: Game time matches real time
    - fast: 1 real minute = 24 game minutes (1 real hour = 1 game day)
    - medium: 1 real minute = 12 game minutes (2 real hours = 1 game day)
    - slow: 1 real minute = 6 game minutes (4 real hours = 1 game day)
    """
    now_utc = get_utc_now()

    # If no state is provided, return current time
    if not state:
        return to_localized(now_utc)

    # Always use real time if:
    # 1. real_time mode is set
    # 2. game hasn't started
    # 3. no duration_key is set
    if (getattr(state, 'duration_key', 'real_time') == 'real_time' or 
        not getattr(state, 'game_start_time', None) or 
        not getattr(state, 'duration_key', None)):
        
        # Pour le mode temps réel
        game_start = getattr(state, 'game_start_time', None)
        if game_start:
            if game_start.tzinfo is None:
                game_start = pytz.utc.localize(game_start)
            
            # On commence à l'heure de début configurée
            start_hour = getattr(state, 'game_day_start_hour', 9)
            base_time = game_start.astimezone(TARGET_TIMEZONE).replace(
                hour=start_hour, minute=0, second=0, microsecond=0
            )
            elapsed = now_utc - game_start
            return (base_time + elapsed).astimezone(TARGET_TIMEZONE)
        
    return to_localized(now_utc)
    
    # Calculate time multiplier based on mode
    time_multipliers = {
        'fast': 24,    # 1 real minute = 24 game minutes
        'medium': 12,  # 1 real minute = 12 game minutes
        'slow': 6      # 1 real minute = 6 game minutes
    }
    
    duration_key = getattr(state, 'duration_key', 'medium')
    multiplier = time_multipliers.get(duration_key, 12)  # Default to medium
    
    # Calculate elapsed real minutes since game start
    game_start_time = getattr(state, 'game_start_time', None)
    if not game_start_time:
        return to_localized(now_utc)
    
    if game_start_time.tzinfo is None:
        game_start_time = pytz.utc.localize(game_start_time)
    
    elapsed_minutes = (now_utc - game_start_time).total_seconds() / 60
    
    # Calculate game minutes
    game_minutes = elapsed_minutes * multiplier
    
    # Calculate the game time
    game_time = game_start_time + datetime.timedelta(minutes=game_minutes)
    
    return to_localized(game_time)
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
