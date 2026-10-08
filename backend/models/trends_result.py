# Copyright (c) 2026 ViralMint. All rights reserved.
# Authorial trends persistence entity.
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

from backend.database import Base


class TrendsResult(Base):
    """
    Trends result entity mapping to persistent database records.
    Keeps table name scout_results for seamless backwards compatibility
    with existing SQLite storage and video relations.
    """
    __tablename__ = "scout_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), default="local", index=True)
    job_id = Column(String(36), nullable=True, index=True)

    # Source platform metadata
    platform = Column(String(20), nullable=False, index=True)
    video_id = Column(String(200), nullable=False)
    video_url = Column(Text, nullable=False)
    embed_url = Column(Text, nullable=True)

    # Media and content attributes
    title = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    author = Column(String(200), nullable=True)
    author_url = Column(Text, nullable=True)
    thumbnail_url = Column(Text, nullable=True)

    # Audience metrics
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    duration_seconds = Column(Integer, nullable=True)
    upload_date = Column(DateTime, nullable=True)

    # Proprietary velocity and virality metrics
    virality_score = Column(Float, default=0.0)
    views_per_hour = Column(Float, nullable=True)
    outlier_score = Column(Float, nullable=True)
    subscriber_count = Column(Integer, nullable=True)
    channel_avg_views = Column(Integer, nullable=True)
    niche = Column(String(200), nullable=True)

    # Pipeline execution state
    is_downloaded = Column(Boolean, default=False)
    is_analyzed = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)


# Aliases for transition compatibility
TrendResult = TrendsResult
ScoutResult = TrendsResult
