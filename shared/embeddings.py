import os
import json
import pickle
import numpy as np
from typing import List, Optional, Dict, Tuple
from pathlib import Path
import openai
from openai import OpenAI

class EmbeddingManager:
    """Simple file-based embedding storage for MVP. Can be upgraded to vector DB later."""
    
    def __init__(self, storage_dir: str = "embeddings_storage"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        
        # Initialize OpenAI client only if API key is available
        try:
            self.client = OpenAI()  # Uses OPENAI_API_KEY from environment
            self.client_available = True
        except Exception as e:
            print(f"Warning: OpenAI client not available: {e}")
            self.client = None
            self.client_available = False
        
        # Cache for embeddings to avoid repeated API calls
        self.embedding_cache: Dict[str, List[float]] = {}
        self._load_cache()
    
    def _get_cache_path(self) -> Path:
        return self.storage_dir / "embedding_cache.pkl"
    
    def _load_cache(self):
        """Load embedding cache from disk"""
        cache_path = self._get_cache_path()
        if cache_path.exists():
            try:
                with open(cache_path, 'rb') as f:
                    self.embedding_cache = pickle.load(f)
            except Exception as e:
                print(f"Warning: Could not load embedding cache: {e}")
                self.embedding_cache = {}
    
    def _save_cache(self):
        """Save embedding cache to disk"""
        try:
            with open(self._get_cache_path(), 'wb') as f:
                pickle.dump(self.embedding_cache, f)
        except Exception as e:
            print(f"Warning: Could not save embedding cache: {e}")
    
    def get_embedding(self, text: str, model: str = "text-embedding-3-small") -> List[float]:
        """Get embedding for text, with caching"""
        # Create cache key
        cache_key = f"{model}:{hash(text)}"
        
        if cache_key in self.embedding_cache:
            return self.embedding_cache[cache_key]
        
        if not self.client_available:
            print("Warning: OpenAI client not available, returning zero vector")
            return [0.0] * 1536  # text-embedding-3-small dimension
        
        try:
            response = self.client.embeddings.create(
                model=model,
                input=text
            )
            embedding = response.data[0].embedding
            
            # Cache the result
            self.embedding_cache[cache_key] = embedding
            self._save_cache()
            
            return embedding
        except Exception as e:
            print(f"Error getting embedding: {e}")
            # Return zero vector as fallback
            return [0.0] * 1536  # text-embedding-3-small dimension
    
    def get_embeddings_batch(self, texts: List[str], model: str = "text-embedding-3-small") -> List[List[float]]:
        """Get embeddings for multiple texts efficiently"""
        embeddings = []
        texts_to_embed = []
        indices_to_embed = []
        
        # Check cache first
        for i, text in enumerate(texts):
            cache_key = f"{model}:{hash(text)}"
            if cache_key in self.embedding_cache:
                embeddings.append(self.embedding_cache[cache_key])
            else:
                embeddings.append(None)  # Placeholder
                texts_to_embed.append(text)
                indices_to_embed.append(i)
        
        # Get embeddings for uncached texts
        if texts_to_embed:
            try:
                response = self.client.embeddings.create(
                    model=model,
                    input=texts_to_embed
                )
                
                for i, (text_idx, embedding_data) in enumerate(zip(indices_to_embed, response.data)):
                    embedding = embedding_data.embedding
                    embeddings[text_idx] = embedding
                    
                    # Cache the result
                    cache_key = f"{model}:{hash(texts_to_embed[i])}"
                    self.embedding_cache[cache_key] = embedding
                
                self._save_cache()
                
            except Exception as e:
                print(f"Error getting batch embeddings: {e}")
                # Fill remaining with zero vectors
                for i in indices_to_embed:
                    if embeddings[i] is None:
                        embeddings[i] = [0.0] * 1536
        
        return embeddings
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        vec1_np = np.array(vec1)
        vec2_np = np.array(vec2)
        
        dot_product = np.dot(vec1_np, vec2_np)
        norm1 = np.linalg.norm(vec1_np)
        norm2 = np.linalg.norm(vec2_np)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def find_similar_items(
        self, 
        query_embedding: List[float], 
        item_embeddings: List[Tuple[int, List[float]]], 
        top_k: int = 5,
        threshold: float = 0.7
    ) -> List[Tuple[int, float]]:
        """Find most similar items to query"""
        similarities = []
        
        for item_id, embedding in item_embeddings:
            similarity = self.cosine_similarity(query_embedding, embedding)
            if similarity >= threshold:
                similarities.append((item_id, similarity))
        
        # Sort by similarity (descending) and return top k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def detect_content_gaps(
        self, 
        existing_embeddings: List[List[float]], 
        target_topics: List[str],
        gap_threshold: float = 0.6
    ) -> List[str]:
        """Detect topics that are not well covered by existing content"""
        gaps = []
        
        for topic in target_topics:
            topic_embedding = self.get_embedding(topic)
            
            # Find best match among existing content
            best_similarity = 0.0
            for existing_embedding in existing_embeddings:
                similarity = self.cosine_similarity(topic_embedding, existing_embedding)
                best_similarity = max(best_similarity, similarity)
            
            # If no good match found, it's a gap
            if best_similarity < gap_threshold:
                gaps.append(topic)
        
        return gaps
    
    def cluster_similar_content(
        self, 
        items: List[Tuple[int, List[float]]], 
        similarity_threshold: float = 0.8
    ) -> List[List[int]]:
        """Simple clustering of similar content items"""
        clusters = []
        used_items = set()
        
        for i, (item_id, embedding) in enumerate(items):
            if item_id in used_items:
                continue
            
            # Start new cluster
            cluster = [item_id]
            used_items.add(item_id)
            
            # Find similar items
            for j, (other_id, other_embedding) in enumerate(items[i+1:], i+1):
                if other_id in used_items:
                    continue
                
                similarity = self.cosine_similarity(embedding, other_embedding)
                if similarity >= similarity_threshold:
                    cluster.append(other_id)
                    used_items.add(other_id)
            
            clusters.append(cluster)
        
        return clusters

# Global embedding manager instance
embedding_manager = EmbeddingManager()