"""
Custom exceptions for the multi-agent system.
"""

from typing import Optional

from multi_agent.core.types import AgentRole


class MultiAgentError(Exception):
    """Base exception for all multi-agent system errors."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class PermissionDeniedError(MultiAgentError):
    """Raised when an agent attempts an unauthorized action."""
    
    def __init__(
        self,
        agent: AgentRole,
        target: AgentRole,
        action: str,
        details: Optional[dict] = None,
    ):
        self.agent = agent
        self.target = target
        self.action = action
        message = f"Agent '{agent.value}' is not authorized to {action} with agent '{target.value}'"
        super().__init__(message, details)


class TaskLoopError(MultiAgentError):
    """Raised when a task enters a detected loop cycle."""
    
    def __init__(
        self,
        task_id: str,
        iteration_count: int,
        max_iterations: int,
        details: Optional[dict] = None,
    ):
        self.task_id = task_id
        self.iteration_count = iteration_count
        self.max_iterations = max_iterations
        message = (
            f"Task '{task_id}' has exceeded maximum iterations "
            f"({iteration_count}/{max_iterations})"
        )
        super().__init__(message, details)


class ScopeDriftError(MultiAgentError):
    """Raised when discussion drifts from original project scope."""
    
    def __init__(
        self,
        task_id: str,
        original_scope: str,
        detected_drift: str,
        details: Optional[dict] = None,
    ):
        self.task_id = task_id
        self.original_scope = original_scope
        self.detected_drift = detected_drift
        message = (
            f"Scope drift detected in task '{task_id}': "
            f"Original scope: '{original_scope}', Detected: '{detected_drift}'"
        )
        super().__init__(message, details)


class AgentNotFoundError(MultiAgentError):
    """Raised when a requested agent is not found."""
    
    def __init__(self, agent_role: AgentRole, details: Optional[dict] = None):
        self.agent_role = agent_role
        message = f"Agent with role '{agent_role.value}' not found"
        super().__init__(message, details)


class MemoryError(MultiAgentError):
    """Raised when there's an issue with memory operations."""
    
    def __init__(
        self,
        operation: str,
        agent: Optional[AgentRole] = None,
        details: Optional[dict] = None,
    ):
        self.operation = operation
        self.agent = agent
        agent_str = f" for agent '{agent.value}'" if agent else ""
        message = f"Memory operation '{operation}' failed{agent_str}"
        super().__init__(message, details)


class AdvisorInterventionError(MultiAgentError):
    """Raised when advisor intervention fails."""
    
    def __init__(
        self,
        reason: str,
        task_id: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        self.reason = reason
        self.task_id = task_id
        task_str = f" for task '{task_id}'" if task_id else ""
        message = f"Advisor intervention failed{task_str}: {reason}"
        super().__init__(message, details)


class TemporaryPermissionError(MultiAgentError):
    """Raised when temporary permission operations fail."""
    
    def __init__(
        self,
        permission_id: str,
        reason: str,
        details: Optional[dict] = None,
    ):
        self.permission_id = permission_id
        self.reason = reason
        message = f"Temporary permission '{permission_id}' error: {reason}"
        super().__init__(message, details)
