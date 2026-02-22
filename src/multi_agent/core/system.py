"""
Main multi-agent system orchestration.
"""

from typing import Optional

from multi_agent.core.types import (
    AgentConfig,
    AgentMessage,
    AgentRole,
    ProjectContext,
    TaskContext,
)
from multi_agent.memory.short_term import ShortTermMemoryManager
from multi_agent.memory.long_term import LongTermMemoryManager
from multi_agent.permissions.guard import PermissionGuard
from multi_agent.permissions.temp_auth import TemporaryAuthManager
from multi_agent.monitoring.loop_detector import LoopDetector
from multi_agent.monitoring.scope_monitor import ScopeMonitor
from multi_agent.monitoring.alert_manager import AlertManager


class MultiAgentSystem:
    """
    Main orchestrator for the multi-agent collaboration system.
    
    Implements a hierarchical agent architecture with:
    - Dual-track memory system (short-term + long-term)
    - Permission-based access control
    - Temporary authorization mechanism
    - Loop detection and advisor intervention
    - Scope drift monitoring
    """
    
    def __init__(
        self,
        project_context: ProjectContext,
        enable_redis: bool = False,
        redis_url: Optional[str] = None,
        chroma_persist_dir: Optional[str] = None,
    ):
        self.project_context = project_context
        self.agents: dict[AgentRole, AgentConfig] = {}
        self.tasks: dict[str, TaskContext] = {}
        
        self.short_term_memory = ShortTermMemoryManager(
            enable_redis=enable_redis,
            redis_url=redis_url,
        )
        self.long_term_memory = LongTermMemoryManager(
            persist_directory=chroma_persist_dir,
        )
        
        self.permission_guard = PermissionGuard()
        self.temp_auth_manager = TemporaryAuthManager()
        self.loop_detector = LoopDetector()
        self.scope_monitor = ScopeMonitor(project_context)
        self.alert_manager = AlertManager()
        
        self._initialize_agents()
    
    def _initialize_agents(self) -> None:
        """Initialize all agent configurations with their roles and permissions."""
        from multi_agent.agents.prompts import get_agent_config
        
        for role in AgentRole:
            config = get_agent_config(role)
            self.agents[role] = config
    
    def register_agent(self, config: AgentConfig) -> None:
        """Register a new agent or update existing one."""
        self.agents[config.role] = config
    
    async def send_message(self, message: AgentMessage) -> bool:
        """
        Send a message from one agent to another.
        
        Validates permissions, checks for loops, and routes the message.
        """
        permission_result = self.permission_guard.validate_communication(
            sender=message.sender,
            receiver=message.receiver,
            temp_permissions=self.temp_auth_manager.get_active_permissions(
                message.sender
            ),
        )
        
        if not permission_result.allowed:
            await self.alert_manager.create_permission_violation_alert(
                source_agent=message.sender,
                target_agent=message.receiver,
                reason=permission_result.reason,
            )
            return False
        
        if message.task_id:
            task = self.tasks.get(str(message.task_id))
            if task:
                loop_detected = self.loop_detector.check_and_record(
                    task_id=str(message.task_id),
                    from_agent=message.sender,
                    to_agent=message.receiver,
                )
                
                if loop_detected:
                    await self.alert_manager.create_loop_alert(
                        task_id=str(message.task_id),
                        source_agent=message.sender,
                    )
                    return False
        
        await self.short_term_memory.store_message(
            agent_role=message.receiver,
            message=message,
        )
        
        return True
    
    def create_task(
        self,
        title: str,
        description: str,
        created_by: AgentRole,
        priority: str = "medium",
    ) -> TaskContext:
        """Create a new task in the system."""
        from multi_agent.core.types import TaskPriority
        
        task = TaskContext(
            title=title,
            description=description,
            created_by=created_by,
            priority=TaskPriority(priority),
        )
        self.tasks[str(task.id)] = task
        self.project_context.active_tasks.append(task.id)
        return task
    
    def get_task(self, task_id: str) -> Optional[TaskContext]:
        """Retrieve a task by its ID."""
        return self.tasks.get(task_id)
    
    async def request_temporary_permission(
        self,
        requester: AgentRole,
        target_role: AgentRole,
        permission_type: str,
        reason: str,
        duration_minutes: int = 30,
        task_id: Optional[str] = None,
        granted_to: Optional[AgentRole] = None,
    ) -> Optional[str]:
        """
        Request temporary permission escalation.
        
        Only CTO can request temporary permissions.
        """
        if requester != AgentRole.CTO:
            return None
        
        actual_granted_to = granted_to if granted_to else requester
        
        permission = self.temp_auth_manager.grant_permission(
            granted_to=actual_granted_to,
            target_role=target_role,
            permission_type=permission_type,
            reason=reason,
            duration_minutes=duration_minutes,
            task_id=task_id,
        )
        
        return str(permission.id) if permission else None
    
    async def escalate_to_advisor(
        self,
        task_id: str,
        context: dict,
    ) -> dict:
        """
        Escalate a task to the advisor committee for intervention.
        
        Used when loops are detected or scope drift occurs.
        """
        from multi_agent.advisor.committee import AdvisorCommittee
        
        task = self.tasks.get(task_id)
        if not task:
            return {"error": "Task not found"}
        
        committee = AdvisorCommittee(
            long_term_memory=self.long_term_memory,
        )
        
        ruling = await committee.analyze_and_rule(
            task=task,
            context=context,
        )
        
        return ruling
    
    async def store_knowledge(
        self,
        content: str,
        metadata: dict,
        collection: str = "project_documents",
    ) -> str:
        """Store knowledge in the long-term memory."""
        return await self.long_term_memory.store(
            content=content,
            metadata=metadata,
            collection=collection,
        )
    
    async def retrieve_knowledge(
        self,
        query: str,
        collection: str = "project_documents",
        n_results: int = 5,
    ) -> list[dict]:
        """Retrieve relevant knowledge from long-term memory."""
        return await self.long_term_memory.retrieve(
            query=query,
            collection=collection,
            n_results=n_results,
        )
    
    def get_agent_context(self, agent_role: AgentRole) -> list[AgentMessage]:
        """Get the current context (short-term memory) for an agent."""
        return self.short_term_memory.get_context(agent_role)
    
    def clear_agent_context(self, agent_role: AgentRole) -> None:
        """Clear the short-term memory for an agent."""
        self.short_term_memory.clear_context(agent_role)
    
    def get_system_status(self) -> dict:
        """Get the current system status for monitoring."""
        return {
            "project": {
                "id": str(self.project_context.id),
                "name": self.project_context.name,
                "active_tasks": len(self.project_context.active_tasks),
                "completed_tasks": len(self.project_context.completed_tasks),
            },
            "agents": {
                role.value: {
                    "name": config.name,
                    "permission_level": config.permission_level.value,
                }
                for role, config in self.agents.items()
            },
            "active_temp_permissions": len(
                self.temp_auth_manager.get_all_active()
            ),
            "alerts": self.alert_manager.get_active_alerts_summary(),
        }
