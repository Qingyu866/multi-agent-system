"""
Tests for monitoring systems.
"""

import pytest

from multi_agent.core.types import AgentRole, ProjectContext, AlertType, TaskPriority
from multi_agent.monitoring.loop_detector import LoopDetector
from multi_agent.monitoring.scope_monitor import ScopeMonitor
from multi_agent.monitoring.alert_manager import AlertManager


class TestLoopDetector:
    """Tests for LoopDetector."""
    
    @pytest.fixture
    def detector(self) -> LoopDetector:
        """Create a loop detector instance."""
        return LoopDetector(max_iterations=3)
    
    def test_no_loop_initially(self, detector: LoopDetector):
        """Test that no loop is detected initially."""
        assert not detector.check_and_record(
            task_id="task-1",
            from_agent=AgentRole.CTO,
            to_agent=AgentRole.DEVELOPER,
        )
    
    def test_loop_after_max_iterations(self, detector: LoopDetector):
        """Test loop detection after maximum iterations."""
        task_id = "task-loop"
        
        for i in range(3):
            detector.check_and_record(
                task_id=task_id,
                from_agent=AgentRole.CTO,
                to_agent=AgentRole.DEVELOPER,
            )
        
        loop_detected = detector.check_and_record(
            task_id=task_id,
            from_agent=AgentRole.CTO,
            to_agent=AgentRole.DEVELOPER,
        )
        
        assert loop_detected
    
    def test_different_flows_no_loop(self, detector: LoopDetector):
        """Test that different flows don't trigger loop."""
        task_id = "task-different"
        
        detector.check_and_record(task_id, AgentRole.CTO, AgentRole.DEVELOPER)
        detector.check_and_record(task_id, AgentRole.CTO, AgentRole.QA_ENGINEER)
        detector.check_and_record(task_id, AgentRole.CTO, AgentRole.DESIGNER)
        
        assert not detector.check_and_record(
            task_id, AgentRole.CTO, AgentRole.DEVELOPER
        )
    
    def test_get_loop_status(self, detector: LoopDetector):
        """Test getting loop status."""
        task_id = "task-status"
        
        for _ in range(4):
            detector.check_and_record(
                task_id=task_id,
                from_agent=AgentRole.CTO,
                to_agent=AgentRole.DEVELOPER,
            )
        
        status = detector.get_loop_status(task_id)
        
        assert status is not None
        assert status["task_id"] == task_id
    
    def test_clear_task_history(self, detector: LoopDetector):
        """Test clearing task history."""
        task_id = "task-clear"
        
        detector.check_and_record(task_id, AgentRole.CTO, AgentRole.DEVELOPER)
        detector.clear_task_history(task_id)
        
        status = detector.get_loop_status(task_id)
        assert status is None
    
    def test_iteration_count(self, detector: LoopDetector):
        """Test getting iteration count."""
        task_id = "task-count"
        
        detector.check_and_record(task_id, AgentRole.CTO, AgentRole.DEVELOPER)
        detector.check_and_record(task_id, AgentRole.CTO, AgentRole.DEVELOPER)
        
        count = detector.get_iteration_count(
            task_id, AgentRole.CTO, AgentRole.DEVELOPER
        )
        
        assert count == 2


class TestScopeMonitor:
    """Tests for ScopeMonitor."""
    
    @pytest.fixture
    def project_context(self) -> ProjectContext:
        """Create a test project context."""
        return ProjectContext(
            name="Test Project",
            description="Test project for scope monitoring",
            requirements=["User login", "Task management"],
            scope_boundaries=["No social features", "No payment integration"],
        )
    
    @pytest.fixture
    def monitor(self, project_context: ProjectContext) -> ScopeMonitor:
        """Create a scope monitor instance."""
        return ScopeMonitor(project_context=project_context)
    
    def test_no_drift_in_normal_content(self, monitor: ScopeMonitor):
        """Test that normal content doesn't trigger drift."""
        is_drift, indicator = monitor.check_content(
            content="Implementing user login functionality with secure authentication",
            task_id="task-1",
            agent_role=AgentRole.DEVELOPER,
        )
        
        assert not is_drift
        assert indicator is None
    
    def test_feature_creep_detection(self, monitor: ScopeMonitor):
        """Test detection of feature creep."""
        is_drift, indicator = monitor.check_content(
            content="While we're at it, let's also add social login features",
            task_id="task-2",
            agent_role=AgentRole.DEVELOPER,
        )
        
        assert is_drift
        assert indicator is not None
        assert indicator.severity in ["medium", "high"]
    
    def test_scope_expansion_detection(self, monitor: ScopeMonitor):
        """Test detection of scope expansion."""
        is_drift, indicator = monitor.check_content(
            content="We should expand the scope to include payment processing",
            task_id="task-3",
            agent_role=AgentRole.CTO,
        )
        
        assert is_drift
        assert indicator is not None
    
    def test_drift_history(self, monitor: ScopeMonitor):
        """Test drift history tracking."""
        monitor.check_content(
            content="It would be nice to add extra features",
            task_id="task-4",
            agent_role=AgentRole.DEVELOPER,
        )
        
        history = monitor.get_drift_history()
        
        assert len(history) == 1
    
    def test_get_original_scope(self, monitor: ScopeMonitor):
        """Test getting original scope."""
        scope = monitor.get_original_scope()
        
        assert "No social features" in scope
        assert "No payment integration" in scope
    
    def test_check_relevance(self, monitor: ScopeMonitor):
        """Test content relevance checking."""
        relevance = monitor.check_relevance(
            content="Implementing user login with authentication"
        )
        
        assert relevance > 0


class TestAlertManager:
    """Tests for AlertManager."""
    
    @pytest.fixture
    def alert_manager(self) -> AlertManager:
        """Create an alert manager instance."""
        return AlertManager()
    
    @pytest.mark.asyncio
    async def test_create_alert(self, alert_manager: AlertManager):
        """Test creating an alert."""
        alert = await alert_manager.create_alert(
            alert_type=AlertType.LOOP_DETECTED,
            severity=TaskPriority.HIGH,
            source_agent=AgentRole.CTO,
            message="Task loop detected",
        )
        
        assert alert.alert_type == AlertType.LOOP_DETECTED
        assert alert.severity == TaskPriority.HIGH
        assert not alert.resolved
    
    @pytest.mark.asyncio
    async def test_create_loop_alert(self, alert_manager: AlertManager):
        """Test creating a loop alert."""
        alert = await alert_manager.create_loop_alert(
            task_id="task-loop",
            source_agent=AgentRole.CTO,
            pattern="CTO->Developer->QA->CTO",
        )
        
        assert alert.alert_type == AlertType.LOOP_DETECTED
        assert "task-loop" in alert.message
    
    @pytest.mark.asyncio
    async def test_create_permission_violation_alert(self, alert_manager: AlertManager):
        """Test creating a permission violation alert."""
        alert = await alert_manager.create_permission_violation_alert(
            source_agent=AgentRole.DEVELOPER,
            target_agent=AgentRole.QA_ENGINEER,
            reason="Direct communication not allowed",
        )
        
        assert alert.alert_type == AlertType.PERMISSION_VIOLATION
        assert alert.source_agent == AgentRole.DEVELOPER
        assert alert.target_agent == AgentRole.QA_ENGINEER
    
    @pytest.mark.asyncio
    async def test_resolve_alert(self, alert_manager: AlertManager):
        """Test resolving an alert."""
        alert = await alert_manager.create_alert(
            alert_type=AlertType.TASK_BLOCKED,
            severity=TaskPriority.HIGH,
            source_agent=AgentRole.DEVELOPER,
            message="Task blocked by dependency",
        )
        
        success = alert_manager.resolve_alert(
            str(alert.id),
            "Dependency resolved"
        )
        
        assert success
        assert alert.resolved
        assert alert.resolution == "Dependency resolved"
    
    @pytest.mark.asyncio
    async def test_get_active_alerts(self, alert_manager: AlertManager):
        """Test getting active alerts."""
        await alert_manager.create_alert(
            alert_type=AlertType.LOOP_DETECTED,
            severity=TaskPriority.HIGH,
            source_agent=AgentRole.CTO,
            message="Alert 1",
        )
        
        await alert_manager.create_alert(
            alert_type=AlertType.SCOPE_DRIFT,
            severity=TaskPriority.MEDIUM,
            source_agent=AgentRole.DEVELOPER,
            message="Alert 2",
        )
        
        active = alert_manager.get_active_alerts()
        
        assert len(active) == 2
    
    @pytest.mark.asyncio
    async def test_get_alerts_summary(self, alert_manager: AlertManager):
        """Test getting alerts summary."""
        await alert_manager.create_alert(
            alert_type=AlertType.LOOP_DETECTED,
            severity=TaskPriority.HIGH,
            source_agent=AgentRole.CTO,
            message="Test",
        )
        
        summary = alert_manager.get_active_alerts_summary()
        
        assert summary["total_active"] == 1
        assert "loop_detected" in summary["by_type"]
        assert "high" in summary["by_severity"]
    
    @pytest.mark.asyncio
    async def test_get_critical_alerts(self, alert_manager: AlertManager):
        """Test getting critical alerts."""
        await alert_manager.create_alert(
            alert_type=AlertType.EMERGENCY_ESCALATION,
            severity=TaskPriority.CRITICAL,
            source_agent=AgentRole.CTO,
            message="Critical issue",
        )
        
        await alert_manager.create_alert(
            alert_type=AlertType.LOOP_DETECTED,
            severity=TaskPriority.HIGH,
            source_agent=AgentRole.CTO,
            message="Non-critical issue",
        )
        
        critical = alert_manager.get_critical_alerts()
        
        assert len(critical) == 1
        assert critical[0].severity == TaskPriority.CRITICAL
