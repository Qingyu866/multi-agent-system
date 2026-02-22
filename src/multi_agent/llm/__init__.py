"""
LLM integration for agent communication.
"""

from multi_agent.llm.client import LLMClient, ExtendedLLMConfig
from multi_agent.llm.agent import LLMAgent, AgentModelManager

__all__ = [
    "LLMClient",
    "ExtendedLLMConfig",
    "LLMAgent",
    "AgentModelManager",
]
