"""
Permission guard for controlling inter-agent communication.
Implements the whitelist-based permission matrix.
"""

from dataclasses import dataclass
from typing import Optional

from multi_agent.core.types import AgentRole, PermissionLevel, TemporaryPermission


@dataclass
class PermissionResult:
    """Result of a permission check."""
    
    allowed: bool
    reason: Optional[str] = None


class PermissionGuard:
    """
    Controls inter-agent communication based on permission whitelist.
    
    Implements the hierarchical permission matrix:
    - CEO: Can call CTO, Advisor, Documentation
    - Advisor: Passive role, only responds to summons
    - CTO: Can call Developer, QA Engineer, Designer
    - Developer: Can only use development tools
    - QA Engineer: Can only use testing tools
    - Designer: Can only use design tools
    - Documentation: Can be called by all agents
    
    Enforces strict isolation to prevent:
    - Cross-level unauthorized communication
    - Bypassing the chain of command
    - Direct manipulation between execution agents
    """
    
    PERMISSION_WHITELIST: dict[AgentRole, list[AgentRole]] = {
        AgentRole.CEO: [
            AgentRole.CTO,
            AgentRole.ADVISOR,
            AgentRole.DOCUMENTATION,
        ],
        AgentRole.ADVISOR: [],
        AgentRole.CTO: [
            AgentRole.DEVELOPER,
            AgentRole.FRONTEND_DEVELOPER,
            AgentRole.BACKEND_DEVELOPER,
            AgentRole.FULLSTACK_DEVELOPER,
            AgentRole.MOBILE_DEVELOPER,
            AgentRole.DEVOPS_ENGINEER,
            AgentRole.DATABASE_DEVELOPER,
            AgentRole.QA_ENGINEER,
            AgentRole.UI_UX_DESIGNER,
            AgentRole.DOCUMENTATION,
        ],
        AgentRole.DEVELOPER: [
            AgentRole.DOCUMENTATION,
        ],
        AgentRole.FRONTEND_DEVELOPER: [
            AgentRole.BACKEND_DEVELOPER,
            AgentRole.UI_UX_DESIGNER,
            AgentRole.DOCUMENTATION,
        ],
        AgentRole.BACKEND_DEVELOPER: [
            AgentRole.FRONTEND_DEVELOPER,
            AgentRole.DATABASE_DEVELOPER,
            AgentRole.DOCUMENTATION,
        ],
        AgentRole.FULLSTACK_DEVELOPER: [
            AgentRole.FRONTEND_DEVELOPER,
            AgentRole.BACKEND_DEVELOPER,
            AgentRole.DATABASE_DEVELOPER,
            AgentRole.DOCUMENTATION,
        ],
        AgentRole.MOBILE_DEVELOPER: [
            AgentRole.BACKEND_DEVELOPER,
            AgentRole.UI_UX_DESIGNER,
            AgentRole.DEVOPS_ENGINEER,
            AgentRole.DOCUMENTATION,
        ],
        AgentRole.DEVOPS_ENGINEER: [
            AgentRole.BACKEND_DEVELOPER,
            AgentRole.DATABASE_DEVELOPER,
            AgentRole.DOCUMENTATION,
        ],
        AgentRole.DATABASE_DEVELOPER: [
            AgentRole.BACKEND_DEVELOPER,
            AgentRole.DEVOPS_ENGINEER,
            AgentRole.DOCUMENTATION,
        ],
        AgentRole.QA_ENGINEER: [
            AgentRole.DOCUMENTATION,
        ],
        AgentRole.UI_UX_DESIGNER: [
            AgentRole.FRONTEND_DEVELOPER,
            AgentRole.MOBILE_DEVELOPER,
            AgentRole.DOCUMENTATION,
        ],
        AgentRole.DOCUMENTATION: [],
    }
    
    FORBIDDEN_ACTIONS: dict[AgentRole, list[str]] = {
        AgentRole.CEO: [
            "direct_developer_task",
            "direct_qa_task",
            "direct_designer_task",
        ],
        AgentRole.ADVISOR: [
            "initiate_communication",
            "direct_any_agent",
            "modify_project_scope",
        ],
        AgentRole.CTO: [
            "report_to_ceo_routine",
            "bypass_ceo_decision",
        ],
        AgentRole.DEVELOPER: [
            "contact_qa_directly",
            "contact_designer_directly",
            "modify_requirements",
        ],
        AgentRole.FRONTEND_DEVELOPER: [
            "modify_backend_logic",
            "modify_database",
            "modify_deployment_config",
        ],
        AgentRole.BACKEND_DEVELOPER: [
            "modify_frontend_code",
            "modify_deployment_config",
        ],
        AgentRole.FULLSTACK_DEVELOPER: [
            "modify_production_config",
        ],
        AgentRole.MOBILE_DEVELOPER: [
            "modify_backend_logic",
            "modify_deployment_config",
        ],
        AgentRole.DEVOPS_ENGINEER: [
            "modify_business_logic",
            "modify_database_schema",
        ],
        AgentRole.DATABASE_DEVELOPER: [
            "modify_business_logic",
            "modify_api_definition",
        ],
        AgentRole.QA_ENGINEER: [
            "demand_code_changes",
            "contact_developer_directly",
            "modify_requirements",
        ],
        AgentRole.UI_UX_DESIGNER: [
            "modify_requirements",
            "contact_developer_directly",
            "implement_code",
        ],
        AgentRole.DOCUMENTATION: [
            "modify_code",
            "make_decisions",
            "assign_tasks",
        ],
    }
    
    def __init__(self):
        self._violation_log: list[dict] = []
    
    def validate_communication(
        self,
        sender: AgentRole,
        receiver: AgentRole,
        temp_permissions: Optional[list[TemporaryPermission]] = None,
    ) -> PermissionResult:
        """
        Validate if sender can communicate with receiver.
        
        Checks:
        1. Standard whitelist permissions
        2. Temporary permissions for emergency situations
        3. Special advisor summons rules
        """
        if isinstance(sender, str):
            sender = AgentRole(sender)
        if isinstance(receiver, str):
            receiver = AgentRole(receiver)
        
        if sender == receiver:
            return PermissionResult(allowed=True)
        
        if receiver in self.PERMISSION_WHITELIST.get(sender, []):
            return PermissionResult(allowed=True)
        
        if temp_permissions:
            for perm in temp_permissions:
                if perm.is_expired():
                    continue
                target = perm.target_role
                if isinstance(target, str):
                    target = AgentRole(target)
                if target == receiver and perm.is_active:
                    return PermissionResult(allowed=True)
        
        if receiver == AgentRole.ADVISOR:
            if sender in [AgentRole.CEO, AgentRole.CTO]:
                return PermissionResult(allowed=True)
        
        sender_val = sender.value if isinstance(sender, AgentRole) else sender
        receiver_val = receiver.value if isinstance(receiver, AgentRole) else receiver
        reason = (
            f"Permission denied: {sender_val} cannot communicate with {receiver_val}. "
            f"Allowed targets for {sender_val}: {[r.value for r in self.PERMISSION_WHITELIST.get(sender, [])]}"
        )
        
        self._log_violation(sender, receiver, "communication", reason)
        
        return PermissionResult(allowed=False, reason=reason)
    
    def validate_action(
        self,
        agent: AgentRole,
        action: str,
        temp_permissions: Optional[list[TemporaryPermission]] = None,
    ) -> PermissionResult:
        """
        Validate if an agent can perform a specific action.
        
        Checks against forbidden actions list.
        """
        forbidden = self.FORBIDDEN_ACTIONS.get(agent, [])
        
        if action in forbidden:
            if temp_permissions:
                for perm in temp_permissions:
                    if not perm.is_expired() and perm.permission_type == action:
                        return PermissionResult(allowed=True)
            
            reason = (
                f"Action '{action}' is forbidden for agent '{agent.value}'"
            )
            self._log_violation(agent, None, action, reason)
            return PermissionResult(allowed=False, reason=reason)
        
        return PermissionResult(allowed=True)
    
    def get_allowed_targets(self, agent: AgentRole) -> list[AgentRole]:
        """Get list of agents that the given agent can communicate with."""
        return self.PERMISSION_WHITELIST.get(agent, []).copy()
    
    def get_forbidden_actions(self, agent: AgentRole) -> list[str]:
        """Get list of actions forbidden for the given agent."""
        return self.FORBIDDEN_ACTIONS.get(agent, []).copy()
    
    def _log_violation(
        self,
        agent: AgentRole,
        target: Optional[AgentRole],
        action: str,
        reason: str,
    ) -> None:
        """Log a permission violation for auditing."""
        from datetime import datetime
        
        self._violation_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "agent": agent.value,
            "target": target.value if target else None,
            "action": action,
            "reason": reason,
        })
    
    def get_violation_log(self, limit: int = 100) -> list[dict]:
        """Get recent permission violations."""
        return self._violation_log[-limit:]
    
    def clear_violation_log(self) -> None:
        """Clear the violation log."""
        self._violation_log = []
    
    def get_permission_matrix(self) -> dict[str, list[str]]:
        """Get the full permission matrix as a readable format."""
        return {
            agent.value: [r.value for r in targets]
            for agent, targets in self.PERMISSION_WHITELIST.items()
        }
