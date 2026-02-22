"""
Tests for the main multi-agent system.
"""

import pytest

from multi_agent.core.types import (
    AgentRole,
    AgentMessage,
    MessageType,
    ProjectContext,
    TaskStatus,
)
from multi_agent.core.system import MultiAgentSystem


class TestMultiAgentSystem:
    """Tests for MultiAgentSystem."""
    
    @pytest.fixture
    def project_context(self) -> ProjectContext:
        """Create a test project context."""
        return ProjectContext(
            name="Test Project",
            description="Test project for system testing",
            requirements=["Feature A", "Feature B"],
            scope_boundaries=["No Feature C"],
        )
    
    @pytest.fixture
    def system(self, project_context: ProjectContext) -> MultiAgentSystem:
        """Create a multi-agent system instance."""
        return MultiAgentSystem(project_context=project_context)
    
    def test_system_initialization(self, system: MultiAgentSystem):
        """Test system initialization."""
        assert system.project_context.name == "Test Project"
        assert len(system.agents) == 7  # All agent roles
        assert AgentRole.CEO in system.agents
        assert AgentRole.CTO in system.agents
        assert AgentRole.DEVELOPER in system.agents
    
    def test_agent_configs_loaded(self, system: MultiAgentSystem):
        """Test that agent configs are properly loaded."""
        ceo_config = system.agents[AgentRole.CEO]
        
        assert ceo_config.role == AgentRole.CEO
        assert ceo_config.name == "CEO Agent"
        assert len(ceo_config.system_prompt) > 0
    
    def test_create_task(self, system: MultiAgentSystem):
        """Test task creation."""
        task = system.create_task(
            title="Test Task",
            description="Test task description",
            created_by=AgentRole.CEO,
            priority="high",
        )
        
        assert task.title == "Test Task"
        assert task.status == TaskStatus.PENDING
        assert str(task.id) in system.tasks
    
    def test_get_task(self, system: MultiAgentSystem):
        """Test task retrieval."""
        created_task = system.create_task(
            title="Test Task",
            description="Test",
            created_by=AgentRole.CEO,
        )
        
        retrieved_task = system.get_task(str(created_task.id))
        
        assert retrieved_task is not None
        assert retrieved_task.id == created_task.id
    
    @pytest.mark.asyncio
    async def test_send_message_valid(self, system: MultiAgentSystem):
        """Test sending a valid message."""
        message = AgentMessage(
            sender=AgentRole.CEO,
            receiver=AgentRole.CTO,
            message_type=MessageType.TASK_ASSIGNMENT,
            content="Please implement feature A",
        )
        
        result = await system.send_message(message)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_send_message_invalid(self, system: MultiAgentSystem):
        """Test sending an invalid message (permission denied)."""
        message = AgentMessage(
            sender=AgentRole.DEVELOPER,
            receiver=AgentRole.QA_ENGINEER,
            message_type=MessageType.TASK_ASSIGNMENT,
            content="Please test my code",
        )
        
        result = await system.send_message(message)
        
        assert result is False
    
    def test_get_agent_context(self, system: MultiAgentSystem):
        """Test getting agent context."""
        context = system.get_agent_context(AgentRole.CEO)
        
        assert isinstance(context, list)
    
    def test_clear_agent_context(self, system: MultiAgentSystem):
        """Test clearing agent context."""
        system.clear_agent_context(AgentRole.CEO)
        
        context = system.get_agent_context(AgentRole.CEO)
        assert len(context) == 0
    
    def test_get_system_status(self, system: MultiAgentSystem):
        """Test getting system status."""
        status = system.get_system_status()
        
        assert "project" in status
        assert "agents" in status
        assert "active_temp_permissions" in status
        assert "alerts" in status
    
    @pytest.mark.asyncio
    async def test_temporary_permission_request(self, system: MultiAgentSystem):
        """Test temporary permission request."""
        perm_id = await system.request_temporary_permission(
            requester=AgentRole.CTO,
            target_role=AgentRole.QA_ENGINEER,
            permission_type="direct_qa_access",
            reason="Emergency testing",
            granted_to=AgentRole.DEVELOPER,
        )
        
        assert perm_id is not None
    
    @pytest.mark.asyncio
    async def test_temporary_permission_non_cto_denied(self, system: MultiAgentSystem):
        """Test that non-CTO cannot request temporary permissions."""
        perm_id = await system.request_temporary_permission(
            requester=AgentRole.DEVELOPER,
            target_role=AgentRole.QA_ENGINEER,
            permission_type="direct_qa_access",
            reason="I want to test",
        )
        
        assert perm_id is None
    
    @pytest.mark.asyncio
    async def test_permission_violation_creates_alert(self, system: MultiAgentSystem):
        """Test that permission violation creates an alert."""
        message = AgentMessage(
            sender=AgentRole.DEVELOPER,
            receiver=AgentRole.QA_ENGINEER,
            message_type=MessageType.TASK_ASSIGNMENT,
            content="Test my code",
        )
        
        await system.send_message(message)
        
        alerts = system.alert_manager.get_active_alerts()
        
        assert len(alerts) == 1
        assert alerts[0].alert_type == "permission_violation"
