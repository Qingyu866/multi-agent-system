"""
Permission control systems for the multi-agent system.
"""

from multi_agent.permissions.guard import PermissionGuard, PermissionResult
from multi_agent.permissions.temp_auth import TemporaryAuthManager

__all__ = [
    "PermissionGuard",
    "PermissionResult",
    "TemporaryAuthManager",
]
