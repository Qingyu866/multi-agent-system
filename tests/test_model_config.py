"""
Tests for agent-specific model configurations.
"""

import pytest

from multi_agent.core.types import AgentRole, AgentModelConfig, ModelProvider
from multi_agent.llm.client import LLMClient, ExtendedLLMConfig
from multi_agent.llm.agent import LLMAgent, AgentModelManager


class TestAgentModelConfig:
    """Tests for AgentModelConfig."""
    
    def test_default_config(self):
        """Test default model configuration."""
        config = AgentModelConfig()
        
        assert config.provider == ModelProvider.OPENAI
        assert config.model == "gpt-4"
        assert config.temperature == 0.7
        assert config.max_tokens == 4000
        assert config.enabled is True
    
    def test_custom_config(self):
        """Test custom model configuration."""
        config = AgentModelConfig(
            provider=ModelProvider.AZURE,
            model="gpt-4-32k",
            api_key="custom-key",
            temperature=0.5,
            max_tokens=8000,
            azure_endpoint="https://example.openai.azure.com/",
            azure_deployment="gpt-4-deployment",
        )
        
        assert config.provider == ModelProvider.AZURE
        assert config.model == "gpt-4-32k"
        assert config.api_key == "custom-key"
        assert config.temperature == 0.5
        assert config.max_tokens == 8000
        assert config.azure_endpoint == "https://example.openai.azure.com/"
    
    def test_get_effective_api_key(self):
        """Test effective API key resolution."""
        config = AgentModelConfig(api_key="agent-key")
        
        assert config.get_effective_api_key() == "agent-key"
        assert config.get_effective_api_key("default-key") == "agent-key"
        
        config_no_key = AgentModelConfig()
        assert config_no_key.get_effective_api_key("default-key") == "default-key"
    
    def test_to_llm_config_dict(self):
        """Test conversion to LLM config dictionary."""
        config = AgentModelConfig(
            model="gpt-3.5-turbo",
            temperature=0.3,
            max_tokens=2000,
        )
        
        config_dict = config.to_llm_config_dict("default-api-key")
        
        assert config_dict["provider"] == "openai"
        assert config_dict["model"] == "gpt-3.5-turbo"
        assert config_dict["temperature"] == 0.3
        assert config_dict["max_tokens"] == 2000
        assert config_dict["api_key"] == "default-api-key"


class TestExtendedLLMConfig:
    """Tests for ExtendedLLMConfig."""
    
    def test_from_agent_model_config(self):
        """Test creating from AgentModelConfig."""
        agent_config = AgentModelConfig(
            model="gpt-4",
            temperature=0.8,
            max_tokens=6000,
            top_p=0.9,
        )
        
        extended = ExtendedLLMConfig.from_agent_model_config(
            agent_config, "default-key"
        )
        
        assert extended.model == "gpt-4"
        assert extended.temperature == 0.8
        assert extended.max_tokens == 6000
        assert extended.top_p == 0.9
    
    def test_from_dict(self):
        """Test creating from dictionary."""
        config = ExtendedLLMConfig.from_dict({
            "provider": "azure",
            "model": "gpt-4",
            "temperature": 0.5,
            "azure_endpoint": "https://example.azure.com/",
        })
        
        assert config.provider == "azure"
        assert config.model == "gpt-4"
        assert config.temperature == 0.5
        assert config.azure_endpoint == "https://example.azure.com/"


class TestLLMClientWithAgentConfig:
    """Tests for LLMClient with agent-specific configurations."""
    
    def test_client_with_agent_model_config(self):
        """Test creating client with AgentModelConfig."""
        config = AgentModelConfig(
            model="gpt-3.5-turbo",
            temperature=0.5,
            max_tokens=2000,
        )
        
        client = LLMClient(config=config, default_api_key="test-key")
        
        assert client.config.model == "gpt-3.5-turbo"
        assert client.config.temperature == 0.5
        assert client.config.max_tokens == 2000
    
    def test_update_config(self):
        """Test updating client configuration."""
        client = LLMClient()
        
        new_config = AgentModelConfig(
            model="gpt-4-turbo",
            temperature=0.9,
        )
        
        client.update_config(new_config)
        
        assert client.config.model == "gpt-4-turbo"
        assert client.config.temperature == 0.9
    
    def test_get_model_info(self):
        """Test getting model information."""
        config = AgentModelConfig(
            model="gpt-4",
            temperature=0.7,
            max_tokens=4000,
        )
        
        client = LLMClient(config=config)
        info = client.get_model_info()
        
        assert info["model"] == "gpt-4"
        assert info["temperature"] == 0.7
        assert info["max_tokens"] == 4000
        assert info["provider"] == "openai"


class TestAgentModelManager:
    """Tests for AgentModelManager."""
    
    def test_configure_agent_model(self):
        """Test configuring agent model."""
        manager = AgentModelManager(default_api_key="default-key")
        
        config = AgentModelConfig(
            model="gpt-4",
            temperature=0.7,
        )
        
        manager.configure_agent_model(AgentRole.CEO, config)
        
        assert manager.get_model_config(AgentRole.CEO) == config
    
    def test_get_llm_client(self):
        """Test getting LLM client for agent."""
        manager = AgentModelManager(default_api_key="default-key")
        
        config = AgentModelConfig(model="gpt-3.5-turbo")
        manager.configure_agent_model(AgentRole.DEVELOPER, config)
        
        client = manager.get_llm_client(AgentRole.DEVELOPER)
        
        assert client.config.model == "gpt-3.5-turbo"
    
    def test_create_agent(self):
        """Test creating agent with configured model."""
        manager = AgentModelManager(default_api_key="default-key")
        
        config = AgentModelConfig(
            model="gpt-4",
            temperature=0.5,
        )
        
        manager.configure_agent_model(AgentRole.CTO, config)
        
        agent = manager.create_agent(AgentRole.CTO)
        
        assert agent.role == AgentRole.CTO
        assert agent.get_model_info()["model"] == "gpt-4"
    
    def test_load_from_dict(self):
        """Test loading configurations from dictionary."""
        manager = AgentModelManager(default_api_key="default-key")
        
        configs = {
            "ceo": {
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 8000,
            },
            "developer": {
                "model": "gpt-3.5-turbo",
                "temperature": 0.3,
                "max_tokens": 4000,
            },
        }
        
        manager.load_from_dict(configs)
        
        ceo_config = manager.get_model_config(AgentRole.CEO)
        assert ceo_config.model == "gpt-4"
        assert ceo_config.temperature == 0.7
        
        dev_config = manager.get_model_config(AgentRole.DEVELOPER)
        assert dev_config.model == "gpt-3.5-turbo"
        assert dev_config.temperature == 0.3
    
    def test_to_dict(self):
        """Test exporting configurations to dictionary."""
        manager = AgentModelManager(default_api_key="default-key")
        
        manager.configure_agent_model(
            AgentRole.CEO,
            AgentModelConfig(model="gpt-4", api_key="secret-key"),
        )
        manager.configure_agent_model(
            AgentRole.DEVELOPER,
            AgentModelConfig(model="gpt-3.5-turbo"),
        )
        
        exported = manager.to_dict()
        
        assert "ceo" in exported
        assert exported["ceo"]["model"] == "gpt-4"
        assert exported["ceo"]["api_key"] == "***"  # Should be masked
        
        assert "developer" in exported
        assert exported["developer"]["model"] == "gpt-3.5-turbo"


class TestLLMAgentWithModelConfig:
    """Tests for LLMAgent with model configuration."""
    
    def test_agent_with_model_config(self):
        """Test creating agent with model config."""
        config = AgentModelConfig(
            model="gpt-4-turbo",
            temperature=0.8,
            max_tokens=6000,
        )
        
        agent = LLMAgent(
            role=AgentRole.CTO,
            model_config=config,
            default_api_key="test-key",
        )
        
        assert agent.role == AgentRole.CTO
        assert agent.get_model_info()["model"] == "gpt-4-turbo"
        assert agent.get_model_info()["temperature"] == 0.8
    
    def test_agent_set_model_config(self):
        """Test setting model config on agent."""
        agent = LLMAgent(role=AgentRole.DEVELOPER)
        
        new_config = AgentModelConfig(
            model="gpt-4",
            temperature=0.3,
        )
        
        agent.set_model_config(new_config)
        
        assert agent.get_model_info()["model"] == "gpt-4"
        assert agent.get_model_info()["temperature"] == 0.3
    
    def test_agent_repr(self):
        """Test agent string representation."""
        config = AgentModelConfig(model="gpt-4")
        agent = LLMAgent(role=AgentRole.CEO, model_config=config)
        
        repr_str = repr(agent)
        
        assert "LLMAgent" in repr_str
        assert "ceo" in repr_str
        assert "gpt-4" in repr_str
