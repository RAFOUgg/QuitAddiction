# --- utils/embed_builder.py ---
import discord

def create_styled_embed(title: str, description: str, color: discord.Color) -> discord.Embed:
    """
    Crée un embed Discord avec un style cohérent.
    """
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    embed.set_footer(text="QuitAddiction Bot")
    return embed

def generate_progress_bar(current: float, total: float, length: int = 10, bar_char: str = "█", empty_char: str = " ") -> str:
    """
    Génère une barre de progression textuelle.
    """
    if total == 0: return ""
    filled_length = int(length * current // total)
    bar = bar_char * filled_length + empty_char * (length - filled_length)
    return f"[{bar}] {current:.0f}/{total:.0f}"