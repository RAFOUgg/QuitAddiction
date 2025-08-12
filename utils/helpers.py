# --- utils/helpers.py ---
import datetime

def clamp(value, min_val, max_val):
    """Limite une valeur à une plage spécifiée."""
    return max(min_val, min(max_val, value))

def format_time_delta(td: datetime.timedelta) -> str:
    """Formate joliment un timedelta pour l'affichage."""
    if not td: return "jamais"
    seconds = int(td.total_seconds())
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    return f"{hours}h {minutes % 60}m"