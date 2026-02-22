"""
Tests for core types and models.
"""

import pytest
from datetime import datetime, timedelta

from multi_agent.core.types import (
    AgentRole,
    AgentMessage,
    TaskStatus,
    TaskPriority,
    PermissionLevel,
    MessageType,
    TaskContext,
    ProjectContext,
    TemporaryPermission,
    SystemAlert,
    AlertType,
)


class TestAgentRole:
    """Tests for AgentRole enum."""
    
    def test_all_roles_exist(self):
        """Test that all expected roles are defined."""
        expected_roles = [
            "ceo", "advisor", "cto", "developer",
            "qa_engineer", "designer", "documentation"
        ]
        actual_roles = [r.value for r in AgentRole]
        assert set(expected_roles) == set(actual_roles)
    
    def test_role_values(self):
        """Test role value access."""
        assert AgentRole.CEO.value == "ceo"
        assert AgentRole.ADVISOR.value == "advisor"
        assert AgentRole.CTO.value == "cto"


class TestAgentMessage:
    """Tests for AgentMessage model."""
    
    def test_message_creation(self):
        """Test creating an agent message."""
        message = AgentMessage(
            sender=AgentRole.CEO,
            receiver=AgentRole.CTO,
            message_type=MessageType.TASK_ASSIGNMENT,
            content="Please implement user authentication",
        )
        
        assert message.sender == AgentRole.CEO
        assert message.receiver == AgentRole.CTO
        assert message.message_type == MessageType.TASK_ASSIGNMENT
        assert message.id is not None
        assert message.timestamp is not None
    
    def test_message_with_task_id(self):
        """Test message with task reference."""
        from uuid import uuid4
        task_id = uuid4()
        
        message = AgentMessage(
            sender=AgentRole.CTO,
            receiver=AgentRole.DEVELOPER,
            message_type=MessageType.TASK_ASSIGNMENT,
            content="Implement login feature",
            task_id=task_id,
        )
        
        assert message.task_id == task_id


class TestTaskContext:
    """Tests for TaskContext model."""
    
    def test_task_creation(self):
        """Test creating a task context."""
        task = TaskContext(
            title="Implement Authentication",
            description="Add user login and registration",
            created_by=AgentRole.CEO,
        )
        
        assert task.title == "Implement Authentication"
        assert task.status == TaskStatus.PENDING
        assert task.priority == TaskPriority.MEDIUM
        assert task.iteration_count == 0
    
    def test_iteration_increment(self):
        """Test iteration count increment."""
        task = TaskContext(
            title="Test Task",
            description="Test description",
            created_by=AgentRole.CTO,
        )
        
        result = task.increment_iteration()
        assert task.iteration_count == 1
        assert result is True
        
        task.iteration_count = 2
        result = task.increment_iteration()
        assert task.iteration_count == 3
        assert result is False
    
    def test_loop_detection(self):
        """Test loop detection logic."""
        task = TaskContext(
            title="Test Task",
            description="Test description",
            created_by=AgentRole.CTO,
            max_iterations=3,
        )
        
        assert not task.is_loop_detected()
        
        task.iteration_count = 3
        assert task.is_loop_detected()


class TestTemporaryPermission:
    """Tests for TemporaryPermission model."""
    
    def test_permission_creation(self):
        """Test creating a temporary permission."""
        expires = datetime.utcnow() + timedelta(minutes=30)
        
        permission = TemporaryPermission(
            granted_to=AgentRole.CTO,
            granted_by=AgentRole.CEO,
            permission_type="direct_qa_access",
            target_role=AgentRole.QA_ENGINEER,
            reason="Emergency bug fix",
            expires_at=expires,
        )
        
        assert permission.granted_to == AgentRole.CTO
        assert permission.is_active is True
        assert not permission.is_expired()
    
    def test_permission_expiration(self):
        """Test permission expiration check."""
        expired_permission = TemporaryPermission(
            granted_to=AgentRole.CTO,
            granted_by=AgentRole.CEO,
            permission_type="test",
            target_role=AgentRole.DEVELOPER,
            reason="Test",
            expires_at=datetime.utcnow() - timedelta(minutes=1),
        )
        
        assert expired_permission.is_expired()
    
    def test_permission_revocation(self):
        """Test permission revocation."""
        permission = TemporaryPermission(
            granted_to=AgentRole.CTO,
            granted_by=AgentRole.CEO,
            permission_type="test",
            target_role=AgentRole.DEVELOPER,
            reason="Test",
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        
        permission.revoke()
        assert permission.is_expired()
        assert not permission.is_active


class TestSystemAlert:
    """Tests for SystemAlert model."""
    
    def test_alert_creation(self):
        """Test creating a system alert."""
        alert = SystemAlert(
            alert_type=AlertType.LOOP_DETECTED,
            severity=TaskPriority.HIGH,
            source_agent=AgentRole.CTO,
            message="Task loop detected",
        )
        
        assert alert.alert_type == AlertType.LOOP_DETECTED
        assert alert.severity == TaskPriority.HIGH
        assert not alert.resolved
    
    def test_alert_resolution(self):
        """Test alert resolution."""
        alert = SystemAlert(
            alert_type=AlertType.PERMISSION_VIOLATION,
            severity=TaskPriority.HIGH,
            source_agent=AgentRole.DEVELOPER,
            message="Unauthorized access attempt",
        )
        
        alert.resolved = True
        alert.resolved_at = datetime.utcnow()
        alert.resolution = "Access denied and logged"
        
        assert alert.resolved
        assert alert.resolution is not None
