"""
Configuration management for the multi-agent system.
Supports agent-specific model configurations.
"""

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class LLMConfig:
    """Configuration for LLM providers."""
    
    provider: str = "openai"
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 4000
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    
    azure_endpoint: Optional[str] = None
    azure_deployment: Optional[str] = None
    api_version: str = "2024-02-01"
    
    timeout: float = 120.0
    max_retries: int = 3
    retry_delay: float = 2.0
    
    http_proxy: Optional[str] = None
    https_proxy: Optional[str] = None


@dataclass
class MemoryConfig:
    """Configuration for memory systems."""
    
    enable_redis: bool = False
    redis_url: str = "redis://localhost:6379/0"
    max_messages_per_agent: int = 100
    retention_hours: int = 24
    
    chroma_persist_dir: str = "./chroma_db"
    embedding_model: str = "all-MiniLM-L6-v2"


@dataclass
class SystemConfig:
    """Configuration for system behavior."""
    
    max_iterations: int = 3
    default_temp_permission_duration: int = 30
    max_context_tokens: int = 8000
    log_level: str = "INFO"
    enable_monitoring: bool = True


class Config:
    """Main configuration class with agent-specific model support."""
    
    def __init__(self):
        self.llm = self._load_llm_config()
        self.memory = self._load_memory_config()
        self.system = self._load_system_config()
        self.agent_models = self._load_agent_model_configs()
    
    def _load_llm_config(self) -> LLMConfig:
        """Load LLM configuration from environment."""
        provider = os.getenv("LLM_PROVIDER", "openai").lower()
        
        if provider == "azure":
            return LLMConfig(
                provider="azure",
                api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
                azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4"),
                model=os.getenv("OPENAI_MODEL", "gpt-4"),
                temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
                max_tokens=int(os.getenv("LLM_MAX_TOKENS", "4000")),
                timeout=float(os.getenv("LLM_TIMEOUT", "120.0")),
                max_retries=int(os.getenv("LLM_MAX_RETRIES", "3")),
                retry_delay=float(os.getenv("LLM_RETRY_DELAY", "2.0")),
                http_proxy=os.getenv("HTTP_PROXY"),
                https_proxy=os.getenv("HTTPS_PROXY"),
            )
        else:
            return LLMConfig(
                provider="openai",
                api_key=os.getenv("OPENAI_API_KEY", ""),
                base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                model=os.getenv("OPENAI_MODEL", "gpt-4"),
                temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
                max_tokens=int(os.getenv("LLM_MAX_TOKENS", "4000")),
                timeout=float(os.getenv("LLM_TIMEOUT", "120.0")),
                max_retries=int(os.getenv("LLM_MAX_RETRIES", "3")),
                retry_delay=float(os.getenv("LLM_RETRY_DELAY", "2.0")),
                http_proxy=os.getenv("HTTP_PROXY"),
                https_proxy=os.getenv("HTTPS_PROXY"),
            )
    
    def _load_memory_config(self) -> MemoryConfig:
        """Load memory configuration from environment."""
        return MemoryConfig(
            enable_redis=os.getenv("ENABLE_REDIS", "false").lower() == "true",
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            max_messages_per_agent=int(os.getenv("MAX_MESSAGES_PER_AGENT", "100")),
            retention_hours=int(os.getenv("RETENTION_HOURS", "24")),
            chroma_persist_dir=os.getenv("CHROMA_PERSIST_DIR", "./chroma_db"),
            embedding_model=os.getenv("CHROMA_EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
        )
    
    def _load_system_config(self) -> SystemConfig:
        """Load system configuration from environment."""
        return SystemConfig(
            max_iterations=int(os.getenv("MAX_ITERATIONS", "3")),
            default_temp_permission_duration=int(
                os.getenv("DEFAULT_TEMP_PERMISSION_DURATION", "30")
            ),
            max_context_tokens=int(os.getenv("MAX_CONTEXT_TOKENS", "8000")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            enable_monitoring=os.getenv("ENABLE_MONITORING", "true").lower() == "true",
        )
    
    def _load_agent_model_configs(self) -> dict:
        """Load agent-specific model configurations from environment."""
        from multi_agent.core.types import AgentRole, AgentModelConfig, ModelProvider
        
        configs = {}
        
        agent_env_mapping = {
            AgentRole.CEO: "CEO",
            AgentRole.ADVISOR: "ADVISOR",
            AgentRole.CTO: "CTO",
            AgentRole.DEVELOPER: "DEVELOPER",
            AgentRole.QA_ENGINEER: "QA",
            AgentRole.DESIGNER: "DESIGNER",
            AgentRole.DOCUMENTATION: "DOCUMENTATION",
        }
        
        global_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        global_api_key = os.getenv("OPENAI_API_KEY", "")
        
        for role, env_suffix in agent_env_mapping.items():
            model = os.getenv(f"AGENT_{env_suffix}_MODEL")
            
            if model:
                agent_base_url = os.getenv(f"AGENT_{env_suffix}_BASE_URL") or global_base_url
                agent_api_key = os.getenv(f"AGENT_{env_suffix}_API_KEY") or global_api_key
                
                config = AgentModelConfig(
                    provider=ModelProvider.OPENAI,
                    model=model,
                    api_key=agent_api_key,
                    base_url=agent_base_url,
                    temperature=float(os.getenv(f"AGENT_{env_suffix}_TEMPERATURE", "0.7")),
                    max_tokens=int(os.getenv(f"AGENT_{env_suffix}_MAX_TOKENS", "4000")),
                    top_p=float(os.getenv(f"AGENT_{env_suffix}_TOP_P", "1.0")),
                    frequency_penalty=float(os.getenv(f"AGENT_{env_suffix}_FREQUENCY_PENALTY", "0.0")),
                    presence_penalty=float(os.getenv(f"AGENT_{env_suffix}_PRESENCE_PENALTY", "0.0")),
                )
                
                azure_endpoint = os.getenv(f"AGENT_{env_suffix}_AZURE_ENDPOINT")
                if azure_endpoint:
                    config.provider = ModelProvider.AZURE
                    config.azure_endpoint = azure_endpoint
                    config.azure_deployment = os.getenv(f"AGENT_{env_suffix}_AZURE_DEPLOYMENT")
                
                configs[role] = config
        
        return configs
    
    def get_agent_model_config(self, role) -> Optional["AgentModelConfig"]:
        """Get model configuration for a specific agent role."""
        from multi_agent.core.types import AgentRole
        
        if isinstance(role, str):
            role = AgentRole(role)
        
        return self.agent_models.get(role)
    
    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        if not self.llm.api_key:
            errors.append("LLM API key is required. Set OPENAI_API_KEY or AZURE_OPENAI_API_KEY")
        
        if self.llm.provider == "azure":
            if not self.llm.azure_endpoint:
                errors.append("Azure endpoint is required for Azure provider")
            if not self.llm.azure_deployment:
                errors.append("Azure deployment name is required for Azure provider")
        
        return errors
    
    def get_all_agent_configs_summary(self) -> dict:
        """Get a summary of all agent model configurations."""
        from multi_agent.core.types import AgentRole
        
        summary = {}
        
        for role in AgentRole:
            config = self.agent_models.get(role)
            if config:
                summary[role.value] = {
                    "model": config.model,
                    "temperature": config.temperature,
                    "max_tokens": config.max_tokens,
                    "has_custom_api_key": bool(config.api_key),
                }
            else:
                summary[role.value] = {
                    "model": self.llm.model,
                    "temperature": self.llm.temperature,
                    "max_tokens": self.llm.max_tokens,
                    "has_custom_api_key": False,
                    "using_default": True,
                }
        
        return summary


config = Config()
@dataclass
class LLMConfig:
    """Configuration for LLM providers."""
    
    provider: str = "openai"
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 4000
    
    azure_endpoint: Optional[str] = None
    azure_deployment: Optional[str] = None
    api_version: str = "2024-02-01"
    
    timeout: float = 120.0
    max_retries: int = 3
    retry_delay: float = 2.0
    
    http_proxy: Optional[str] = None
    https_proxy: Optional[str] = None