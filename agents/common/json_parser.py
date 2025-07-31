"""
Robust JSON parsing utilities with fallback strategies.
"""
import json
import re
from typing import Any, Dict, List, Union, Optional

from .exceptions import JSONParsingError


class JSONParser:
    """Handles JSON parsing with multiple fallback strategies"""
    
    @staticmethod
    def parse_response(response: str, expected_type: str = "auto") -> Union[Dict, List]:
        """
        Parse JSON response with multiple fallback strategies
        
        Args:
            response: Raw response string from OpenAI
            expected_type: "dict", "list", or "auto" to detect
            
        Returns:
            Parsed JSON object (dict or list)
            
        Raises:
            JSONParsingError: If all parsing strategies fail
        """
        if not response or not response.strip():
            raise JSONParsingError("Empty response provided")
        
        # Strategy 1: Direct JSON parsing
        try:
            parsed = json.loads(response.strip())
            return JSONParser._validate_type(parsed, expected_type)
        except json.JSONDecodeError:
            pass
        
        # Strategy 2: Extract from markdown code block
        try:
            json_match = re.search(
                r'```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```', 
                response, 
                re.DOTALL
            )
            if json_match:
                parsed = json.loads(json_match.group(1))
                return JSONParser._validate_type(parsed, expected_type)
        except json.JSONDecodeError:
            pass
        
        # Strategy 3: Find JSON object/array in text
        try:
            # Look for JSON object
            if expected_type in ["dict", "auto"]:
                obj_match = re.search(r'\{.*\}', response, re.DOTALL)
                if obj_match:
                    parsed = json.loads(obj_match.group(0))
                    return JSONParser._validate_type(parsed, expected_type)
            
            # Look for JSON array
            if expected_type in ["list", "auto"]:
                arr_match = re.search(r'\[.*\]', response, re.DOTALL)
                if arr_match:
                    parsed = json.loads(arr_match.group(0))
                    return JSONParser._validate_type(parsed, expected_type)
        except json.JSONDecodeError:
            pass
        
        # All strategies failed
        raise JSONParsingError(
            f"Failed to parse JSON from response. Expected {expected_type}. "
            f"Raw response: {response[:200]}..."
        )
    
    @staticmethod
    def _validate_type(parsed: Any, expected_type: str) -> Union[Dict, List]:
        """Validate that parsed JSON matches expected type"""
        if expected_type == "auto":
            return parsed
        elif expected_type == "dict" and isinstance(parsed, dict):
            return parsed
        elif expected_type == "list" and isinstance(parsed, list):
            return parsed
        else:
            raise JSONParsingError(
                f"Parsed JSON type {type(parsed).__name__} doesn't match expected {expected_type}"
            )
    
    @staticmethod
    def safe_get(data: Dict, key: str, default: Any = None) -> Any:
        """Safely get value from dictionary with default"""
        return data.get(key, default)
    
    @staticmethod
    def extract_fields(data: Dict, required_fields: List[str]) -> Dict[str, Any]:
        """Extract required fields from data, raising error if missing"""
        result = {}
        missing_fields = []
        
        for field in required_fields:
            if field in data:
                result[field] = data[field]
            else:
                missing_fields.append(field)
        
        if missing_fields:
            raise JSONParsingError(f"Missing required fields: {missing_fields}")
        
        return result