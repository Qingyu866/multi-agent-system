"""
LLM client for interacting with various LLM providers.
Supports agent-specific model configurations, timeouts, and retries.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Optional, Union

from openai import AsyncOpenAI, AsyncAzureOpenAI, APIError, APITimeoutError, APIConnectionError

from multi_agent.config import LLMConfig
from multi_agent.core.types import AgentModelConfig, ModelProvider


@dataclass
class ExtendedLLMConfig:
    """Extended LLM configuration with all parameters."""
    
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
    
    timeout: float = 60.0
    max_retries: int = 3
    retry_delay: float = 1.0
    
    http_proxy: Optional[str] = None
    https_proxy: Optional[str] = None
    
    @classmethod
    def from_llm_config(cls, config: LLMConfig) -> "ExtendedLLMConfig":
        """Create from basic LLMConfig."""
        return cls(
            provider=config.provider,
            api_key=config.api_key,
            base_url=config.base_url,
            model=config.model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            top_p=getattr(config, 'top_p', 1.0),
            frequency_penalty=getattr(config, 'frequency_penalty', 0.0),
            presence_penalty=getattr(config, 'presence_penalty', 0.0),
            azure_endpoint=config.azure_endpoint,
            azure_deployment=config.azure_deployment,
            api_version=config.api_version,
            timeout=config.timeout,
            max_retries=config.max_retries,
            retry_delay=config.retry_delay,
            http_proxy=config.http_proxy,
            https_proxy=config.https_proxy,
        )
    
    @classmethod
    def from_agent_model_config(
        cls,
        config: AgentModelConfig,
        default_api_key: Optional[str] = None,
    ) -> "ExtendedLLMConfig":
        """Create from AgentModelConfig."""
        api_key = config.get_effective_api_key(default_api_key) or ""
        
        return cls(
            provider=config.provider.value,
            api_key=api_key,
            base_url=config.base_url or "https://api.openai.com/v1",
            model=config.model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            top_p=config.top_p,
            frequency_penalty=config.frequency_penalty,
            presence_penalty=config.presence_penalty,
            azure_endpoint=config.azure_endpoint,
            azure_deployment=config.azure_deployment,
            api_version=config.api_version,
        )
    
    @classmethod
    def from_dict(cls, data: dict) -> "ExtendedLLMConfig":
        """Create from dictionary."""
        return cls(
            provider=data.get("provider", "openai"),
            api_key=data.get("api_key", ""),
            base_url=data.get("base_url", "https://api.openai.com/v1"),
            model=data.get("model", "gpt-4"),
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens", 4000),
            top_p=data.get("top_p", 1.0),
            frequency_penalty=data.get("frequency_penalty", 0.0),
            presence_penalty=data.get("presence_penalty", 0.0),
            azure_endpoint=data.get("azure_endpoint"),
            azure_deployment=data.get("azure_deployment"),
            api_version=data.get("api_version", "2024-02-01"),
            timeout=data.get("timeout", 60.0),
            max_retries=data.get("max_retries", 3),
            retry_delay=data.get("retry_delay", 1.0),
            http_proxy=data.get("http_proxy"),
            https_proxy=data.get("https_proxy"),
        )


class LLMClient:
    """
    Client for LLM API interactions.
    
    Supports:
    - OpenAI API
    - Azure OpenAI
    - Agent-specific model configurations
    - Automatic retries with exponential backoff
    - Proxy support
    - Timeout configuration
    """
    
    def __init__(
        self,
        config: Optional[Union[LLMConfig, ExtendedLLMConfig, AgentModelConfig]] = None,
        default_api_key: Optional[str] = None,
    ):
        if config is None:
            self.config = ExtendedLLMConfig()
        elif isinstance(config, AgentModelConfig):
            self.config = ExtendedLLMConfig.from_agent_model_config(
                config, default_api_key
            )
        elif isinstance(config, LLMConfig):
            self.config = ExtendedLLMConfig.from_llm_config(config)
        else:
            self.config = config
        
        self._client = None
        self._client_type: Optional[str] = None
    
    def _get_client(self):
        """Get or create the appropriate LLM client."""
        client_type = self._get_client_type()
        
        if self._client is None or self._client_type != client_type:
            self._client = self._create_client()
            self._client_type = client_type
        
        return self._client
    
    def _get_client_type(self) -> str:
        """Determine the client type based on configuration."""
        if self.config.provider == "azure" or self.config.azure_endpoint:
            return "azure"
        return "openai"
    
    def _create_client(self):
        """Create a new LLM client based on configuration."""
        if self._get_client_type() == "azure":
            return AsyncAzureOpenAI(
                api_key=self.config.api_key,
                azure_endpoint=self.config.azure_endpoint or "",
                api_version=self.config.api_version,
                timeout=self.config.timeout,
                max_retries=self.config.max_retries,
            )
        else:
            return AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                timeout=self.config.timeout,
                max_retries=self.config.max_retries,
            )
    
    async def _retry_with_backoff(self, func, *args, **kwargs):
        """Execute function with exponential backoff retry."""
        last_error = None
        
        for attempt in range(self.config.max_retries):
            try:
                return await func(*args, **kwargs)
            except APITimeoutError as e:
                last_error = e
                if attempt < self.config.max_retries - 1:
                    delay = self.config.retry_delay * (2 ** attempt)
                    print(f"\n⏳ Request timed out, retrying in {delay}s... (attempt {attempt + 2}/{self.config.max_retries})")
                    await asyncio.sleep(delay)
            except APIConnectionError as e:
                last_error = e
                if attempt < self.config.max_retries - 1:
                    delay = self.config.retry_delay * (2 ** attempt)
                    print(f"\n⏳ Connection failed, retrying in {delay}s... (attempt {attempt + 2}/{self.config.max_retries})")
                    await asyncio.sleep(delay)
            except APIError as e:
                if hasattr(e, 'status_code') and e.status_code in [429, 500, 502, 503, 504]:
                    last_error = e
                    if attempt < self.config.max_retries - 1:
                        delay = self.config.retry_delay * (2 ** attempt)
                        print(f"\n⏳ Server error ({e.status_code}), retrying in {delay}s... (attempt {attempt + 2}/{self.config.max_retries})")
                        await asyncio.sleep(delay)
                else:
                    raise
            except Exception as e:
                raise RuntimeError(f"LLM API error: {str(e)}")
        
        raise RuntimeError(f"LLM API error after {self.config.max_retries} retries: {str(last_error)}")
    
    async def chat_completion(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        stream: bool = False,
        **kwargs,
    ) -> str:
        """
        Send a chat completion request with automatic retry.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (defaults to config)
            temperature: Temperature (defaults to config)
            max_tokens: Max tokens (defaults to config)
            top_p: Top-p sampling (defaults to config)
            frequency_penalty: Frequency penalty (defaults to config)
            presence_penalty: Presence penalty (defaults to config)
            stream: Whether to stream the response
            **kwargs: Additional parameters to pass to the API
            
        Returns:
            The generated text
        """
        client = self._get_client()
        
        model_name = model or self.config.model
        if self._get_client_type() == "azure" and self.config.azure_deployment:
            model_name = self.config.azure_deployment
        
        request_params = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.config.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.config.max_tokens,
            "top_p": top_p if top_p is not None else self.config.top_p,
            "frequency_penalty": frequency_penalty if frequency_penalty is not None else self.config.frequency_penalty,
            "presence_penalty": presence_penalty if presence_penalty is not None else self.config.presence_penalty,
            "stream": stream,
        }
        
        request_params.update(kwargs)
        
        async def _make_request():
            response = await client.chat.completions.create(**request_params)
            
            if stream:
                content = ""
                async for chunk in response:
                    if chunk.choices[0].delta.content:
                        content += chunk.choices[0].delta.content
                return content
            else:
                return response.choices[0].message.content
        
        return await self._retry_with_backoff(_make_request)
    
    async def generate_with_system_prompt(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: Optional[list[dict]] = None,
        **kwargs,
    ) -> str:
        """
        Generate a response with a system prompt.
        
        Args:
            system_prompt: The system prompt
            user_message: The user message
            conversation_history: Optional conversation history
            **kwargs: Additional parameters for chat_completion
            
        Returns:
            The generated response
        """
        messages = [{"role": "system", "content": system_prompt}]
        
        if conversation_history:
            messages.extend(conversation_history)
        
        messages.append({"role": "user", "content": user_message})
        
        return await self.chat_completion(messages, **kwargs)
    
    def update_config(self, config: Union[ExtendedLLMConfig, AgentModelConfig]) -> None:
        """Update the client configuration."""
        if isinstance(config, AgentModelConfig):
            self.config = ExtendedLLMConfig.from_agent_model_config(config)
        else:
            self.config = config
        self._client = None
        self._client_type = None
    
    def get_model_info(self) -> dict:
        """Get information about the current model configuration."""
        return {
            "provider": self.config.provider,
            "model": self.config.model,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "top_p": self.config.top_p,
            "timeout": self.config.timeout,
            "max_retries": self.config.max_retries,
            "client_type": self._get_client_type(),
        }
