"""
Database Schemas

Beer Pong app schemas using Pydantic. Each model name maps to a MongoDB
collection using the lowercase name (e.g., Match -> "match").
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime

class Player(BaseModel):
    """
    Players collection schema
    Collection name: "player"
    """
    name: str = Field(..., description="Player display name")
    nickname: Optional[str] = Field(None, description="Optional nickname")
    avatar_url: Optional[str] = Field(None, description="Avatar image URL")

class HitEvent(BaseModel):
    """Embedded event stored inside a match document"""
    team: Literal['A', 'B'] = Field(..., description="Which team made the hit")
    shooter: Optional[str] = Field(None, description="Name of the shooter")
    cups: int = Field(1, ge=1, le=10, description="How many cups were hit in this turn")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class Match(BaseModel):
    """
    Matches collection schema
    Collection name: "match"
    """
    team_a: str = Field(..., description="Team A name")
    team_b: str = Field(..., description="Team B name")
    cups_per_side: int = Field(10, ge=1, le=20, description="Starting cups per side")
    cups_remaining_a: int = Field(10, ge=0)
    cups_remaining_b: int = Field(10, ge=0)
    status: Literal['ongoing', 'finished'] = Field('ongoing')
    winner: Optional[Literal['A', 'B']] = Field(None, description="Winner team code if finished")
    events: List[HitEvent] = Field(default_factory=list, description="Chronological list of hit events")
