"""
Multi-Agent Collaboration System
A highly realistic software company simulation with hierarchical agent architecture.
"""

__version__ = "0.1.0"

from multi_agent.core.types import AgentRole, AgentMessage, TaskStatus, MessageType, ProjectContext
from multi_agent.core.system import MultiAgentSystem
from multi_agent.config import Config, config

__all__ = [
    "AgentRole",
    "AgentMessage",
    "TaskStatus",
    "MessageType",
    "ProjectContext",
    "MultiAgentSystem",
    "Config",
    "config",
]
