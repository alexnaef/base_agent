from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class ResearchStatusEnum(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class VerificationStatusEnum(str, Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    DISPUTED = "disputed"
    NEEDS_REVIEW = "needs_review"

# Research Brief Schemas
class ResearchBriefCreate(BaseModel):
    topic: str
    angle: Optional[str] = None
    tone: str = "informative"
    target_length_min: int = 30
    additional_instructions: Optional[str] = None

class ResearchBriefUpdate(BaseModel):
    angle: Optional[str] = None
    tone: Optional[str] = None
    target_length_min: Optional[int] = None
    additional_instructions: Optional[str] = None
    status: Optional[ResearchStatusEnum] = None

class ResearchBrief(BaseModel):
    id: int
    topic: str
    angle: Optional[str]
    tone: str
    target_length_min: int
    additional_instructions: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Research Item Schemas
class ResearchItemCreate(BaseModel):
    brief_id: int
    title: str
    url: str
    description: Optional[str] = None
    content: Optional[str] = None
    source_type: str = "web"

class ResearchItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    credibility_score: Optional[float] = None
    relevance_score: Optional[float] = None
    verification_status: Optional[VerificationStatusEnum] = None

class ResearchItem(BaseModel):
    id: int
    brief_id: int
    title: str
    url: str
    description: Optional[str]
    content: Optional[str]
    source_type: str
    credibility_score: float
    relevance_score: float
    verification_status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# Claim Schemas
class ClaimCreate(BaseModel):
    brief_id: int
    text: str
    category: Optional[str] = None
    source_ids: List[int] = []

class ClaimUpdate(BaseModel):
    text: Optional[str] = None
    category: Optional[str] = None
    veracity_score: Optional[float] = None
    importance_score: Optional[float] = None
    verification_status: Optional[VerificationStatusEnum] = None
    verification_notes: Optional[str] = None

class Claim(BaseModel):
    id: int
    brief_id: int
    text: str
    category: Optional[str]
    veracity_score: float
    importance_score: float
    verification_status: str
    verification_notes: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

# Podcast Script Schemas
class PodcastScriptCreate(BaseModel):
    brief_id: int
    title: str
    outline: Optional[Dict[str, Any]] = None
    content: str

class PodcastScriptUpdate(BaseModel):
    title: Optional[str] = None
    outline: Optional[Dict[str, Any]] = None
    content: Optional[str] = None
    word_count: Optional[int] = None
    estimated_read_time_min: Optional[float] = None
    citation_count: Optional[int] = None
    quality_score: Optional[float] = None
    status: Optional[str] = None

class PodcastScript(BaseModel):
    id: int
    brief_id: int
    title: str
    outline: Optional[Dict[str, Any]]
    content: str
    word_count: Optional[int]
    estimated_read_time_min: Optional[float]
    citation_count: int
    quality_score: float
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Research Query Schemas
class ResearchQueryCreate(BaseModel):
    brief_id: int
    query_text: str
    search_engine: str = "brave"

class ResearchQuery(BaseModel):
    id: int
    brief_id: int
    query_text: str
    search_engine: str
    status: str
    results_count: int
    executed_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

# Agent Event Schemas
class AgentEventCreate(BaseModel):
    brief_id: Optional[int] = None
    agent_name: str
    event_type: str
    payload: Optional[Dict[str, Any]] = None
    message: Optional[str] = None

class AgentEvent(BaseModel):
    id: int
    brief_id: Optional[int]
    agent_name: str
    event_type: str
    payload: Optional[Dict[str, Any]]
    message: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

# Response schemas for complex queries
class ResearchBriefWithItems(ResearchBrief):
    research_items: List[ResearchItem] = []
    claims: List[Claim] = []
    podcast_scripts: List[PodcastScript] = []

class ClaimWithSources(Claim):
    sources: List[ResearchItem] = []

# Utility schemas
class ResearchProgress(BaseModel):
    brief_id: int
    total_queries: int
    completed_queries: int
    total_items: int
    verified_items: int
    total_claims: int
    verified_claims: int
    completion_percentage: float
    
class QualityMetrics(BaseModel):
    brief_id: int
    average_credibility_score: float
    average_veracity_score: float
    citation_coverage: float  # percentage of claims with sources
    source_diversity: int  # number of unique domains/sources