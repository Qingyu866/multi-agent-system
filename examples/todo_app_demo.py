"""
待办App多智能体协作示例

演示如何使用多智能体系统开发一个简单的待办事项应用。
"""

import asyncio
import os
from datetime import datetime

# 设置环境变量（实际使用时应该放在 .env 文件中）
os.environ.setdefault("OPENAI_API_KEY", "your-api-key-here")
os.environ.setdefault("OPENAI_MODEL", "gpt-4")

from multi_agent import MultiAgentSystem, ProjectContext, AgentRole, AgentMessage, MessageType
from multi_agent.llm import LLMClient, LLMAgent
from multi_agent.config import config


async def run_todo_app_demo():
    """运行待办App开发演示。"""
    
    print("=" * 60)
    print("多智能体协作系统 - 待办App开发演示")
    print("=" * 60)
    
    # 验证配置
    errors = config.validate()
    if errors:
        print("\n配置错误:")
        for error in errors:
            print(f"  - {error}")
        print("\n请设置 OPENAI_API_KEY 环境变量")
        return
    
    # 1. 创建项目上下文
    print("\n[1/6] 创建项目...")
    project = ProjectContext(
        name="待办事项应用",
        description="一个简洁的待办事项管理应用",
        requirements=[
            "用户可以添加、编辑、删除待办事项",
            "支持标记完成状态",
            "支持设置优先级",
            "数据需要持久化存储",
            "支持按状态筛选",
        ],
        scope_boundaries=[
            "不支持多用户协作",
            "不支持云端同步",
            "不支持提醒通知",
        ],
    )
    
    # 2. 初始化多智能体系统
    print("[2/6] 初始化多智能体系统...")
    system = MultiAgentSystem(
        project_context=project,
        chroma_persist_dir="./chroma_db_todo",
    )
    
    # 3. CEO Agent 制定战略
    print("\n[3/6] CEO Agent 制定项目战略...")
    ceo_agent = LLMAgent(role=AgentRole.CEO)
    
    ceo_message = AgentMessage(
        sender=AgentRole.CEO,
        receiver=AgentRole.CTO,
        message_type=MessageType.TASK_ASSIGNMENT,
        content="请为待办事项应用制定技术方案和任务分配",
    )
    
    # 存储消息到CTO的上下文
    await system.send_message(ceo_message)
    
    # 4. CTO Agent 制定技术方案
    print("\n[4/6] CTO Agent 制定技术方案...")
    cto_agent = LLMAgent(role=AgentRole.CTO)
    
    tech_plan = await cto_agent.generate_task_plan(
        requirements="\n".join(project.requirements),
        constraints=project.scope_boundaries,
    )
    
    print("\n技术方案:")
    print(f"  - 任务分解: {len(tech_plan.get('tasks', []))} 个子任务")
    print(f"  - 复杂度: {tech_plan.get('complexity', 'medium')}")
    
    # 5. 创建开发任务
    print("\n[5/6] 创建开发任务...")
    
    tasks = [
        ("设计数据模型", "定义待办事项的数据结构", "high"),
        ("实现CRUD功能", "添加、读取、更新、删除操作", "high"),
        ("实现筛选功能", "按状态筛选待办事项", "medium"),
        ("实现UI界面", "设计用户界面", "medium"),
        ("编写测试", "单元测试和集成测试", "medium"),
    ]
    
    created_tasks = []
    for title, desc, priority in tasks:
        task = system.create_task(
            title=title,
            description=desc,
            created_by=AgentRole.CTO,
            priority=priority,
        )
        created_tasks.append(task)
        print(f"  ✓ 创建任务: {title} ({priority})")
    
    # 6. Developer Agent 实现功能
    print("\n[6/6] Developer Agent 实现核心功能...")
    dev_agent = LLMAgent(role=AgentRole.DEVELOPER)
    
    # 模拟开发过程
    sample_code = '''
class TodoItem:
    def __init__(self, title, priority="medium"):
        self.title = title
        self.priority = priority
        self.completed = False
        self.created_at = datetime.now()
    
    def mark_complete(self):
        self.completed = True
    
    def mark_incomplete(self):
        self.completed = False

class TodoApp:
    def __init__(self):
        self.items = []
    
    def add_item(self, title, priority="medium"):
        item = TodoItem(title, priority)
        self.items.append(item)
        return item
    
    def get_items(self, filter_status=None):
        if filter_status is None:
            return self.items
        return [item for item in self.items 
                if item.completed == (filter_status == "completed")]
'''
    
    # 模拟代码审查
    print("\n  提交代码进行审查...")
    review_result = await dev_agent.review_code(
        code=sample_code,
        context="待办事项应用的核心数据模型",
    )
    
    print(f"  代码质量评分: {review_result.get('quality_score', 0)}/10")
    
    issues = review_result.get('issues', [])
    if issues:
        print(f"  发现 {len(issues)} 个问题:")
        for issue in issues[:3]:
            print(f"    - {issue}")
    else:
        print("  未发现明显问题")
    
    # 7. 系统状态报告
    print("\n" + "=" * 60)
    print("系统状态报告")
    print("=" * 60)
    
    status = system.get_system_status()
    print(f"\n项目: {status['project']['name']}")
    print(f"活跃任务: {status['project']['active_tasks']}")
    print(f"已完成任务: {status['project']['completed_tasks']}")
    print(f"\n已注册智能体: {len(status['agents'])}")
    for role, info in status['agents'].items():
        print(f"  - {role}: {info['name']}")
    
    print(f"\n活跃临时权限: {status['active_temp_permissions']}")
    print(f"活跃警报: {status['alerts']['total_active']}")
    
    # 8. 权限矩阵展示
    print("\n" + "=" * 60)
    print("权限矩阵")
    print("=" * 60)
    
    matrix = system.permission_guard.get_permission_matrix()
    for role, targets in matrix.items():
        targets_str = ", ".join(targets) if targets else "无"
        print(f"\n{role}:")
        print(f"  可通信对象: {targets_str}")
    
    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)


async def demo_permission_control():
    """演示权限控制功能。"""
    print("\n" + "=" * 60)
    print("权限控制演示")
    print("=" * 60)
    
    project = ProjectContext(
        name="权限测试",
        description="测试权限控制",
    )
    system = MultiAgentSystem(project_context=project)
    
    # 测试有效通信
    print("\n测试有效通信 (CEO -> CTO):")
    valid_message = AgentMessage(
        sender=AgentRole.CEO,
        receiver=AgentRole.CTO,
        message_type=MessageType.TASK_ASSIGNMENT,
        content="请分配开发任务",
    )
    result = await system.send_message(valid_message)
    print(f"  结果: {'✓ 允许' if result else '✗ 拒绝'}")
    
    # 测试无效通信
    print("\n测试无效通信 (Developer -> QA):")
    invalid_message = AgentMessage(
        sender=AgentRole.DEVELOPER,
        receiver=AgentRole.QA_ENGINEER,
        message_type=MessageType.TASK_ASSIGNMENT,
        content="请测试我的代码",
    )
    result = await system.send_message(invalid_message)
    print(f"  结果: {'✓ 允许' if result else '✗ 拒绝'}")
    
    # 测试临时权限
    print("\n测试临时权限 (CTO 授予 Developer -> QA 权限):")
    perm_id = await system.request_temporary_permission(
        requester=AgentRole.CTO,
        target_role=AgentRole.QA_ENGINEER,
        permission_type="direct_qa_access",
        reason="紧急Bug修复需要直接测试",
        granted_to=AgentRole.DEVELOPER,
    )
    print(f"  临时权限ID: {perm_id}")
    
    if perm_id:
        print("  ✓ 权限已授予 Developer")
    
    # 查看违规记录
    violations = system.permission_guard.get_violation_log()
    if violations:
        print(f"\n权限违规记录 ({len(violations)} 条):")
        for v in violations[-3:]:
            print(f"  - {v['agent']} 尝试访问 {v['target']}")


async def demo_loop_detection():
    """演示死循环检测功能。"""
    print("\n" + "=" * 60)
    print("死循环检测演示")
    print("=" * 60)
    
    project = ProjectContext(
        name="循环检测测试",
        description="测试循环检测",
    )
    system = MultiAgentSystem(project_context=project)
    
    # 创建任务
    task = system.create_task(
        title="循环测试任务",
        description="测试任务循环",
        created_by=AgentRole.CTO,
    )
    
    print(f"\n任务ID: {task.id}")
    print("模拟任务流转: CTO -> Developer -> QA -> CTO (重复4次)")
    
    # 模拟循环
    flow = [
        (AgentRole.CTO, AgentRole.DEVELOPER),
        (AgentRole.DEVELOPER, AgentRole.QA_ENGINEER),
        (AgentRole.QA_ENGINEER, AgentRole.CTO),
    ]
    
    loop_detected = False
    for i in range(4):
        for from_agent, to_agent in flow:
            message = AgentMessage(
                sender=from_agent,
                receiver=to_agent,
                message_type=MessageType.TASK_UPDATE,
                content=f"Iteration {i+1}",
                task_id=task.id,
            )
            result = await system.send_message(message)
            if not result:
                loop_detected = True
                print(f"\n  ⚠ 第 {i+1} 轮检测到循环!")
                break
        if loop_detected:
            break
    
    if not loop_detected:
        print("\n  未检测到循环")
    
    # 查看循环状态
    loop_status = system.loop_detector.get_loop_status(str(task.id))
    if loop_status:
        print(f"\n循环状态:")
        print(f"  模式: {' -> '.join(loop_status['pattern'])}")
        print(f"  发生次数: {loop_status['occurrences']}")


if __name__ == "__main__":
    # 运行演示
    asyncio.run(run_todo_app_demo())
    asyncio.run(demo_permission_control())
    asyncio.run(demo_loop_detection())
