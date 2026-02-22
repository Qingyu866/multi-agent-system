"""
Agent definitions and system prompts.

智能体架构：
- 决策层: CEO, ADVISOR
- 管理层: CTO
- 执行层: 细分开发Agent
- 支撑层: QA_ENGINEER, DOCUMENTATION

细分Agent：
- Frontend Developer: 前端开发
- Backend Developer: 后端开发
- Fullstack Developer: 全栈开发
- Mobile Developer: 移动端开发
- DevOps Engineer: DevOps工程师
- Database Developer: 数据库开发
- UI/UX Designer: UI/UX设计师
"""

from multi_agent.agents.prompts import get_agent_config, get_all_agent_configs
from multi_agent.agents.sub_agents import (
    SUB_AGENT_CONFIGS,
    get_sub_agent_config,
    get_all_sub_agent_configs,
    FRONTEND_DEVELOPER_PROMPT,
    BACKEND_DEVELOPER_PROMPT,
    FULLSTACK_DEVELOPER_PROMPT,
    MOBILE_DEVELOPER_PROMPT,
    DEVOPS_ENGINEER_PROMPT,
    DATABASE_DEVELOPER_PROMPT,
    UI_UX_DESIGNER_PROMPT,
)
from multi_agent.agents.coordinator import (
    TaskAnalyzer,
    TaskRouter,
    ResultIntegrator,
    SubAgentCoordinator,
    TaskCategory,
    TaskComplexity,
    TaskAnalysis,
    AgentAssignment,
    IntegrationResult,
)

__all__ = [
    "get_agent_config",
    "get_all_agent_configs",
    "SUB_AGENT_CONFIGS",
    "get_sub_agent_config",
    "get_all_sub_agent_configs",
    "FRONTEND_DEVELOPER_PROMPT",
    "BACKEND_DEVELOPER_PROMPT",
    "FULLSTACK_DEVELOPER_PROMPT",
    "MOBILE_DEVELOPER_PROMPT",
    "DEVOPS_ENGINEER_PROMPT",
    "DATABASE_DEVELOPER_PROMPT",
    "UI_UX_DESIGNER_PROMPT",
    "TaskAnalyzer",
    "TaskRouter",
    "ResultIntegrator",
    "SubAgentCoordinator",
    "TaskCategory",
    "TaskComplexity",
    "TaskAnalysis",
    "AgentAssignment",
    "IntegrationResult",
]
