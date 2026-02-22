# 多智能体协作系统使用指南

## 快速开始

### 1. 配置环境

复制环境变量模板并填写你的API密钥：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4
```

### 2. 基本使用

```python
import asyncio
from multi_agent import MultiAgentSystem, ProjectContext, AgentRole, AgentMessage, MessageType
from multi_agent.llm import LLMAgent

async def main():
    # 创建项目
    project = ProjectContext(
        name="我的项目",
        description="项目描述",
        requirements=["需求1", "需求2"],
        scope_boundaries=["范围限制1"],
    )
    
    # 初始化系统
    system = MultiAgentSystem(project_context=project)
    
    # 创建任务
    task = system.create_task(
        title="实现功能A",
        description="详细描述",
        created_by=AgentRole.CEO,
        priority="high",
    )
    
    # 使用LLM Agent
    cto_agent = LLMAgent(role=AgentRole.CTO)
    
    # 生成任务计划
    plan = await cto_agent.generate_task_plan(
        requirements="实现用户登录功能",
        constraints=["使用JWT认证"],
    )
    
    print(plan)

asyncio.run(main())
```

### 3. CLI 使用

```bash
# 查看系统状态
multi-agent status

# 列出所有Agent
multi-agent agent list

# 查看权限矩阵
multi-agent permission matrix

# 创建任务
multi-agent task create --title "新功能" --description "功能描述"
```

### 4. 运行示例

```bash
# 运行待办App演示
python examples/todo_app_demo.py
```

## 配置选项

### LLM 配置

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `OPENAI_API_KEY` | OpenAI API密钥 | 必填 |
| `OPENAI_BASE_URL` | API基础URL | https://api.openai.com/v1 |
| `OPENAI_MODEL` | 使用的模型 | gpt-4 |
| `LLM_TEMPERATURE` | 温度参数 | 0.7 |
| `LLM_MAX_TOKENS` | 最大token数 | 4000 |

### 内存配置

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `ENABLE_REDIS` | 启用Redis | false |
| `REDIS_URL` | Redis连接URL | redis://localhost:6379/0 |
| `CHROMA_PERSIST_DIR` | Chroma持久化目录 | ./chroma_db |

### 系统配置

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `MAX_ITERATIONS` | 最大任务迭代次数 | 3 |
| `DEFAULT_TEMP_PERMISSION_DURATION` | 临时权限默认时长(分钟) | 30 |
| `LOG_LEVEL` | 日志级别 | INFO |

## Agent 角色说明

| 角色 | 职责 | 可通信对象 |
|-----|------|-----------|
| CEO | 战略决策 | CTO, Advisor, Documentation |
| Advisor | 顾问咨询 | 被动响应 |
| CTO | 技术管理 | Developer, QA, Designer, Documentation |
| Developer | 开发实现 | Documentation |
| QA Engineer | 质量测试 | Documentation |
| Designer | 界面设计 | Documentation |
| Documentation | 文档管理 | 可被所有Agent调用 |

## 核心功能

### 1. 权限控制

```python
# 检查通信权限
result = system.permission_guard.validate_communication(
    sender=AgentRole.CEO,
    receiver=AgentRole.CTO,
)
print(result.allowed)  # True
```

### 2. 临时授权

```python
# CTO授予Developer临时访问QA的权限
perm_id = await system.request_temporary_permission(
    requester=AgentRole.CTO,
    target_role=AgentRole.QA_ENGINEER,
    permission_type="direct_qa_access",
    reason="紧急Bug修复",
    granted_to=AgentRole.DEVELOPER,
)
```

### 3. 死循环检测

```python
# 系统会自动检测任务循环
# 当同一任务在CTO->Developer->QA之间流转超过3次时触发警报
```

### 4. 范围监控

```python
# 监控内容是否偏离项目范围
is_drift, indicator = system.scope_monitor.check_content(
    content="我们顺便添加社交功能吧",
)
# is_drift = True (检测到范围偏离)
```

## API 参考

### MultiAgentSystem

- `create_task(title, description, created_by, priority)` - 创建任务
- `send_message(message)` - 发送消息
- `get_system_status()` - 获取系统状态
- `request_temporary_permission(...)` - 请求临时权限
- `escalate_to_advisor(task_id, context)` - 升级到顾问

### LLMAgent

- `process_message(message)` - 处理消息
- `generate_task_plan(requirements, constraints)` - 生成任务计划
- `review_code(code, context)` - 代码审查

## 注意事项

1. **API密钥安全**: 不要将 `.env` 文件提交到版本控制
2. **成本控制**: LLM调用会产生费用，注意监控使用量
3. **上下文限制**: 注意Agent的上下文长度限制
4. **权限边界**: 严格遵守权限矩阵，避免越权操作
