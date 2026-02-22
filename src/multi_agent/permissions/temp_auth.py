"""
Temporary authorization system for emergency situations.
Allows CTO to grant temporary bypass permissions.
"""

from datetime import datetime, timedelta
from typing import Optional

from multi_agent.core.types import AgentRole, TemporaryPermission


class TemporaryAuthManager:
    """
    Manages temporary permission grants for emergency situations.
    
    Key features:
    - Only CTO can initiate temporary permissions
    - Default duration: 30 minutes or task completion
    - Automatic expiration and cleanup
    - Full audit trail
    
    Supported temporary permissions:
    - Developer -> QA: Direct testing submission
    - Designer -> Developer: Direct resource handoff
    """
    
    VALID_TEMP_PERMISSIONS: dict[AgentRole, list[tuple[AgentRole, str]]] = {
        AgentRole.CTO: [
            (AgentRole.DEVELOPER, "direct_qa_access"),
            (AgentRole.DEVELOPER, "direct_designer_access"),
            (AgentRole.QA_ENGINEER, "direct_developer_access"),
            (AgentRole.DESIGNER, "direct_developer_access"),
        ],
    }
    
    def __init__(self, default_duration_minutes: int = 30):
        self.default_duration_minutes = default_duration_minutes
        self._permissions: dict[str, TemporaryPermission] = {}
        self._grant_history: list[dict] = []
    
    def grant_permission(
        self,
        granted_to: AgentRole,
        target_role: AgentRole,
        permission_type: str,
        reason: str,
        duration_minutes: Optional[int] = None,
        task_id: Optional[str] = None,
        granted_by: AgentRole = AgentRole.CTO,
    ) -> Optional[TemporaryPermission]:
        """
        Grant a temporary permission.
        
        Only CTO can grant permissions (enforced by caller).
        """
        if not self._is_valid_permission(granted_to, target_role, permission_type):
            return None
        
        duration = duration_minutes or self.default_duration_minutes
        expires_at = datetime.utcnow() + timedelta(minutes=duration)
        
        permission = TemporaryPermission(
            granted_to=granted_to,
            granted_by=granted_by,
            permission_type=permission_type,
            target_role=target_role,
            reason=reason,
            expires_at=expires_at,
            task_id=task_id,
        )
        
        self._permissions[str(permission.id)] = permission
        
        self._grant_history.append({
            "permission_id": str(permission.id),
            "granted_to": granted_to.value,
            "target_role": target_role.value,
            "permission_type": permission_type,
            "reason": reason,
            "duration_minutes": duration,
            "task_id": task_id,
            "granted_at": datetime.utcnow().isoformat(),
        })
        
        return permission
    
    def revoke_permission(self, permission_id: str) -> bool:
        """Revoke a temporary permission by ID."""
        permission = self._permissions.get(permission_id)
        if permission:
            permission.revoke()
            return True
        return False
    
    def revoke_all_for_task(self, task_id: str) -> int:
        """Revoke all temporary permissions for a specific task."""
        count = 0
        for perm in self._permissions.values():
            if str(perm.task_id) == task_id and perm.is_active:
                perm.revoke()
                count += 1
        return count
    
    def get_permission(self, permission_id: str) -> Optional[TemporaryPermission]:
        """Get a specific permission by ID."""
        return self._permissions.get(permission_id)
    
    def get_active_permissions(
        self,
        agent_role: AgentRole,
    ) -> list[TemporaryPermission]:
        """Get all active permissions for an agent."""
        self._cleanup_expired()
        
        return [
            perm for perm in self._permissions.values()
            if perm.granted_to == agent_role and not perm.is_expired()
        ]
    
    def get_all_active(self) -> list[TemporaryPermission]:
        """Get all active temporary permissions."""
        self._cleanup_expired()
        
        return [
            perm for perm in self._permissions.values()
            if not perm.is_expired()
        ]
    
    def _is_valid_permission(
        self,
        granted_to: AgentRole,
        target_role: AgentRole,
        permission_type: str,
    ) -> bool:
        """Check if the permission combination is valid."""
        if isinstance(granted_to, str):
            granted_to = AgentRole(granted_to)
        if isinstance(target_role, str):
            target_role = AgentRole(target_role)
        
        valid_combinations = self.VALID_TEMP_PERMISSIONS.get(AgentRole.CTO, [])
        for combo in valid_combinations:
            combo_agent, combo_perm_type = combo
            if combo_agent == granted_to and combo_perm_type == permission_type:
                return True
        return False
    
    def _cleanup_expired(self) -> int:
        """Remove expired permissions from active list."""
        expired_ids = [
            pid for pid, perm in self._permissions.items()
            if perm.is_expired()
        ]
        
        for pid in expired_ids:
            del self._permissions[pid]
        
        return len(expired_ids)
    
    def get_grant_history(self, limit: int = 100) -> list[dict]:
        """Get the history of permission grants."""
        return self._grant_history[-limit:]
    
    def get_permission_stats(self) -> dict:
        """Get statistics about temporary permissions."""
        active = self.get_all_active()
        
        return {
            "total_grants": len(self._grant_history),
            "active_count": len(active),
            "by_agent": {
                role.value: len([p for p in active if p.granted_to == role])
                for role in AgentRole
            },
            "by_type": self._count_by_permission_type(active),
        }
    
    def _count_by_permission_type(
        self,
        permissions: list[TemporaryPermission],
    ) -> dict[str, int]:
        """Count permissions by type."""
        counts: dict[str, int] = {}
        for perm in permissions:
            counts[perm.permission_type] = counts.get(perm.permission_type, 0) + 1
        return counts
