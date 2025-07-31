"""
Custom exceptions for agent operations.
"""

class AgentError(Exception):
    """Base exception for all agent-related errors"""
    pass

class OpenAIError(AgentError):
    """Raised when OpenAI API operations fail"""
    pass

class JSONParsingError(AgentError):
    """Raised when JSON parsing fails"""
    pass

class PromptTemplateError(AgentError):
    """Raised when prompt template operations fail"""
    pass

class ValidationError(AgentError):
    """Raised when input validation fails"""
    pass