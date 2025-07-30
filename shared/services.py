"""
Service layer for database operations. Provides high-level functions for agents to use.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from .database import db_manager
from .models import (
    ResearchBrief, ResearchItem, Claim, PodcastScript, 
    ResearchQuery, AgentEvent, claim_sources
)
from .schemas import (
    ResearchBriefCreate, ResearchItemCreate, ClaimCreate, 
    PodcastScriptCreate, ResearchQueryCreate, AgentEventCreate
)
from .embeddings import embedding_manager

class ResearchService:
    """Service for managing research briefs and related operations"""
    
    def create_brief(self, brief_data: ResearchBriefCreate) -> ResearchBrief:
        """Create a new research brief"""
        with db_manager.session_scope() as session:
            brief = ResearchBrief(**brief_data.dict())
            session.add(brief)
            session.flush()  # Get the ID
            session.refresh(brief)  # Refresh to ensure we have all data
            # Create a new instance with the data to avoid session issues
            brief_dict = {
                'id': brief.id,
                'topic': brief.topic,
                'angle': brief.angle,
                'tone': brief.tone,
                'target_length_min': brief.target_length_min,
                'additional_instructions': brief.additional_instructions,
                'status': brief.status,
                'created_at': brief.created_at,
                'updated_at': brief.updated_at
            }
            return brief_dict
    
    def get_brief(self, brief_id: int) -> Optional[Dict[str, Any]]:
        """Get a research brief by ID"""
        with db_manager.session_scope() as session:
            brief = session.query(ResearchBrief).filter(ResearchBrief.id == brief_id).first()
            if brief:
                return {
                    'id': brief.id,
                    'topic': brief.topic,
                    'angle': brief.angle,
                    'tone': brief.tone,
                    'target_length_min': brief.target_length_min,
                    'additional_instructions': brief.additional_instructions,
                    'status': brief.status,
                    'created_at': brief.created_at,
                    'updated_at': brief.updated_at
                }
            return None
    
    def update_brief_status(self, brief_id: int, status: str) -> bool:
        """Update the status of a research brief"""
        with db_manager.session_scope() as session:
            brief = session.query(ResearchBrief).filter(ResearchBrief.id == brief_id).first()
            if brief:
                brief.status = status
                return True
            return False
    
    def add_research_item(self, item_data: ResearchItemCreate) -> ResearchItem:
        """Add a research item and generate its embedding"""
        with db_manager.session_scope() as session:
            item = ResearchItem(**item_data.dict())
            
            # Generate embedding for content if available
            if item.content:
                embedding = embedding_manager.get_embedding(item.content)
                item.embedding_vector = str(embedding)  # Store as JSON string
            
            session.add(item)
            session.flush()
            return item
    
    def add_claim(self, claim_data: ClaimCreate) -> Claim:
        """Add a claim and link it to sources"""
        with db_manager.session_scope() as session:
            claim = Claim(
                brief_id=claim_data.brief_id,
                text=claim_data.text,
                category=claim_data.category
            )
            session.add(claim)
            session.flush()
            
            # Link to sources if provided
            if claim_data.source_ids:
                sources = session.query(ResearchItem).filter(
                    ResearchItem.id.in_(claim_data.source_ids)
                ).all()
                claim.sources.extend(sources)
            
            return claim
    
    def get_research_progress(self, brief_id: int) -> Dict[str, Any]:
        """Get research progress metrics for a brief"""
        with db_manager.session_scope() as session:
            # Count total and completed queries
            total_queries = session.query(ResearchQuery).filter(
                ResearchQuery.brief_id == brief_id
            ).count()
            
            completed_queries = session.query(ResearchQuery).filter(
                and_(ResearchQuery.brief_id == brief_id, ResearchQuery.status == "completed")
            ).count()
            
            # Count research items
            total_items = session.query(ResearchItem).filter(
                ResearchItem.brief_id == brief_id
            ).count()
            
            verified_items = session.query(ResearchItem).filter(
                and_(ResearchItem.brief_id == brief_id, ResearchItem.verification_status == "verified")
            ).count()
            
            # Count claims
            total_claims = session.query(Claim).filter(
                Claim.brief_id == brief_id
            ).count()
            
            verified_claims = session.query(Claim).filter(
                and_(Claim.brief_id == brief_id, Claim.verification_status == "verified")
            ).count()
            
            # Calculate completion percentage
            completion_percentage = 0.0
            if total_queries > 0:
                completion_percentage = (completed_queries / total_queries) * 100
            
            return {
                "brief_id": brief_id,
                "total_queries": total_queries,
                "completed_queries": completed_queries,
                "total_items": total_items,
                "verified_items": verified_items,
                "total_claims": total_claims,
                "verified_claims": verified_claims,
                "completion_percentage": completion_percentage
            }
    
    def find_similar_items(self, brief_id: int, query_text: str, top_k: int = 5) -> List[ResearchItem]:
        """Find research items similar to the query text"""
        with db_manager.session_scope() as session:
            # Get all items for this brief that have embeddings
            items = session.query(ResearchItem).filter(
                and_(
                    ResearchItem.brief_id == brief_id,
                    ResearchItem.embedding_vector.isnot(None)
                )
            ).all()
            
            if not items:
                return []
            
            # Get query embedding
            query_embedding = embedding_manager.get_embedding(query_text)
            
            # Calculate similarities
            item_embeddings = []
            for item in items:
                try:
                    embedding = eval(item.embedding_vector)  # Convert string back to list
                    item_embeddings.append((item.id, embedding))
                except:
                    continue
            
            # Find similar items
            similar_ids = embedding_manager.find_similar_items(
                query_embedding, item_embeddings, top_k
            )
            
            # Return the actual items
            if similar_ids:
                similar_item_ids = [item_id for item_id, _ in similar_ids]
                return session.query(ResearchItem).filter(
                    ResearchItem.id.in_(similar_item_ids)
                ).all()
            
            return []

class QueryService:
    """Service for managing research queries"""
    
    def add_query(self, query_data: ResearchQueryCreate) -> Dict[str, Any]:
        """Add a new research query"""
        with db_manager.session_scope() as session:
            query = ResearchQuery(**query_data.dict())
            session.add(query)
            session.flush()
            session.refresh(query)
            return {
                'id': query.id,
                'brief_id': query.brief_id,
                'query_text': query.query_text,
                'search_engine': query.search_engine,
                'status': query.status,
                'results_count': query.results_count,
                'executed_at': query.executed_at,
                'created_at': query.created_at
            }
    
    def update_query_status(self, query_id: int, status: str, results_count: int = 0) -> bool:
        """Update query status and results count"""
        with db_manager.session_scope() as session:
            query = session.query(ResearchQuery).filter(ResearchQuery.id == query_id).first()
            if query:
                query.status = status
                query.results_count = results_count
                if status == "completed":
                    query.executed_at = func.now()
                return True
            return False

class ScriptService:
    """Service for managing podcast scripts"""
    
    def create_script(self, script_data: PodcastScriptCreate) -> PodcastScript:
        """Create a new podcast script"""
        with db_manager.session_scope() as session:
            script = PodcastScript(**script_data.dict())
            
            # Calculate word count and estimated read time
            if script.content:
                script.word_count = len(script.content.split())
                # Average reading speed: 150-160 words per minute for narration
                script.estimated_read_time_min = script.word_count / 155
            
            session.add(script)
            session.flush()
            return script
    
    def update_script_quality(self, script_id: int, quality_score: float, citation_count: int) -> bool:
        """Update script quality metrics"""
        with db_manager.session_scope() as session:
            script = session.query(PodcastScript).filter(PodcastScript.id == script_id).first()
            if script:
                script.quality_score = quality_score
                script.citation_count = citation_count
                return True
            return False

class EventService:
    """Service for logging agent events"""
    
    def log_event(self, event_data: AgentEventCreate) -> AgentEvent:
        """Log an agent event"""
        with db_manager.session_scope() as session:
            event = AgentEvent(**event_data.dict())
            session.add(event)
            session.flush()
            return event
    
    def get_events_for_brief(self, brief_id: int, limit: int = 50) -> List[AgentEvent]:
        """Get recent events for a research brief"""
        with db_manager.session_scope() as session:
            return session.query(AgentEvent).filter(
                AgentEvent.brief_id == brief_id
            ).order_by(AgentEvent.created_at.desc()).limit(limit).all()

# Global service instances
research_service = ResearchService()
query_service = QueryService()
script_service = ScriptService()
event_service = EventService()