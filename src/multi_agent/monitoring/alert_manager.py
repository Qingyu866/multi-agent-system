"""
Alert management system for the multi-agent system.
"""

from datetime import datetime
from typing import Optional

from multi_agent.core.types import (
    AgentRole,
    AlertType,
    SystemAlert,
    TaskPriority,
)


class AlertManager:
    """
    Manages system alerts for various events and conditions.
    
    Alert types:
    - Loop detected: Task circulation patterns
    - Scope drift: Project scope deviation
    - Permission violation: Unauthorized access attempts
    - Task blocked: Tasks unable to proceed
    - Emergency escalation: Critical issues requiring attention
    - Temp permission expired: Temporary authorizations ended
    """
    
    def __init__(self, max_active_alerts: int = 100):
        self.max_active_alerts = max_active_alerts
        self._alerts: dict[str, SystemAlert] = {}
        self._alert_history: list[dict] = []
    
    async def create_alert(
        self,
        alert_type: AlertType,
        severity: TaskPriority,
        source_agent: AgentRole,
        message: str,
        target_agent: Optional[AgentRole] = None,
        task_id: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> SystemAlert:
        """Create a new system alert."""
        alert = SystemAlert(
            alert_type=alert_type,
            severity=severity,
            source_agent=source_agent,
            target_agent=target_agent,
            task_id=task_id,
            message=message,
            context=context or {},
        )
        
        self._alerts[str(alert.id)] = alert
        
        self._alert_history.append({
            "alert_id": str(alert.id),
            "alert_type": alert_type.value,
            "severity": severity.value,
            "source_agent": source_agent.value,
            "target_agent": target_agent.value if target_agent else None,
            "task_id": task_id,
            "message": message,
            "created_at": datetime.utcnow().isoformat(),
        })
        
        if len(self._alerts) > self.max_active_alerts:
            self._prune_resolved_alerts()
        
        return alert
    
    async def create_loop_alert(
        self,
        task_id: str,
        source_agent: AgentRole,
        pattern: Optional[str] = None,
    ) -> SystemAlert:
        """Create a loop detection alert."""
        message = f"Task {task_id} has entered a loop pattern"
        if pattern:
            message += f": {pattern}"
        
        return await self.create_alert(
            alert_type=AlertType.LOOP_DETECTED,
            severity=TaskPriority.HIGH,
            source_agent=source_agent,
            message=message,
            task_id=task_id,
            context={"pattern": pattern} if pattern else {},
        )
    
    async def create_scope_drift_alert(
        self,
        task_id: str,
        source_agent: AgentRole,
        drift_type: str,
        original_scope: str,
        detected_content: str,
    ) -> SystemAlert:
        """Create a scope drift alert."""
        return await self.create_alert(
            alert_type=AlertType.SCOPE_DRIFT,
            severity=TaskPriority.MEDIUM,
            source_agent=source_agent,
            message=f"Scope drift detected: {drift_type}",
            task_id=task_id,
            context={
                "drift_type": drift_type,
                "original_scope": original_scope,
                "detected_content": detected_content[:200],
            },
        )
    
    async def create_permission_violation_alert(
        self,
        source_agent: AgentRole,
        target_agent: AgentRole,
        reason: str,
    ) -> SystemAlert:
        """Create a permission violation alert."""
        return await self.create_alert(
            alert_type=AlertType.PERMISSION_VIOLATION,
            severity=TaskPriority.HIGH,
            source_agent=source_agent,
            target_agent=target_agent,
            message=f"Permission violation: {reason}",
            context={"reason": reason},
        )
    
    async def create_task_blocked_alert(
        self,
        task_id: str,
        source_agent: AgentRole,
        blocker: str,
    ) -> SystemAlert:
        """Create a task blocked alert."""
        return await self.create_alert(
            alert_type=AlertType.TASK_BLOCKED,
            severity=TaskPriority.HIGH,
            source_agent=source_agent,
            message=f"Task blocked: {blocker}",
            task_id=task_id,
            context={"blocker": blocker},
        )
    
    async def create_emergency_escalation_alert(
        self,
        task_id: str,
        source_agent: AgentRole,
        reason: str,
    ) -> SystemAlert:
        """Create an emergency escalation alert."""
        return await self.create_alert(
            alert_type=AlertType.EMERGENCY_ESCALATION,
            severity=TaskPriority.CRITICAL,
            source_agent=source_agent,
            message=f"Emergency escalation: {reason}",
            task_id=task_id,
            context={"reason": reason},
        )
    
    async def create_temp_permission_expired_alert(
        self,
        permission_id: str,
        agent: AgentRole,
        permission_type: str,
    ) -> SystemAlert:
        """Create a temporary permission expired alert."""
        return await self.create_alert(
            alert_type=AlertType.TEMP_PERMISSION_EXPIRED,
            severity=TaskPriority.LOW,
            source_agent=agent,
            message=f"Temporary permission expired: {permission_type}",
            context={
                "permission_id": permission_id,
                "permission_type": permission_type,
            },
        )
    
    def resolve_alert(self, alert_id: str, resolution: str) -> bool:
        """Resolve an alert with a resolution message."""
        alert = self._alerts.get(alert_id)
        if alert:
            alert.resolved = True
            alert.resolved_at = datetime.utcnow()
            alert.resolution = resolution
            return True
        return False
    
    def get_alert(self, alert_id: str) -> Optional[SystemAlert]:
        """Get a specific alert by ID."""
        return self._alerts.get(alert_id)
    
    def get_active_alerts(self) -> list[SystemAlert]:
        """Get all active (unresolved) alerts."""
        return [
            alert for alert in self._alerts.values()
            if not alert.resolved
        ]
    
    def get_alerts_by_type(self, alert_type: AlertType) -> list[SystemAlert]:
        """Get alerts filtered by type."""
        return [
            alert for alert in self._alerts.values()
            if alert.alert_type == alert_type
        ]
    
    def get_alerts_by_task(self, task_id: str) -> list[SystemAlert]:
        """Get alerts for a specific task."""
        return [
            alert for alert in self._alerts.values()
            if str(alert.task_id) == task_id
        ]
    
    def get_active_alerts_summary(self) -> dict:
        """Get a summary of active alerts."""
        active = self.get_active_alerts()
        
        by_type: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        
        for alert in active:
            type_val = alert.alert_type.value if hasattr(alert.alert_type, 'value') else alert.alert_type
            type_key = str(type_val)
            by_type[type_key] = by_type.get(type_key, 0) + 1
            
            severity_val = alert.severity.value if hasattr(alert.severity, 'value') else alert.severity
            severity_key = str(severity_val)
            by_severity[severity_key] = by_severity.get(severity_key, 0) + 1
        
        return {
            "total_active": len(active),
            "by_type": by_type,
            "by_severity": by_severity,
        }
    
    def get_critical_alerts(self) -> list[SystemAlert]:
        """Get all critical severity alerts."""
        return [
            alert for alert in self._alerts.values()
            if alert.severity == TaskPriority.CRITICAL and not alert.resolved
        ]
    
    def _prune_resolved_alerts(self) -> None:
        """Remove old resolved alerts to make room."""
        resolved_ids = [
            aid for aid, alert in self._alerts.items()
            if alert.resolved
        ]
        
        for aid in resolved_ids[:len(resolved_ids) // 2]:
            del self._alerts[aid]
    
    def get_alert_history(self, limit: int = 100) -> list[dict]:
        """Get the alert history."""
        return self._alert_history[-limit:]
    
    def clear_resolved_alerts(self) -> int:
        """Clear all resolved alerts."""
        resolved_ids = [
            aid for aid, alert in self._alerts.items()
            if alert.resolved
        ]
        
        for aid in resolved_ids:
            del self._alerts[aid]
        
        return len(resolved_ids)
