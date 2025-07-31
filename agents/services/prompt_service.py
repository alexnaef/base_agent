"""
Service for managing and rendering prompt templates.
"""
from typing import Dict, Any, Optional
from string import Template

from ..common.exceptions import PromptTemplateError


class PromptService:
    """Manages prompt templates and rendering"""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.templates: Dict[str, str] = {}
    
    def register_template(self, name: str, template: str):
        """Register a prompt template"""
        self.templates[name] = template
    
    def render_template(self, template_name: str, **kwargs) -> str:
        """
        Render a template with the provided variables
        
        Args:
            template_name: Name of the registered template
            **kwargs: Variables to substitute in template
            
        Returns:
            Rendered template string
            
        Raises:
            PromptTemplateError: If template not found or rendering fails
        """
        if template_name not in self.templates:
            raise PromptTemplateError(f"Template '{template_name}' not found for {self.agent_name}")
        
        try:
            template = Template(self.templates[template_name])
            return template.safe_substitute(**kwargs)
        except Exception as e:
            raise PromptTemplateError(f"Failed to render template '{template_name}': {str(e)}")
    
    def get_system_message(self, role_description: str) -> str:
        """Create a standard system message"""
        return f"You are an expert {role_description}."
    
    def validate_required_params(self, template_name: str, **kwargs):
        """Validate that all required parameters are provided"""
        template = self.templates.get(template_name, "")
        
        # Extract template variables (simple approach)
        import re
        variables = re.findall(r'\$\{?(\w+)\}?', template)
        
        missing = [var for var in variables if var not in kwargs]
        if missing:
            raise PromptTemplateError(
                f"Missing required parameters for template '{template_name}': {missing}"
            )