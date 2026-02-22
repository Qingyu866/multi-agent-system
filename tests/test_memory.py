"""
Tests for memory systems.
"""

import pytest

from multi_agent.core.types import AgentRole, AgentMessage, MessageType
from multi_agent.memory.short_term import ShortTermMemoryManager


class TestShortTermMemoryManager:
    """Tests for ShortTermMemoryManager."""
    
    @pytest.fixture
    def memory_manager(self) -> ShortTermMemoryManager:
        """Create a short-term memory manager instance."""
        return ShortTermMemoryManager(
            max_messages_per_agent=10,
            retention_hours=24,
        )
    
    @pytest.fixture
    def sample_message(self) -> AgentMessage:
        """Create a sample message."""
        return AgentMessage(
            sender=AgentRole.CTO,
            receiver=AgentRole.DEVELOPER,
            message_type=MessageType.TASK_ASSIGNMENT,
            content="Implement user authentication",
        )
    
    @pytest.mark.asyncio
    async def test_store_message(self, memory_manager: ShortTermMemoryManager, sample_message: AgentMessage):
        """Test storing a message."""
        await memory_manager.store_message(
            agent_role=AgentRole.DEVELOPER,
            message=sample_message,
        )
        
        context = memory_manager.get_context(AgentRole.DEVELOPER)
        
        assert len(context) == 1
        assert context[0].content == "Implement user authentication"
    
    @pytest.mark.asyncio
    async def test_max_messages_limit(self, memory_manager: ShortTermMemoryManager):
        """Test that message limit is enforced."""
        for i in range(15):
            message = AgentMessage(
                sender=AgentRole.CTO,
                receiver=AgentRole.DEVELOPER,
                message_type=MessageType.TASK_ASSIGNMENT,
                content=f"Task {i}",
            )
            await memory_manager.store_message(AgentRole.DEVELOPER, message)
        
        context = memory_manager.get_context(AgentRole.DEVELOPER)
        
        assert len(context) == 10
    
    @pytest.mark.asyncio
    async def test_isolated_contexts(self, memory_manager: ShortTermMemoryManager):
        """Test that agent contexts are isolated."""
        dev_message = AgentMessage(
            sender=AgentRole.CTO,
            receiver=AgentRole.DEVELOPER,
            message_type=MessageType.TASK_ASSIGNMENT,
            content="Developer task",
        )
        
        qa_message = AgentMessage(
            sender=AgentRole.CTO,
            receiver=AgentRole.QA_ENGINEER,
            message_type=MessageType.TASK_ASSIGNMENT,
            content="QA task",
        )
        
        await memory_manager.store_message(AgentRole.DEVELOPER, dev_message)
        await memory_manager.store_message(AgentRole.QA_ENGINEER, qa_message)
        
        dev_context = memory_manager.get_context(AgentRole.DEVELOPER)
        qa_context = memory_manager.get_context(AgentRole.QA_ENGINEER)
        
        assert len(dev_context) == 1
        assert len(qa_context) == 1
        assert dev_context[0].content == "Developer task"
        assert qa_context[0].content == "QA task"
    
    def test_clear_context(self, memory_manager: ShortTermMemoryManager):
        """Test clearing an agent's context."""
        message = AgentMessage(
            sender=AgentRole.CTO,
            receiver=AgentRole.DEVELOPER,
            message_type=MessageType.TASK_ASSIGNMENT,
            content="Test",
        )
        memory_manager._store_in_memory(AgentRole.DEVELOPER, message)
        
        memory_manager.clear_context(AgentRole.DEVELOPER)
        
        context = memory_manager.get_context(AgentRole.DEVELOPER)
        assert len(context) == 0
    
    def test_get_context_size(self, memory_manager: ShortTermMemoryManager):
        """Test getting context size."""
        for i in range(5):
            message = AgentMessage(
                sender=AgentRole.CTO,
                receiver=AgentRole.DEVELOPER,
                message_type=MessageType.TASK_ASSIGNMENT,
                content=f"Task {i}",
            )
            memory_manager._store_in_memory(AgentRole.DEVELOPER, message)
        
        size = memory_manager.get_context_size(AgentRole.DEVELOPER)
        
        assert size == 5
    
    def test_get_all_contexts_summary(self, memory_manager: ShortTermMemoryManager):
        """Test getting summary of all contexts."""
        message = AgentMessage(
            sender=AgentRole.CTO,
            receiver=AgentRole.DEVELOPER,
            message_type=MessageType.TASK_ASSIGNMENT,
            content="Test",
        )
        memory_manager._store_in_memory(AgentRole.DEVELOPER, message)
        
        summary = memory_manager.get_all_contexts_summary()
        
        assert "developer" in summary
        assert summary["developer"] == 1
