from .models import Base, engine, SessionLocal, ServerConfig, Cook

def init_db():
    """
    Initialise la base de données.
    Crée toutes les tables définies dans models.py si elles n'existent pas déjà.
    Cette fonction est appelée une seule fois au démarrage du bot.
    """
    Base.metadata.create_all(bind=engine)

def get_db_session():
    """Retourne une nouvelle session de base de données."""
    return SessionLocal()

# --- Fonctions pour ServerConfig ---

def get_or_create_server_config(session, guild_id: int) -> ServerConfig:
    """
    Récupère la configuration d'un serveur depuis la DB.
    Si elle n'existe pas, elle est créée et retournée.
    """
    config = session.query(ServerConfig).filter(ServerConfig.guild_id == guild_id).first()
    if not config:
        config = ServerConfig(guild_id=guild_id)
        session.add(config)
        session.commit()
    return config

def update_staff_role(session, guild_id: int, role_id: int):
    """Met à jour le rôle staff pour un serveur."""
    config = get_or_create_server_config(session, guild_id)
    config.staff_role_id = role_id
    session.commit()

def update_main_channel(session, guild_id: int, channel_id: int):
    """Met à jour le salon principal pour un serveur."""
    config = get_or_create_server_config(session, guild_id)
    config.main_channel_id = channel_id
    session.commit()

# --- Fonctions pour le Cuisinier (à venir) ---

def get_or_create_cook(session, guild_id: int) -> Cook:
    """
    Récupère les données du cuisinier pour un serveur.
    S'il n'existe pas, il est créé et retourné.
    """
    cook = session.query(Cook).filter(Cook.guild_id == guild_id).first()
    if not cook:
        cook = Cook(guild_id=guild_id)
        session.add(cook)
        session.commit()
    return cook