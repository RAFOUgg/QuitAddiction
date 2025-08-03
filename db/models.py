# --- db/models.py ---
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class ServerState(Base):
    __tablename__ = "server_state"
    id = Column(Integer, primary_key=True)
    guild_id = Column(String, unique=True)
    admin_role_id = Column(String, nullable=True) # Ajouter cette ligne
    game_channel_id = Column(String, nullable=True) # Ajouter cette ligne
    game_started = Column(Boolean, default=False) # Ajouter cette ligne
    phys = Column(Float, default=100)
    ment = Column(Float, default=100)
    happy = Column(Float, default=80)
    stress = Column(Float, default=20)
    food = Column(Float, default=100)
    water = Column(Float, default=100)
    energy = Column(Float, default=100)
    addiction = Column(Float, default=0)
    pain = Column(Float, default=0)
    bladder = Column(Float, default=0)
    trip = Column(Float, default=0)
    tox = Column(Float, default=0)
    wallet = Column(Integer, default=0)
    last_update = Column(DateTime, default=datetime.datetime.utcnow)

class PlayerProfile(Base):
    __tablename__ = "player_profile"
    id = Column(Integer, primary_key=True)
    user_id = Column(String)
    guild_id = Column(String)
    contributions = Column(Integer, default=0)
    actions_done = Column(Integer, default=0)

class ActionLog(Base):
    __tablename__ = "action_log"
    id = Column(Integer, primary_key=True)
    guild_id = Column(String)
    user_id = Column(String)
    action = Column(String)
    effect = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)