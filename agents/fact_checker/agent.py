"""
Fact Checker Agent - core business logic.
"""
import sys
import os
from typing import List, Any

# Add parent directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from agents.common import BaseAgent
from config import AGENT_INSTRUCTIONS
from tools import ClaimExtractorTool, VerifierTool, CredibilityAssessorTool, ReportGeneratorTool


class FactCheckerAgent(BaseAgent):
    """Agent specialized in fact-checking and source credibility assessment"""
    
    def __init__(self):
        super().__init__(
            name="fact-checker",
            instructions=AGENT_INSTRUCTIONS
        )
        
        # Initialize tools
        self.claim_extractor_tool = ClaimExtractorTool(self)
        self.verifier_tool = VerifierTool(self)
        self.credibility_assessor_tool = CredibilityAssessorTool(self)
        self.report_generator_tool = ReportGeneratorTool(self)
    
    def get_tools(self) -> List[Any]:
        """Return list of tools this agent provides"""
        return [
            self.claim_extractor_tool,
            self.verifier_tool,
            self.credibility_assessor_tool,
            self.report_generator_tool
        ]