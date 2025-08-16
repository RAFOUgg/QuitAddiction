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

def get_current_game_time(state: 'ServerState') -> datetime.datetime:
    """
    Calculates the current in-game time based on the game mode.
    Returns a timezone-aware datetime object in the TARGET_TIMEZONE.
    """
    now_utc = get_utc_now()

    # For real-time games, game time IS the real-world time.
    if state.duration_key == 'real_time' or not state.game_minutes_per_day:
        return now_utc.astimezone(TARGET_TIMEZONE)

    # For accelerated time modes (e.g., 'test')
    if not state.game_start_time:
        return now_utc.astimezone(TARGET_TIMEZONE) # Fallback

    elapsed_real_seconds = (now_utc - state.game_start_time).total_seconds()
    real_seconds_per_game_day = state.game_minutes_per_day * 60
    game_seconds_elapsed = (elapsed_real_seconds / real_seconds_per_game_day) * (24 * 3600)

    start_hour = state.game_day_start_hour or 9 # Default to 9 AM
    game_time_at_start_utc = state.game_start_time.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    current_game_time_utc = game_time_at_start_utc + datetime.timedelta(seconds=game_seconds_elapsed)
    
    return to_localized(current_game_time_utc)

# --- Time-based condition checks ---

def is_work_time(game_time: datetime.datetime) -> bool:
    """Checks if the given game_time is within working hours (9:00-11:30, 13:00-17:30)."""
    t = game_time.time()
    return (datetime.time(9, 0) <= t < datetime.time(11, 30)) or \
           (datetime.time(13, 0) <= t < datetime.time(17, 30))

def is_lunch_break(game_time: datetime.datetime) -> bool:
    """Checks if the given game_time is during lunch break (11:30-13:00)."""
    return datetime.time(11, 30) <= game_time.time() < datetime.time(13, 0)

def is_night(game_time: datetime.datetime) -> bool:
    """Checks if the given game_time is at night (22:00-6:00)."""
    t = game_time.time()
    return t >= datetime.time(22, 0) or t < datetime.time(6, 0)
