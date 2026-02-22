"""
Tests for permission guard and temporary authorization.
"""

import pytest

from multi_agent.core.types import AgentRole, TemporaryPermission
from multi_agent.permissions.guard import PermissionGuard
from multi_agent.permissions.temp_auth import TemporaryAuthManager


class TestPermissionGuard:
    """Tests for PermissionGuard."""
    
    @pytest.fixture
    def guard(self) -> PermissionGuard:
        """Create a permission guard instance."""
        return PermissionGuard()
    
    def test_ceo_allowed_targets(self, guard: PermissionGuard):
        """Test CEO's allowed communication targets."""
        targets = guard.get_allowed_targets(AgentRole.CEO)
        
        assert AgentRole.CTO in targets
        assert AgentRole.ADVISOR in targets
        assert AgentRole.DOCUMENTATION in targets
        assert AgentRole.DEVELOPER not in targets
    
    def test_cto_allowed_targets(self, guard: PermissionGuard):
        """Test CTO's allowed communication targets."""
        targets = guard.get_allowed_targets(AgentRole.CTO)
        
        assert AgentRole.DEVELOPER in targets
        assert AgentRole.QA_ENGINEER in targets
        assert AgentRole.DESIGNER in targets
        assert AgentRole.CEO not in targets
    
    def test_developer_limited_targets(self, guard: PermissionGuard):
        """Test Developer's limited communication targets."""
        targets = guard.get_allowed_targets(AgentRole.DEVELOPER)
        
        assert AgentRole.DOCUMENTATION in targets
        assert AgentRole.QA_ENGINEER not in targets
        assert AgentRole.DESIGNER not in targets
        assert AgentRole.CTO not in targets
    
    def test_valid_communication(self, guard: PermissionGuard):
        """Test valid communication between agents."""
        result = guard.validate_communication(
            sender=AgentRole.CEO,
            receiver=AgentRole.CTO,
        )
        
        assert result.allowed is True
        assert result.reason is None
    
    def test_invalid_communication(self, guard: PermissionGuard):
        """Test invalid communication between agents."""
        result = guard.validate_communication(
            sender=AgentRole.DEVELOPER,
            receiver=AgentRole.QA_ENGINEER,
        )
        
        assert result.allowed is False
        assert result.reason is not None
    
    def test_advisor_passive_role(self, guard: PermissionGuard):
        """Test that Advisor cannot initiate communication."""
        targets = guard.get_allowed_targets(AgentRole.ADVISOR)
        assert len(targets) == 0
    
    def test_ceo_can_summon_advisor(self, guard: PermissionGuard):
        """Test that CEO can summon Advisor."""
        result = guard.validate_communication(
            sender=AgentRole.CEO,
            receiver=AgentRole.ADVISOR,
        )
        
        assert result.allowed is True
    
    def test_forbidden_actions_developer(self, guard: PermissionGuard):
        """Test forbidden actions for Developer."""
        forbidden = guard.get_forbidden_actions(AgentRole.DEVELOPER)
        
        assert "contact_qa_directly" in forbidden
        assert "contact_designer_directly" in forbidden
        assert "modify_requirements" in forbidden
    
    def test_forbidden_actions_qa(self, guard: PermissionGuard):
        """Test forbidden actions for QA Engineer."""
        forbidden = guard.get_forbidden_actions(AgentRole.QA_ENGINEER)
        
        assert "demand_code_changes" in forbidden
        assert "contact_developer_directly" in forbidden
    
    def test_violation_logging(self, guard: PermissionGuard):
        """Test that violations are logged."""
        guard.validate_communication(
            sender=AgentRole.DEVELOPER,
            receiver=AgentRole.QA_ENGINEER,
        )
        
        violations = guard.get_violation_log()
        assert len(violations) == 1
        assert violations[0]["agent"] == "developer"
        assert violations[0]["target"] == "qa_engineer"


class TestTemporaryAuthManager:
    """Tests for TemporaryAuthManager."""
    
    @pytest.fixture
    def auth_manager(self) -> TemporaryAuthManager:
        """Create a temporary auth manager instance."""
        return TemporaryAuthManager(default_duration_minutes=30)
    
    def test_grant_permission(self, auth_manager: TemporaryAuthManager):
        """Test granting temporary permission."""
        permission = auth_manager.grant_permission(
            granted_to=AgentRole.DEVELOPER,
            target_role=AgentRole.QA_ENGINEER,
            permission_type="direct_qa_access",
            reason="Emergency bug fix testing",
        )
        
        assert permission is not None
        assert permission.granted_to == AgentRole.DEVELOPER
        assert permission.target_role == AgentRole.QA_ENGINEER
    
    def test_get_active_permissions(self, auth_manager: TemporaryAuthManager):
        """Test retrieving active permissions."""
        auth_manager.grant_permission(
            granted_to=AgentRole.DEVELOPER,
            target_role=AgentRole.QA_ENGINEER,
            permission_type="direct_qa_access",
            reason="Test",
        )
        
        active = auth_manager.get_active_permissions(AgentRole.DEVELOPER)
        
        assert len(active) == 1
        assert active[0].permission_type == "direct_qa_access"
    
    def test_revoke_permission(self, auth_manager: TemporaryAuthManager):
        """Test revoking a permission."""
        permission = auth_manager.grant_permission(
            granted_to=AgentRole.DEVELOPER,
            target_role=AgentRole.QA_ENGINEER,
            permission_type="direct_qa_access",
            reason="Test",
        )
        
        success = auth_manager.revoke_permission(str(permission.id))
        
        assert success is True
        assert permission.is_active is False
    
    def test_revoke_all_for_task(self, auth_manager: TemporaryAuthManager):
        """Test revoking all permissions for a task."""
        task_id = "test-task-123"
        
        auth_manager.grant_permission(
            granted_to=AgentRole.DEVELOPER,
            target_role=AgentRole.QA_ENGINEER,
            permission_type="direct_qa_access",
            reason="Test",
            task_id=task_id,
        )
        
        auth_manager.grant_permission(
            granted_to=AgentRole.DESIGNER,
            target_role=AgentRole.DEVELOPER,
            permission_type="direct_developer_access",
            reason="Test",
            task_id=task_id,
        )
        
        count = auth_manager.revoke_all_for_task(task_id)
        
        assert count == 2
    
    def test_grant_history(self, auth_manager: TemporaryAuthManager):
        """Test grant history tracking."""
        auth_manager.grant_permission(
            granted_to=AgentRole.DEVELOPER,
            target_role=AgentRole.QA_ENGINEER,
            permission_type="direct_qa_access",
            reason="Test 1",
        )
        
        auth_manager.grant_permission(
            granted_to=AgentRole.DESIGNER,
            target_role=AgentRole.DEVELOPER,
            permission_type="direct_developer_access",
            reason="Test 2",
        )
        
        history = auth_manager.get_grant_history()
        
        assert len(history) == 2
    
    def test_permission_stats(self, auth_manager: TemporaryAuthManager):
        """Test permission statistics."""
        auth_manager.grant_permission(
            granted_to=AgentRole.DEVELOPER,
            target_role=AgentRole.QA_ENGINEER,
            permission_type="direct_qa_access",
            reason="Test",
        )
        
        stats = auth_manager.get_permission_stats()
        
        assert stats["total_grants"] == 1
        assert stats["active_count"] == 1


class TestPermissionWithTempAuth:
    """Tests for permission guard with temporary authorization."""
    
    def test_temp_permission_allows_communication(self):
        """Test that temporary permission allows otherwise forbidden communication."""
        guard = PermissionGuard()
        auth_manager = TemporaryAuthManager()
        
        permission = auth_manager.grant_permission(
            granted_to=AgentRole.DEVELOPER,
            target_role=AgentRole.QA_ENGINEER,
            permission_type="direct_qa_access",
            reason="Emergency testing",
        )
        
        temp_perms = auth_manager.get_active_permissions(AgentRole.DEVELOPER)
        
        result = guard.validate_communication(
            sender=AgentRole.DEVELOPER,
            receiver=AgentRole.QA_ENGINEER,
            temp_permissions=temp_perms,
        )
        
        assert result.allowed is True
