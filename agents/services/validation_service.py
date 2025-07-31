"""
Service for input validation and sanitization.
"""
from typing import Any, Dict, List, Optional, Union
from ..common.exceptions import ValidationError


class ValidationService:
    """Handles input validation and sanitization"""
    
    @staticmethod
    def validate_brief_id(brief_id: Any) -> int:
        """Validate and convert brief_id to integer"""
        try:
            brief_id_int = int(brief_id)
            if brief_id_int <= 0:
                raise ValidationError("Brief ID must be a positive integer")
            return brief_id_int
        except (ValueError, TypeError):
            raise ValidationError("Brief ID must be a valid integer")
    
    @staticmethod
    def validate_positive_int(value: Any, field_name: str, min_value: int = 1) -> int:
        """Validate positive integer field"""
        try:
            int_value = int(value)
            if int_value < min_value:
                raise ValidationError(f"{field_name} must be at least {min_value}")
            return int_value
        except (ValueError, TypeError):
            raise ValidationError(f"{field_name} must be a valid integer")
    
    @staticmethod
    def validate_string(value: Any, field_name: str, max_length: Optional[int] = None) -> str:
        """Validate string field"""
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string")
        
        if not value.strip():
            raise ValidationError(f"{field_name} cannot be empty")
        
        if max_length and len(value) > max_length:
            raise ValidationError(f"{field_name} cannot exceed {max_length} characters")
        
        return value.strip()
    
    @staticmethod
    def validate_choice(value: Any, field_name: str, choices: List[str]) -> str:
        """Validate that value is one of the allowed choices"""
        if value not in choices:
            raise ValidationError(f"{field_name} must be one of: {', '.join(choices)}")
        return value
    
    @staticmethod
    def validate_float_range(
        value: Any, 
        field_name: str, 
        min_value: float = 0.0, 
        max_value: float = 1.0
    ) -> float:
        """Validate float within range"""
        try:
            float_value = float(value)
            if not (min_value <= float_value <= max_value):
                raise ValidationError(
                    f"{field_name} must be between {min_value} and {max_value}"
                )
            return float_value
        except (ValueError, TypeError):
            raise ValidationError(f"{field_name} must be a valid number")
    
    @staticmethod
    def validate_list_length(
        value: List[Any], 
        field_name: str, 
        min_length: int = 0, 
        max_length: Optional[int] = None
    ) -> List[Any]:
        """Validate list length"""
        if not isinstance(value, list):
            raise ValidationError(f"{field_name} must be a list")
        
        if len(value) < min_length:
            raise ValidationError(f"{field_name} must have at least {min_length} items")
        
        if max_length and len(value) > max_length:
            raise ValidationError(f"{field_name} cannot have more than {max_length} items")
        
        return value
    
    @staticmethod
    def sanitize_content(content: str, max_length: int = 10000) -> str:
        """Sanitize content for processing"""
        if not content:
            return ""
        
        # Basic sanitization
        sanitized = content.strip()
        
        # Truncate if too long
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length] + "..."
        
        return sanitized