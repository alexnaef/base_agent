from datetime import datetime
from typing import Optional, List
from enum import Enum

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import func

Base = declarative_base()

class ResearchStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class VerificationStatus(str, Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    DISPUTED = "disputed"
    NEEDS_REVIEW = "needs_review"

class ResearchBrief(Base):
    __tablename__ = "research_briefs"
    
    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String, nullable=False)
    angle = Column(Text)  # specific focus/perspective
    tone = Column(String, default="informative")  # informative, analytical, narrative
    target_length_min = Column(Integer, default=30)  # target podcast length in minutes
    additional_instructions = Column(Text)
    status = Column(String, default=ResearchStatus.PENDING)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    research_items = relationship("ResearchItem", back_populates="brief")
    claims = relationship("Claim", back_populates="brief")
    podcast_scripts = relationship("PodcastScript", back_populates="brief")

class ResearchItem(Base):
    __tablename__ = "research_items"
    
    id = Column(Integer, primary_key=True, index=True)
    brief_id = Column(Integer, ForeignKey("research_briefs.id"), nullable=False)
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)
    description = Column(Text)
    content = Column(Text)  # scraped/cleaned content
    source_type = Column(String, default="web")  # web, academic, news, etc.
    credibility_score = Column(Float, default=0.5)  # 0.0 to 1.0
    relevance_score = Column(Float, default=0.5)  # 0.0 to 1.0
    verification_status = Column(String, default=VerificationStatus.UNVERIFIED)
    embedding_vector = Column(Text)  # JSON string of embedding vector
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    brief = relationship("ResearchBrief", back_populates="research_items")
    claims = relationship("Claim", secondary="claim_sources", back_populates="sources")

class Claim(Base):
    __tablename__ = "claims"
    
    id = Column(Integer, primary_key=True, index=True)
    brief_id = Column(Integer, ForeignKey("research_briefs.id"), nullable=False)
    text = Column(Text, nullable=False)
    category = Column(String)  # fact, opinion, statistic, quote, etc.
    veracity_score = Column(Float, default=0.5)  # confidence in claim accuracy
    importance_score = Column(Float, default=0.5)  # relevance to research topic
    verification_status = Column(String, default=VerificationStatus.UNVERIFIED)
    verification_notes = Column(Text)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    brief = relationship("ResearchBrief", back_populates="claims")
    sources = relationship("ResearchItem", secondary="claim_sources", back_populates="claims")

# Association table for many-to-many relationship between claims and sources
from sqlalchemy import Table
claim_sources = Table(
    'claim_sources',
    Base.metadata,
    Column('claim_id', Integer, ForeignKey('claims.id'), primary_key=True),
    Column('source_id', Integer, ForeignKey('research_items.id'), primary_key=True)
)

class PodcastScript(Base):
    __tablename__ = "podcast_scripts"
    
    id = Column(Integer, primary_key=True, index=True)
    brief_id = Column(Integer, ForeignKey("research_briefs.id"), nullable=False)
    title = Column(String, nullable=False)
    outline = Column(JSON)  # structured outline with chapters
    content = Column(Text, nullable=False)  # full manuscript
    word_count = Column(Integer)
    estimated_read_time_min = Column(Float)
    citation_count = Column(Integer, default=0)
    quality_score = Column(Float, default=0.5)  # overall quality assessment
    status = Column(String, default="draft")  # draft, reviewed, finalized
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    brief = relationship("ResearchBrief", back_populates="podcast_scripts")

class ResearchQuery(Base):
    __tablename__ = "research_queries"
    
    id = Column(Integer, primary_key=True, index=True)
    brief_id = Column(Integer, ForeignKey("research_briefs.id"), nullable=False)
    query_text = Column(String, nullable=False)
    search_engine = Column(String, default="brave")
    status = Column(String, default=ResearchStatus.PENDING)
    results_count = Column(Integer, default=0)
    executed_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())

class AgentEvent(Base):
    __tablename__ = "agent_events"
    
    id = Column(Integer, primary_key=True, index=True)
    brief_id = Column(Integer, ForeignKey("research_briefs.id"))
    agent_name = Column(String, nullable=False)
    event_type = Column(String, nullable=False)  # started, completed, error, etc.
    payload = Column(JSON)  # event-specific data
    message = Column(Text)
    created_at = Column(DateTime, default=func.now())