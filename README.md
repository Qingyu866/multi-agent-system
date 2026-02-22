# Multi-Agent Collaboration System

A highly realistic software company simulation with hierarchical agent architecture.

## Features

- **Hierarchical Agent Architecture**: CEO, CTO, Developer, QA Engineer, Designer, Documentation, and Advisor roles
- **Dual-Track Memory System**: Short-term memory for each agent + Long-term memory with Chroma vector database
- **Permission Control**: Whitelist-based permission matrix for inter-agent communication
- **Temporary Authorization**: CTO can grant temporary bypass permissions for emergency situations
- **Loop Detection**: Automatic detection of task circulation patterns
- **Scope Monitoring**: Real-time detection of project scope drift
- **Advisor Committee**: Expert analysis and deadlock resolution

## Installation

```bash
pip install -e ".[dev]"
```

## Quick Start

```python
from multi_agent import MultiAgentSystem, ProjectContext

# Create a project
project = ProjectContext(
    name="My Project",
    description="A sample project",
    requirements=["Feature A", "Feature B"],
    scope_boundaries=["No Feature C"],
)

# Initialize the system
system = MultiAgentSystem(project_context=project)

# Create a task
task = system.create_task(
    title="Implement Feature A",
    description="Build the core functionality",
    created_by="ceo",
    priority="high",
)

# Check system status
status = system.get_system_status()
print(status)
```

## CLI Usage

```bash
# Initialize a project
multi-agent init --name "My Project" --description "Project description"

# Show system status
multi-agent status

# Create a task
multi-agent task create --title "New Feature" --description "Feature description"

# List agents
multi-agent agent list

# View permission matrix
multi-agent permission matrix
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      CEO Agent                          │
│           (Strategic Decision & Oversight)              │
└─────────────────────┬───────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
┌───────────┐  ┌───────────┐  ┌───────────┐
│   CTO     │  │  Advisor  │  │   Docs    │
│  Agent    │  │ Committee │  │   Agent   │
└─────┬─────┘  └───────────┘  └───────────┘
      │
      ├──────────┬──────────┐
      │          │          │
      ▼          ▼          ▼
┌─────────┐ ┌─────────┐ ┌─────────┐
│  Dev    │ │   QA    │ │Designer │
│ Agent   │ │ Engineer│ │ Agent   │
└─────────┘ └─────────┘ └─────────┘
```

## License

MIT
