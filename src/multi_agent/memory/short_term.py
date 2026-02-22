"""
Short-term memory management for individual agent contexts.
Provides isolated context windows for each agent to prevent context pollution.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from multi_agent.core.types import AgentMessage, AgentRole


class ShortTermMemoryManager:
    """
    Manages short-term memory for each agent independently.
    
    Each agent has its own isolated context window to ensure:
    - Context purity: No unauthorized information leakage
    - Independent operation: Agents don't interfere with each other
    - Configurable retention: Automatic cleanup of old messages
    
    Supports both in-memory storage and Redis for distributed deployments.
    """
    
    def __init__(
        self,
        enable_redis: bool = False,
        redis_url: Optional[str] = None,
        max_messages_per_agent: int = 100,
        retention_hours: int = 24,
    ):
        self.enable_redis = enable_redis
        self.redis_url = redis_url
        self.max_messages_per_agent = max_messages_per_agent
        self.retention_hours = retention_hours
        
        self._memory: dict[AgentRole, list[AgentMessage]] = defaultdict(list)
        self._redis_client = None
        
        if enable_redis:
            self._init_redis()
    
    def _init_redis(self) -> None:
        """Initialize Redis connection for distributed memory."""
        try:
            import redis
            self._redis_client = redis.from_url(
                self.redis_url or "redis://localhost:6379"
            )
        except ImportError:
            self.enable_redis = False
            self._redis_client = None
    
    async def store_message(
        self,
        agent_role: AgentRole,
        message: AgentMessage,
    ) -> None:
        """
        Store a message in an agent's short-term memory.
        
        Automatically manages memory size by removing oldest messages
        when the limit is exceeded.
        """
        if self.enable_redis and self._redis_client:
            await self._store_in_redis(agent_role, message)
        else:
            self._store_in_memory(agent_role, message)
    
    def _store_in_memory(
        self,
        agent_role: AgentRole,
        message: AgentMessage,
    ) -> None:
        """Store message in local memory."""
        self._memory[agent_role].append(message)
        
        if len(self._memory[agent_role]) > self.max_messages_per_agent:
            self._memory[agent_role] = self._memory[agent_role][
                -self.max_messages_per_agent:
            ]
    
    async def _store_in_redis(
        self,
        agent_role: AgentRole,
        message: AgentMessage,
    ) -> None:
        """Store message in Redis for distributed access."""
        import json
        
        key = f"agent_memory:{agent_role.value}"
        message_json = message.model_dump_json()
        
        await self._redis_client.lpush(key, message_json)
        await self._redis_client.ltrim(key, 0, self.max_messages_per_agent - 1)
        await self._redis_client.expire(
            key, timedelta(hours=self.retention_hours)
        )
    
    def get_context(
        self,
        agent_role: AgentRole,
        limit: Optional[int] = None,
    ) -> list[AgentMessage]:
        """
        Retrieve the context for a specific agent.
        
        Returns messages in chronological order (oldest first).
        """
        if self.enable_redis and self._redis_client:
            return self._get_from_redis_sync(agent_role, limit)
        
        messages = self._memory.get(agent_role, [])
        
        if limit:
            messages = messages[-limit:]
        
        return list(messages)
    
    def _get_from_redis_sync(
        self,
        agent_role: AgentRole,
        limit: Optional[int] = None,
    ) -> list[AgentMessage]:
        """Synchronously get messages from Redis."""
        import json
        
        key = f"agent_memory:{agent_role.value}"
        count = limit or self.max_messages_per_agent
        
        messages_json = self._redis_client.lrange(key, 0, count - 1)
        
        messages = []
        for msg_json in reversed(messages_json):
            try:
                msg_data = json.loads(msg_json)
                messages.append(AgentMessage(**msg_data))
            except Exception:
                continue
        
        return messages
    
    def clear_context(self, agent_role: AgentRole) -> None:
        """Clear all messages from an agent's context."""
        if self.enable_redis and self._redis_client:
            key = f"agent_memory:{agent_role.value}"
            self._redis_client.delete(key)
        else:
            self._memory[agent_role] = []
    
    def get_context_size(self, agent_role: AgentRole) -> int:
        """Get the number of messages in an agent's context."""
        if self.enable_redis and self._redis_client:
            key = f"agent_memory:{agent_role.value}"
            return self._redis_client.llen(key)
        return len(self._memory.get(agent_role, []))
    
    def cleanup_expired(self) -> int:
        """
        Remove expired messages from in-memory storage.
        
        Returns the number of messages removed.
        """
        if self.enable_redis:
            return 0
        
        cutoff_time = datetime.utcnow() - timedelta(hours=self.retention_hours)
        removed_count = 0
        
        for agent_role in list(self._memory.keys()):
            original_count = len(self._memory[agent_role])
            self._memory[agent_role] = [
                msg for msg in self._memory[agent_role]
                if msg.timestamp > cutoff_time
            ]
            removed_count += original_count - len(self._memory[agent_role])
        
        return removed_count
    
    def get_all_contexts_summary(self) -> dict[str, int]:
        """Get a summary of all agent contexts."""
        if self.enable_redis and self._redis_client:
            summary = {}
            for role in AgentRole:
                key = f"agent_memory:{role.value}"
                summary[role.value] = self._redis_client.llen(key)
            return summary
        
        return {
            role.value: len(messages)
            for role, messages in self._memory.items()
        }
