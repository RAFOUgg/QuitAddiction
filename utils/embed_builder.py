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