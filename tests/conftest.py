"""
Test configuration and fixtures.
"""

import pytest
from typing import Generator

from multi_agent.core.types import AgentRole, ProjectContext
from multi_agent.core.system import MultiAgentSystem


@pytest.fixture
def project_context() -> ProjectContext:
    """Create a test project context."""
    return ProjectContext(
        name="Test Project",
        description="A test project for unit testing",
        requirements=[
            "User authentication",
            "Task management",
            "Data persistence",
        ],
        scope_boundaries=[
            "No third-party integrations",
            "Single user mode only",
            "Local storage only",
        ],
    )


@pytest.fixture
def multi_agent_system(project_context: ProjectContext) -> MultiAgentSystem:
    """Create a test multi-agent system."""
    return MultiAgentSystem(project_context=project_context)
