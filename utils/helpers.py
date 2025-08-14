# --- utils/helpers.py ---
import datetime
import json
from db.models import PlayerProfile

def clamp(value, min_val, max_val):
    """Limite une valeur à une plage spécifiée."""
    return max(min_val, min(max_val, value))

def format_time_delta(td: datetime.timedelta) -> str:
    """Formate joliment un timedelta pour l'affichage (jours, heures, minutes)."""
    if not td: return "N/A"
    
    total_seconds = int(td.total_seconds())
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0 and days == 0: # N'affiche les minutes que s'il n'y a pas de jours
        parts.append(f"{minutes}m")
    if not parts and seconds > 0:
        return f"{seconds}s"
    
    return " ".join(parts) if parts else "0m"

def get_player_notif_settings(player: PlayerProfile) -> dict:
    """Charge les paramètres de notification du joueur à partir du JSON en base de données."""
    default_settings = {
        "low_vitals": True,
        "cravings": True,
        "friend_messages": True
    }
    if not player.notifications_config:
        return default_settings.copy()
    try:
        settings = json.loads(player.notifications_config)
        # Ensure all keys from default are present
        for key, value in default_settings.items():
            if key not in settings:
                settings[key] = value
        return settings
    except json.JSONDecodeError:
        return default_settings.copy()