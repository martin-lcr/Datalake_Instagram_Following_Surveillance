"""
Modèles Pydantic pour l'API FastAPI
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class FollowerRecord(BaseModel):
    """Modèle pour un follower"""
    username: str
    full_name: Optional[str]
    is_private: Optional[bool]
    is_verified: Optional[bool]
    follower_count: Optional[int]
    predicted_gender: str
    confidence: float
    scraped_at: datetime
    target_account: str

    class Config:
        from_attributes = True


class FollowingRecord(BaseModel):
    """Modèle pour un following (compte suivi)"""
    username: str
    full_name: Optional[str]
    is_private: Optional[bool]
    is_verified: Optional[bool]
    follower_count: Optional[int]
    predicted_gender: str
    confidence: float
    scraped_at: datetime
    target_account: str

    class Config:
        from_attributes = True


class DailyDiffRecord(BaseModel):
    """Modèle pour les changements quotidiens"""
    username: str
    full_name: Optional[str]
    predicted_gender: str
    confidence: float
    change_type: str  # 'added' ou 'deleted'
    data_type: str  # 'followers' ou 'following'
    comparison_date: str
    scraped_at: Optional[datetime]

    class Config:
        from_attributes = True


class GenderStats(BaseModel):
    """Statistiques par genre"""
    male: int = 0
    female: int = 0
    unknown: int = 0


class StatsResponse(BaseModel):
    """Réponse pour les statistiques globales"""
    total_followers: int
    total_following: int
    latest_followers_added: int
    latest_followers_deleted: int
    latest_following_added: int
    latest_following_deleted: int
    last_update: Optional[datetime]


class GenderStatsResponse(BaseModel):
    """Réponse pour les statistiques de genre"""
    data_type: str
    total: int
    by_gender: GenderStats
    percentages: dict = Field(default_factory=dict)
