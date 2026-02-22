"""
LLM-powered agent implementation.
Supports agent-specific model configurations.
"""

from typing import Optional, Union

from multi_agent.core.types import AgentRole, AgentMessage, MessageType, AgentConfig, AgentModelConfig, ModelProvider
from multi_agent.llm.client import LLMClient, ExtendedLLMConfig
from multi_agent.config import config


class LLMAgent:
    """
    An agent powered by LLM for intelligent responses.
    
    This wraps an AgentConfig with LLM capabilities to enable
    intelligent agent behavior. Each agent can have its own
    dedicated model configuration.
    """
    
    def __init__(
        self,
        role: AgentRole,
        llm_client: Optional[LLMClient] = None,
        model_config: Optional[AgentModelConfig] = None,
        default_api_key: Optional[str] = None,
    ):
        self.role = role
        self.agent_config = self._get_agent_config(role)
        self.conversation_history: list[dict] = []
        
        if llm_client is not None:
            self.llm_client = llm_client
        elif model_config is not None:
            self.llm_client = LLMClient(
                config=model_config,
                default_api_key=default_api_key,
            )
        elif self.agent_config.model_config is not None:
            self.llm_client = LLMClient(
                config=self.agent_config.model_config,
                default_api_key=default_api_key or config.llm.api_key,
            )
        else:
            self.llm_client = LLMClient(config.llm)
    
    def _get_agent_config(self, role: AgentRole) -> AgentConfig:
        """Get configuration for this agent role."""
        from multi_agent.agents.prompts import get_agent_config
        return get_agent_config(role)
    
    @property
    def config(self) -> AgentConfig:
        """Get the agent configuration."""
        return self.agent_config
    
    @property
    def model_config(self) -> Optional[AgentModelConfig]:
        """Get the model configuration for this agent."""
        return self.agent_config.model_config
    
    def set_model_config(self, model_config: AgentModelConfig) -> None:
        """
        Set a new model configuration for this agent.
        
        Args:
            model_config: The new model configuration
        """
        self.agent_config.model_config = model_config
        self.llm_client.update_config(model_config)
    
    async def process_message(self, message: AgentMessage) -> str:
        """
        Process an incoming message and generate a response.
        
        Args:
            message: The incoming message
            
        Returns:
            The agent's response
        """
        user_content = self._build_user_prompt(message)
        
        response = await self.llm_client.generate_with_system_prompt(
            system_prompt=self.agent_config.system_prompt,
            user_message=user_content,
            conversation_history=self.conversation_history[-10:],
        )
        
        self.conversation_history.append({
            "role": "user",
            "content": user_content,
        })
        self.conversation_history.append({
            "role": "assistant",
            "content": response,
        })
        
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
        
        return response
    
    def _build_user_prompt(self, message: AgentMessage) -> str:
        """Build the user prompt from the message."""
        prompt_parts = [
            f"Message from {message.sender.value}:",
            f"Type: {message.message_type.value}",
            f"Content: {message.content}",
        ]
        
        if message.task_id:
            prompt_parts.append(f"Task ID: {message.task_id}")
        
        if message.metadata:
            prompt_parts.append(f"Metadata: {message.metadata}")
        
        return "\n".join(prompt_parts)
    
    async def generate_task_plan(
        self,
        requirements: str,
        constraints: Optional[list[str]] = None,
    ) -> dict:
        """
        Generate a task plan based on requirements.
        
        Args:
            requirements: The task requirements
            constraints: Optional constraints
            
        Returns:
            A task plan dict
        """
        constraint_text = ""
        if constraints:
            constraint_text = "\nConstraints:\n" + "\n".join(f"- {c}" for c in constraints)
        
        prompt = f"""Based on the following requirements, create a task plan:

Requirements:
{requirements}
{constraint_text}

Please provide:
1. Task breakdown (list of subtasks)
2. Dependencies between tasks
3. Estimated complexity (low/medium/high)
4. Recommended assignee roles

Format your response as JSON with keys: tasks, dependencies, complexity, assignees"""

        response = await self.llm_client.generate_with_system_prompt(
            system_prompt=self.agent_config.system_prompt,
            user_message=prompt,
        )
        
        try:
            import json
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            else:
                json_str = response
            
            return json.loads(json_str.strip())
        except Exception:
            return {
                "raw_response": response,
                "tasks": [],
                "dependencies": [],
                "complexity": "medium",
                "assignees": [],
            }
    
    async def review_code(
        self,
        code: str,
        context: Optional[str] = None,
    ) -> dict:
        """
        Review code and provide feedback.
        
        Args:
            code: The code to review
            context: Optional context
            
        Returns:
            Review results
        """
        prompt = f"""Please review the following code:

```python
{code}
```

Context: {context or 'No additional context'}

Provide feedback on:
1. Code quality
2. Potential bugs
3. Security issues
4. Performance concerns
5. Suggestions for improvement

Format as JSON with keys: quality_score (1-10), issues (list), suggestions (list)"""

        response = await self.llm_client.generate_with_system_prompt(
            system_prompt=self.agent_config.system_prompt,
            user_message=prompt,
        )
        
        try:
            import json
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            else:
                json_str = response
            
            return json.loads(json_str.strip())
        except Exception:
            return {
                "raw_response": response,
                "quality_score": 5,
                "issues": [],
                "suggestions": [],
            }
    
    def clear_history(self) -> None:
        """Clear the conversation history."""
        self.conversation_history = []
    
    def get_model_info(self) -> dict:
        """Get information about the current model configuration."""
        return self.llm_client.get_model_info()
    
    def __repr__(self) -> str:
        return f"LLMAgent(role={self.role.value}, model={self.get_model_info()['model']})"


class AgentModelManager:
    """
    Manager for agent-specific model configurations.
    
    Provides centralized management of model configurations
    for all agents in the system.
    """
    
    def __init__(self, default_api_key: Optional[str] = None):
        self.default_api_key = default_api_key
        self._model_configs: dict[AgentRole, AgentModelConfig] = {}
        self._llm_clients: dict[AgentRole, LLMClient] = {}
    
    def configure_agent_model(
        self,
        role: AgentRole,
        model_config: AgentModelConfig,
    ) -> None:
        """
        Configure a specific model for an agent.
        
        Args:
            role: The agent role
            model_config: The model configuration
        """
        self._model_configs[role] = model_config
        self._llm_clients[role] = LLMClient(
            config=model_config,
            default_api_key=self.default_api_key,
        )
    
    def get_model_config(self, role: AgentRole) -> Optional[AgentModelConfig]:
        """Get the model configuration for an agent."""
        return self._model_configs.get(role)
    
    def get_llm_client(self, role: AgentRole) -> LLMClient:
        """
        Get or create an LLM client for an agent.
        
        Returns the agent-specific client if configured,
        otherwise creates a default client.
        """
        if role in self._llm_clients:
            return self._llm_clients[role]
        
        if role in self._model_configs:
            self._llm_clients[role] = LLMClient(
                config=self._model_configs[role],
                default_api_key=self.default_api_key,
            )
            return self._llm_clients[role]
        
        from multi_agent.config import config
        return LLMClient(config.llm)
    
    def create_agent(self, role: AgentRole) -> LLMAgent:
        """
        Create an LLM agent with the configured model.
        
        Args:
            role: The agent role
            
        Returns:
            A configured LLMAgent instance
        """
        model_config = self._model_configs.get(role)
        return LLMAgent(
            role=role,
            model_config=model_config,
            default_api_key=self.default_api_key,
        )
    
    def get_all_model_configs(self) -> dict[str, AgentModelConfig]:
        """Get all configured model configurations."""
        return {
            role.value: config
            for role, config in self._model_configs.items()
        }
    
    def load_from_dict(self, configs: dict[str, dict]) -> None:
        """
        Load model configurations from a dictionary.
        
        Args:
            configs: Dictionary mapping role names to config dicts
        """
        for role_str, config_dict in configs.items():
            try:
                role = AgentRole(role_str)
                model_config = AgentModelConfig(
                    provider=ModelProvider(config_dict.get("provider", "openai")),
                    model=config_dict.get("model", "gpt-4"),
                    api_key=config_dict.get("api_key"),
                    base_url=config_dict.get("base_url"),
                    temperature=config_dict.get("temperature", 0.7),
                    max_tokens=config_dict.get("max_tokens", 4000),
                    top_p=config_dict.get("top_p", 1.0),
                    frequency_penalty=config_dict.get("frequency_penalty", 0.0),
                    presence_penalty=config_dict.get("presence_penalty", 0.0),
                    azure_endpoint=config_dict.get("azure_endpoint"),
                    azure_deployment=config_dict.get("azure_deployment"),
                )
                self.configure_agent_model(role, model_config)
            except ValueError:
                pass
    
    def to_dict(self) -> dict[str, dict]:
        """Export all model configurations to a dictionary."""
        result = {}
        for role, config in self._model_configs.items():
            result[role.value] = {
                "provider": config.provider.value,
                "model": config.model,
                "api_key": "***" if config.api_key else None,
                "base_url": config.base_url,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
                "top_p": config.top_p,
                "frequency_penalty": config.frequency_penalty,
                "presence_penalty": config.presence_penalty,
                "azure_endpoint": config.azure_endpoint,
                "azure_deployment": config.azure_deployment,
            }
        return result
