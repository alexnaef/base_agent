"""
Service for common metrics and calculations.
"""
from typing import Dict, List, Any, Tuple
import re


class MetricsService:
    """Handles common metrics calculations"""
    
    @staticmethod
    def calculate_word_count(text: str) -> int:
        """Calculate word count in text"""
        if not text:
            return 0
        return len(text.split())
    
    @staticmethod
    def calculate_read_time(text: str, words_per_minute: int = 155) -> float:
        """Calculate estimated read time in minutes"""
        word_count = MetricsService.calculate_word_count(text)
        return word_count / words_per_minute
    
    @staticmethod
    def count_citations(text: str) -> int:
        """Count citations in text (Source: pattern)"""
        if not text:
            return 0
        return len(re.findall(r'\(Source:', text))
    
    @staticmethod
    def calculate_completion_percentage(completed: int, total: int) -> float:
        """Calculate completion percentage"""
        if total == 0:
            return 0.0
        return (completed / total) * 100
    
    @staticmethod
    def calculate_average_score(scores: List[float]) -> float:
        """Calculate average score from list"""
        if not scores:
            return 0.0
        return sum(scores) / len(scores)
    
    @staticmethod
    def analyze_query_coverage(queries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze how well queries cover different research angles"""
        if not queries:
            return {
                "categories_covered": [],
                "category_distribution": {},
                "coverage_score": 0.0,
                "balance_assessment": "no_queries"
            }
        
        categories = {}
        for query in queries:
            category = query.get("category", "unknown")
            categories[category] = categories.get(category, 0) + 1
        
        total_queries = len(queries)
        expected_categories = 6  # core_facts, context, events, analysis, perspectives, timeline
        coverage_score = len(categories) / expected_categories * 100
        
        # Check if distribution is balanced
        max_category_count = max(categories.values()) if categories else 0
        balance_threshold = total_queries * 0.4  # No category should have more than 40%
        balance_assessment = "balanced" if max_category_count <= balance_threshold else "unbalanced"
        
        return {
            "categories_covered": list(categories.keys()),
            "category_distribution": categories,
            "coverage_score": round(coverage_score, 1),
            "balance_assessment": balance_assessment
        }
    
    @staticmethod
    def analyze_performance_data(
        performance_data: List[Dict[str, Any]]
    ) -> Tuple[float, List[str]]:
        """Analyze performance data and generate recommendations"""
        if not performance_data:
            return 0.0, ["No performance data available"]
        
        # Calculate average results
        total_results = sum(p.get("results_count", 0) for p in performance_data)
        completed_queries = len([p for p in performance_data if p.get("status") == "completed"])
        avg_results = total_results / completed_queries if completed_queries > 0 else 0
        
        recommendations = []
        
        # Analyze underperforming queries
        underperforming = [
            p for p in performance_data 
            if p.get("results_count", 0) < avg_results * 0.7
        ]
        if underperforming:
            recommendations.append(f"Consider refining {len(underperforming)} underperforming queries")
        
        # Analyze zero-result queries
        zero_results = [p for p in performance_data if p.get("results_count", 0) == 0]
        if zero_results:
            recommendations.append(f"Replace {len(zero_results)} queries that returned no results")
        
        # Overall performance assessment
        if avg_results < 3:
            recommendations.append("Overall query specificity may be too high - consider broader terms")
        elif avg_results > 10:
            recommendations.append("Queries may be too broad - consider more specific targeting")
        
        if not recommendations:
            recommendations.append("Query performance looks good - maintain current strategy")
        
        return avg_results, recommendations
    
    @staticmethod
    def calculate_content_reliability(
        verification_score: float, 
        credibility_score: float
    ) -> str:
        """Calculate overall content reliability assessment"""
        combined_score = (verification_score + credibility_score) / 2
        
        if combined_score >= 0.8:
            return "high"
        elif combined_score >= 0.6:
            return "medium"
        else:
            return "low"