"""
Agent-specific model configuration example.

Demonstrates how to configure different models for different agents.
"""

import asyncio
import os
from multi_agent.core.types import AgentRole, AgentModelConfig, ModelProvider
from multi_agent.llm import LLMAgent, AgentModelManager, LLMClient


def demo_agent_model_config():
    """Demonstrate agent-specific model configuration."""
    
    print("=" * 60)
    print("Agent-Specific Model Configuration Demo")
    print("=" * 60)
    
    # 1. Create individual model configurations for each agent
    print("\n[1] Creating agent-specific model configurations...")
    
    ceo_model = AgentModelConfig(
        provider=ModelProvider.OPENAI,
        model="gpt-4",
        temperature=0.7,
        max_tokens=8000,
    )
    
    developer_model = AgentModelConfig(
        provider=ModelProvider.OPENAI,
        model="gpt-4",
        temperature=0.3,  # Lower temperature for code generation
        max_tokens=10000,
    )
    
    documentation_model = AgentModelConfig(
        provider=ModelProvider.OPENAI,
        model="gpt-3.5-turbo",  # Cheaper model for documentation
        temperature=0.5,
        max_tokens=6000,
    )
    
    print(f"  CEO: {ceo_model.model} (temp={ceo_model.temperature})")
    print(f"  Developer: {developer_model.model} (temp={developer_model.temperature})")
    print(f"  Documentation: {documentation_model.model} (temp={documentation_model.temperature})")
    
    # 2. Create agents with their specific models
    print("\n[2] Creating agents with specific models...")
    
    ceo_agent = LLMAgent(
        role=AgentRole.CEO,
        model_config=ceo_model,
        default_api_key=os.getenv("OPENAI_API_KEY"),
    )
    
    dev_agent = LLMAgent(
        role=AgentRole.DEVELOPER,
        model_config=developer_model,
        default_api_key=os.getenv("OPENAI_API_KEY"),
    )
    
    doc_agent = LLMAgent(
        role=AgentRole.DOCUMENTATION,
        model_config=documentation_model,
        default_api_key=os.getenv("OPENAI_API_KEY"),
    )
    
    print(f"  {ceo_agent}")
    print(f"  {dev_agent}")
    print(f"  {doc_agent}")
    
    # 3. Use AgentModelManager for centralized configuration
    print("\n[3] Using AgentModelManager for centralized management...")
    
    manager = AgentModelManager(default_api_key=os.getenv("OPENAI_API_KEY"))
    
    # Configure models for all agents
    manager.configure_agent_model(AgentRole.CEO, ceo_model)
    manager.configure_agent_model(AgentRole.CTO, AgentModelConfig(
        model="gpt-4",
        temperature=0.7,
        max_tokens=12000,
    ))
    manager.configure_agent_model(AgentRole.DEVELOPER, developer_model)
    manager.configure_agent_model(AgentRole.QA_ENGINEER, AgentModelConfig(
        model="gpt-4",
        temperature=0.5,
        max_tokens=8000,
    ))
    manager.configure_agent_model(AgentRole.DESIGNER, AgentModelConfig(
        model="gpt-4",
        temperature=0.8,  # Higher temperature for creative work
        max_tokens=8000,
    ))
    manager.configure_agent_model(AgentRole.DOCUMENTATION, documentation_model)
    
    # Export configuration
    config_export = manager.to_dict()
    print("\n  Exported configuration:")
    for role, config in config_export.items():
        print(f"    {role}: {config['model']} (temp={config['temperature']})")
    
    # 4. Create agents from manager
    print("\n[4] Creating agents from manager...")
    
    cto_agent = manager.create_agent(AgentRole.CTO)
    print(f"  Created: {cto_agent}")
    
    # 5. Load configuration from dictionary
    print("\n[5] Loading configuration from dictionary...")
    
    config_dict = {
        "ceo": {
            "provider": "openai",
            "model": "gpt-4-turbo",
            "temperature": 0.7,
            "max_tokens": 8000,
        },
        "advisor": {
            "provider": "openai",
            "model": "gpt-4",
            "temperature": 0.5,
            "max_tokens": 16000,
        },
        "developer": {
            "provider": "openai",
            "model": "gpt-4",
            "temperature": 0.3,
            "max_tokens": 10000,
        },
    }
    
    new_manager = AgentModelManager(default_api_key="test-key")
    new_manager.load_from_dict(config_dict)
    
    print("  Loaded configurations:")
    for role, config in new_manager.to_dict().items():
        print(f"    {role}: {config['model']}")
    
    # 6. Dynamic model switching
    print("\n[6] Dynamic model switching...")
    
    agent = LLMAgent(role=AgentRole.DEVELOPER)
    print(f"  Initial: {agent}")
    
    # Switch to a different model
    agent.set_model_config(AgentModelConfig(
        model="gpt-4-turbo",
        temperature=0.2,
    ))
    print(f"  After switch: {agent}")
    
    print("\n" + "=" * 60)
    print("Demo completed!")
    print("=" * 60)


def demo_azure_configuration():
    """Demonstrate Azure OpenAI configuration for specific agents."""
    
    print("\n" + "=" * 60)
    print("Azure OpenAI Configuration Demo")
    print("=" * 60)
    
    # Configure CEO to use Azure OpenAI
    ceo_azure_config = AgentModelConfig(
        provider=ModelProvider.AZURE,
        model="gpt-4",
        azure_endpoint="https://your-resource.openai.azure.com/",
        azure_deployment="gpt-4-deployment",
        api_version="2024-02-01",
        temperature=0.7,
        max_tokens=8000,
    )
    
    # Other agents use standard OpenAI
    dev_openai_config = AgentModelConfig(
        provider=ModelProvider.OPENAI,
        model="gpt-4",
        temperature=0.3,
        max_tokens=10000,
    )
    
    print("\nCEO Agent Configuration:")
    print(f"  Provider: {ceo_azure_config.provider.value}")
    print(f"  Model: {ceo_azure_config.model}")
    print(f"  Azure Endpoint: {ceo_azure_config.azure_endpoint}")
    
    print("\nDeveloper Agent Configuration:")
    print(f"  Provider: {dev_openai_config.provider.value}")
    print(f"  Model: {dev_openai_config.model}")
    
    print("\n" + "=" * 60)


def demo_model_info():
    """Demonstrate getting model information."""
    
    print("\n" + "=" * 60)
    print("Model Information Demo")
    print("=" * 60)
    
    configs = {
        AgentRole.CEO: AgentModelConfig(model="gpt-4", temperature=0.7, max_tokens=8000),
        AgentRole.ADVISOR: AgentModelConfig(model="gpt-4", temperature=0.5, max_tokens=16000),
        AgentRole.CTO: AgentModelConfig(model="gpt-4", temperature=0.7, max_tokens=12000),
        AgentRole.DEVELOPER: AgentModelConfig(model="gpt-4", temperature=0.3, max_tokens=10000),
        AgentRole.QA_ENGINEER: AgentModelConfig(model="gpt-4", temperature=0.5, max_tokens=8000),
        AgentRole.DESIGNER: AgentModelConfig(model="gpt-4", temperature=0.8, max_tokens=8000),
        AgentRole.DOCUMENTATION: AgentModelConfig(model="gpt-3.5-turbo", temperature=0.5, max_tokens=6000),
    }
    
    print("\nAgent Model Configurations:")
    print("-" * 60)
    print(f"{'Role':<15} {'Model':<20} {'Temp':<8} {'Max Tokens':<12}")
    print("-" * 60)
    
    for role, config in configs.items():
        print(f"{role.value:<15} {config.model:<20} {config.temperature:<8} {config.max_tokens:<12}")
    
    print("-" * 60)
    print("\n" + "=" * 60)


if __name__ == "__main__":
    demo_agent_model_config()
    demo_azure_configuration()
    demo_model_info()
