"""
Core type definitions and data models for the multi-agent system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AgentRole(str, Enum):
    """Agent role definitions following hierarchical structure."""
    
    CEO = "ceo"
    ADVISOR = "advisor"
    CTO = "cto"
    DEVELOPER = "developer"
    QA_ENGINEER = "qa_engineer"
    DESIGNER = "designer"
    DOCUMENTATION = "documentation"


class ModelProvider(str, Enum):
    """Supported LLM providers."""
    
    OPENAI = "openai"
    AZURE = "azure"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    CUSTOM = "custom"


class TaskStatus(str, Enum):
    """Task lifecycle status."""
    
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    IN_REVIEW = "in_review"
    COMPLETED = "completed"
    FAILED = "failed"
    ESCALATED = "escalated"


class TaskPriority(str, Enum):
    """Task priority levels."""
    
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PermissionLevel(str, Enum):
    """Permission levels for agent interactions."""
    
    FULL = "full"
    STANDARD = "standard"
    LIMITED = "limited"
    READ_ONLY = "read_only"


class MessageType(str, Enum):
    """Types of messages between agents."""
    
    TASK_ASSIGNMENT = "task_assignment"
    TASK_UPDATE = "task_update"
    TASK_COMPLETION = "task_completion"
    QUESTION = "question"
    ANSWER = "answer"
    ESCALATION = "escalation"
    PERMISSION_REQUEST = "permission_request"
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_DENIED = "permission_denied"
    ALERT = "alert"
    ADVISOR_SUMMONS = "advisor_summons"
    ADVISOR_RULING = "advisor_ruling"


@dataclass
class AgentModelConfig:
    """
    Model configuration for an individual agent.
    
    Allows each agent to have its own dedicated model configuration,
    enabling fine-grained control over model selection and parameters.
    """
    
    provider: ModelProvider = ModelProvider.OPENAI
    model: str = "gpt-4"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    
    temperature: float = 0.7
    max_tokens: int = 4000
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    
    azure_endpoint: Optional[str] = None
    azure_deployment: Optional[str] = None
    api_version: str = "2024-02-01"
    
    anthropic_api_key: Optional[str] = None
    
    local_model_path: Optional[str] = None
    
    custom_client_class: Optional[str] = None
    custom_config: dict[str, Any] = field(default_factory=dict)
    
    enabled: bool = True
    fallback_model: Optional[str] = None
    rate_limit_rpm: Optional[int] = None
    rate_limit_tpm: Optional[int] = None
    
    def get_effective_api_key(self, default_key: Optional[str] = None) -> Optional[str]:
        """Get the effective API key, using default if not set."""
        if self.api_key:
            return self.api_key
        if self.provider == ModelProvider.AZURE and self.azure_endpoint:
            return None
        if self.provider == ModelProvider.ANTHROPIC and self.anthropic_api_key:
            return self.anthropic_api_key
        return default_key
    
    def to_llm_config_dict(self, default_api_key: Optional[str] = None) -> dict:
        """Convert to a dictionary suitable for LLMClient initialization."""
        config = {
            "provider": self.provider.value,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
        }
        
        api_key = self.get_effective_api_key(default_api_key)
        if api_key:
            config["api_key"] = api_key
        
        if self.base_url:
            config["base_url"] = self.base_url
        
        if self.provider == ModelProvider.AZURE:
            if self.azure_endpoint:
                config["azure_endpoint"] = self.azure_endpoint
            if self.azure_deployment:
                config["azure_deployment"] = self.azure_deployment
            config["api_version"] = self.api_version
        
        if self.provider == ModelProvider.ANTHROPIC and self.anthropic_api_key:
            config["api_key"] = self.anthropic_api_key
        
        return config


@dataclass
class AgentConfig:
    """Configuration for an individual agent."""
    
    role: AgentRole
    name: str
    system_prompt: str
    permission_whitelist: list[AgentRole] = field(default_factory=list)
    permission_level: PermissionLevel = PermissionLevel.STANDARD
    max_context_tokens: int = 4000
    tools: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    model_config: Optional[AgentModelConfig] = None


class AgentMessage(BaseModel):
    """Message structure for inter-agent communication."""
    
    id: UUID = Field(default_factory=uuid4)
    sender: AgentRole
    receiver: AgentRole
    message_type: MessageType
    content: str
    task_id: Optional[UUID] = None
    parent_message_id: Optional[UUID] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskContext(BaseModel):
    """Context for a specific task being processed."""
    
    id: UUID = Field(default_factory=uuid4)
    title: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    assigned_to: Optional[AgentRole] = None
    created_by: AgentRole
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    iteration_count: int = 0
    max_iterations: int = 3
    history: list[AgentMessage] = Field(default_factory=list)
    dependencies: list[UUID] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    
    def increment_iteration(self) -> bool:
        """Increment iteration count and check if limit exceeded."""
        self.iteration_count += 1
        self.updated_at = datetime.utcnow()
        return self.iteration_count < self.max_iterations
    
    def is_loop_detected(self) -> bool:
        """Check if task has exceeded maximum iterations."""
        return self.iteration_count >= self.max_iterations


class ProjectContext(BaseModel):
    """Global project context shared across agents."""
    
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str
    requirements: list[str] = Field(default_factory=list)
    scope_boundaries: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    active_tasks: list[UUID] = Field(default_factory=list)
    completed_tasks: list[UUID] = Field(default_factory=list)
    decisions: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TemporaryPermission(BaseModel):
    """Temporary permission grant for emergency situations."""
    
    id: UUID = Field(default_factory=uuid4)
    granted_to: AgentRole
    granted_by: AgentRole
    permission_type: str
    target_role: AgentRole
    reason: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    is_active: bool = True
    task_id: Optional[str] = None
    
    def is_expired(self) -> bool:
        """Check if the temporary permission has expired."""
        return datetime.utcnow() > self.expires_at or not self.is_active
    
    def revoke(self) -> None:
        """Revoke the temporary permission."""
        self.is_active = False


class AlertType(str, Enum):
    """Types of system alerts."""
    
    LOOP_DETECTED = "loop_detected"
    SCOPE_DRIFT = "scope_drift"
    PERMISSION_VIOLATION = "permission_violation"
    TASK_BLOCKED = "task_blocked"
    EMERGENCY_ESCALATION = "emergency_escalation"
    TEMP_PERMISSION_EXPIRED = "temp_permission_expired"


class SystemAlert(BaseModel):
    """System alert for monitoring and intervention."""
    
    id: UUID = Field(default_factory=uuid4)
    alert_type: AlertType
    severity: TaskPriority
    source_agent: AgentRole
    target_agent: Optional[AgentRole] = None
    task_id: Optional[str] = None
    message: str
    context: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolution: Optional[str] = None
