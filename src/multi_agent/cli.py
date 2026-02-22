"""
Enhanced CLI with code saving and Claude CLI integration.

完整工作流程：
1. 初始化 - 设置工作目录和项目结构
2. 代码生成 - Claude CLI在指定目录执行并保存文件
3. QA审查 - 根据审查标准检查代码
4. 修改循环 - 根据QA反馈修改代码（最多3轮）
5. 最终确认 - CEO确认代码质量
6. 部署准备 - 生成部署配置和文档
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Optional, Callable

from multi_agent.core.types import (
    AgentRole,
    AgentMessage,
    MessageType,
    ProjectContext,
    TaskContext,
    TaskStatus,
    TaskPriority,
)
from multi_agent.core.system import MultiAgentSystem
from multi_agent.llm import LLMAgent, AgentModelManager
from multi_agent.config import config
from multi_agent.codegen import (
    CodeManager,
    ClaudeCodeGenerator,
    ClaudeCLIConfig,
    check_claude_cli_available,
    WorkflowStage,
    WorkflowState,
    QAReviewCriteria,
)


class Colors:
    """ANSI color codes for terminal output."""
    
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    
    ROLE_COLORS = {
        AgentRole.CEO: MAGENTA,
        AgentRole.ADVISOR: YELLOW,
        AgentRole.CTO: CYAN,
        AgentRole.DEVELOPER: GREEN,
        AgentRole.FRONTEND_DEVELOPER: GREEN,
        AgentRole.BACKEND_DEVELOPER: BLUE,
        AgentRole.FULLSTACK_DEVELOPER: CYAN,
        AgentRole.MOBILE_DEVELOPER: MAGENTA,
        AgentRole.DEVOPS_ENGINEER: YELLOW,
        AgentRole.DATABASE_DEVELOPER: BLUE,
        AgentRole.QA_ENGINEER: BLUE,
        AgentRole.UI_UX_DESIGNER: RED,
        AgentRole.DOCUMENTATION: WHITE,
    }


def print_colored(text: str, color: str = Colors.WHITE) -> None:
    """Print colored text to terminal."""
    print(f"{color}{text}{Colors.RESET}")


def print_header(text: str) -> None:
    """Print a formatted header."""
    print()
    print_colored("=" * 60, Colors.BOLD)
    print_colored(f"  {text}", Colors.BOLD)
    print_colored("=" * 60, Colors.BOLD)


def print_agent_message(
    agent_role: AgentRole,
    message: str,
    message_type: str = "message",
) -> None:
    """Print a message from an agent with color coding."""
    color = Colors.ROLE_COLORS.get(agent_role, Colors.WHITE)
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    prefix_map = {
        "message": "💬",
        "task": "📋",
        "progress": "⏳",
        "complete": "✅",
        "error": "❌",
        "warning": "⚠️",
        "info": "ℹ️",
        "question": "❓",
        "file": "📄",
        "cli": "🔧",
    }
    
    prefix = prefix_map.get(message_type, "💬")
    
    print(f"{color}[{timestamp}] {prefix} {agent_role.value.upper():<12}{Colors.RESET} {message}")


def print_progress_bar(current: int, total: int, prefix: str = "") -> None:
    """Print a progress bar."""
    bar_length = 30
    filled = int(bar_length * current / total) if total > 0 else 0
    bar = "█" * filled + "░" * (bar_length - filled)
    percent = int(100 * current / total) if total > 0 else 0
    
    print(f"\r{prefix} [{bar}] {percent}% ({current}/{total})", end="", flush=True)


class ProjectSession:
    """
    Interactive project session with code saving and Claude CLI integration.
    
    完整工作流程：
    1. 初始化阶段 - 创建项目结构
    2. 开发阶段 - 代码生成、QA审查、修改循环
    3. 最终确认 - CEO确认代码质量
    4. 部署准备 - 生成部署配置
    """
    
    def __init__(
        self,
        project: ProjectContext,
        output_dir: str,
        verbose: bool = True,
        use_claude_cli: bool = True,
        qa_criteria: Optional[QAReviewCriteria] = None,
    ):
        self.project = project
        self.output_dir = output_dir
        self.verbose = verbose
        self.use_claude_cli = use_claude_cli
        self.system = MultiAgentSystem(project_context=project)
        
        self.code_manager = CodeManager(output_dir=output_dir)
        self.qa_criteria = qa_criteria or QAReviewCriteria()
        self.workflow_state = WorkflowState()
        
        self.model_manager = AgentModelManager(
            default_api_key=config.llm.api_key
        )
        self._load_agent_models()
        
        self.agents: dict[AgentRole, LLMAgent] = {}
        self.tasks: list[TaskContext] = []
        self.tech_stack: dict = {}
        self.all_generated_files: list[str] = []
        
        self.claude_generator: Optional[ClaudeCodeGenerator] = None
        if use_claude_cli:
            self._init_claude_cli()
    
    def _load_agent_models(self) -> None:
        """Load agent-specific model configurations."""
        for role, model_config in config.agent_models.items():
            self.model_manager.configure_agent_model(role, model_config)
    
    def _init_claude_cli(self) -> None:
        """Initialize Claude CLI integration with working directory."""
        available, info = check_claude_cli_available()
        
        if available:
            abs_output_dir = os.path.abspath(self.output_dir)
            
            cli_config = ClaudeCLIConfig(
                model=config.llm.model,
                max_tokens=100000,
                timeout=300,
                working_dir=abs_output_dir,
                auto_save=True,
            )
            self.claude_generator = ClaudeCodeGenerator(
                code_manager=self.code_manager,
                cli_config=cli_config,
                output_callback=self._claude_output_callback,
                qa_criteria=self.qa_criteria,
            )
            
            self.claude_generator.set_working_directory(abs_output_dir)
            
            print_agent_message(
                AgentRole.DEVELOPER,
                f"Claude CLI 已启用，工作目录: {abs_output_dir}",
                "cli",
            )
        else:
            print_agent_message(
                AgentRole.DEVELOPER,
                info,
                "warning",
            )
            self.use_claude_cli = False
    
    def _claude_output_callback(self, source: str, msg_type: str, message: str) -> None:
        """Handle output from Claude CLI."""
        if self.verbose:
            print_agent_message(AgentRole.DEVELOPER, message, msg_type)
    
    def _get_agent(self, role: AgentRole) -> LLMAgent:
        """Get or create an LLM agent."""
        if role not in self.agents:
            self.agents[role] = self.model_manager.create_agent(role)
        return self.agents[role]
    
    async def analyze_requirements(self, requirements: str) -> dict:
        """Analyze requirements and recommend tech stack."""
        print_header("需求分析")
        
        cto = self._get_agent(AgentRole.CTO)
        
        print_agent_message(
            AgentRole.CTO,
            "正在分析项目需求，推荐技术栈...",
            "progress",
        )
        
        tech_prompt = f"""分析以下项目需求，推荐合适的技术栈：

{requirements}

请用中文回复，格式如下：
## 推荐技术栈
**前端框架**: [推荐]
**后端框架**: [推荐]
**数据库**: [推荐]

## 推荐理由
[简要说明]
"""
        
        response = await cto.llm_client.generate_with_system_prompt(
            system_prompt="你是一个资深技术架构师，请用中文回复。",
            user_message=tech_prompt,
        )
        
        print()
        print_colored(response, Colors.CYAN)
        print()
        
        self.tech_stack = self._parse_tech_stack(response)
        
        return {
            "analysis": response,
            "tech_stack": self.tech_stack,
        }
    
    def _parse_tech_stack(self, response: str) -> dict:
        """Parse tech stack from response."""
        import re
        tech_stack = {}
        
        patterns = {
            "frontend": r"\*\*前端框架\*\*[：:]\s*(.+)",
            "backend": r"\*\*后端框架\*\*[：:]\s*(.+)",
            "database": r"\*\*数据库\*\*[：:]\s*(.+)",
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, response)
            if match:
                tech_stack[key] = match.group(1).strip()
        
        return tech_stack
    
    async def ask_for_clarification(
        self,
        requirements: str,
        interactive: bool = True,
    ) -> dict:
        """Ask user for additional information if needed."""
        if not interactive:
            return {"requirements": requirements, "tech_stack": self.tech_stack}
        
        print_header("需求确认")
        
        print_agent_message(
            AgentRole.CEO,
            "请确认以下信息，或按 Enter 使用推荐配置：",
            "question",
        )
        
        print()
        print_colored("当前需求：", Colors.YELLOW)
        print(f"  {requirements}")
        print()
        
        if self.tech_stack:
            print_colored("推荐技术栈：", Colors.YELLOW)
            for key, value in self.tech_stack.items():
                print(f"  - {key}: {value}")
            print()
        
        print_colored("选项：", Colors.YELLOW)
        print("  1. 按 Enter 使用当前配置继续")
        print("  2. 输入 'y' 确认并开始开发")
        print("  3. 输入补充需求或修改技术栈")
        print()
        
        try:
            user_input = input("请选择 [1/2/补充信息]: ").strip()
            
            if user_input.lower() == 'y' or user_input == '2':
                return {"requirements": requirements, "tech_stack": self.tech_stack}
            elif user_input and user_input != '1':
                return {
                    "requirements": f"{requirements}\n\n用户补充：{user_input}",
                    "tech_stack": self.tech_stack,
                }
            else:
                return {"requirements": requirements, "tech_stack": self.tech_stack}
        except EOFError:
            return {"requirements": requirements, "tech_stack": self.tech_stack}
    
    async def publish_requirements(
        self,
        requirements: str,
        scope_boundaries: Optional[list[str]] = None,
        tech_stack: Optional[dict] = None,
    ) -> dict:
        """Publish project requirements and create tasks."""
        print_header("发布项目需求")
        
        if scope_boundaries:
            self.project.scope_boundaries = scope_boundaries
        
        if tech_stack:
            self.tech_stack = tech_stack
        
        # Create project structure
        print_agent_message(
            AgentRole.CEO,
            f"创建项目结构: {self.output_dir}",
            "progress",
        )
        
        structure = self.code_manager.create_project_structure(
            self.project.name,
            self.tech_stack,
        )
        
        print_agent_message(
            AgentRole.CTO,
            f"项目结构已创建: {len(structure['directories'])} 个目录",
            "complete",
        )
        
        print_agent_message(
            AgentRole.CEO,
            "转发给 CTO 进行任务规划...",
            "progress",
        )
        
        cto = self._get_agent(AgentRole.CTO)
        
        print_colored("\n📊 CTO 正在创建任务计划...", Colors.CYAN)
        
        enhanced_requirements = requirements
        if self.tech_stack:
            tech_info = "\n".join([f"- {k}: {v}" for k, v in self.tech_stack.items()])
            enhanced_requirements = f"{requirements}\n\n技术栈配置：\n{tech_info}"
        
        plan = await cto.generate_task_plan(
            requirements=enhanced_requirements,
            constraints=scope_boundaries,
        )
        
        tasks = plan.get("tasks", [])
        if not tasks and plan.get("raw_response"):
            tasks = self._extract_tasks_from_response(plan.get("raw_response", ""))
        
        if isinstance(tasks, dict):
            tasks = list(tasks.values()) if tasks else []
        
        if not isinstance(tasks, list):
            tasks = [str(tasks)]
        
        print_agent_message(
            AgentRole.CTO,
            f"根据需求创建了 {len(tasks)} 个任务",
            "complete",
        )
        
        for i, task_desc in enumerate(tasks, 1):
            if isinstance(task_desc, dict):
                title = task_desc.get("title", task_desc.get("task", str(task_desc)))
            else:
                title = str(task_desc)
            
            task = self.system.create_task(
                title=title,
                description=title,
                created_by=AgentRole.CTO,
                priority="high" if i <= 3 else "medium",
            )
            self.tasks.append(task)
            
            if self.verbose:
                print_agent_message(
                    AgentRole.CTO,
                    f"任务 {i}: {title[:50]}{'...' if len(title) > 50 else ''}",
                    "task",
                )
        
        return {
            "project_id": str(self.project.id),
            "plan": plan,
            "tasks_created": len(self.tasks),
            "output_dir": self.output_dir,
        }
    
    def _extract_tasks_from_response(self, response: str) -> list[str]:
        """Extract tasks from raw LLM response."""
        tasks = []
        lines = response.split("\n")
        
        for line in lines:
            line = line.strip()
            if line.startswith(("- ", "* ", "• ", "1. ", "2. ", "3. ", "4. ", "5. ")):
                task = line.lstrip("- *•123456789. ").strip()
                if task and len(task) > 5:
                    tasks.append(task)
        
        return tasks if tasks else ["实现核心功能"]
    
    async def run_development_cycle(
        self,
        task_index: int = 0,
        interactive: bool = False,
        max_revision_rounds: int = 3,
    ) -> dict:
        """Run a development cycle for a specific task with QA feedback loop."""
        if task_index >= len(self.tasks):
            return {"error": "Task index out of range"}
        
        task = self.tasks[task_index]
        
        print_header(f"处理任务: {task.title}")
        
        print_agent_message(
            AgentRole.CEO,
            f"监控任务进度: {task.title}",
            "info",
        )
        
        print_agent_message(
            AgentRole.CTO,
            f"将任务分配给开发者: {task.title}",
            "progress",
        )
        
        context = {
            'tech_stack': self.tech_stack,
            'project_name': self.project.name,
            'requirements': self.project.requirements,
        }
        
        dev_response = ""
        saved_files = []
        qa_feedbacks = []
        revision_round = 0
        
        while revision_round <= max_revision_rounds:
            if revision_round == 0:
                dev_response, saved_files = await self._generate_code(
                    task, context, task_index, dev_response
                )
            else:
                print_agent_message(
                    AgentRole.CTO,
                    f"根据QA反馈进行第 {revision_round} 轮修改...",
                    "progress",
                )
                
                last_qa_feedback = qa_feedbacks[-1] if qa_feedbacks else ""
                dev_response, saved_files = await self._revise_code(
                    task, context, task_index, dev_response, last_qa_feedback
                )
            
            if self.verbose and dev_response:
                self._print_code_preview(dev_response, revision_round + 1)
            
            print_agent_message(
                AgentRole.CTO,
                "转发给 QA 进行审查...",
                "progress",
            )
            
            qa = self._get_agent(AgentRole.QA_ENGINEER)
            
            print_colored("\n🔍 QA 工程师正在审查...", Colors.BLUE)
            
            qa_response = await qa.process_message(AgentMessage(
                sender=AgentRole.CTO,
                receiver=AgentRole.QA_ENGINEER,
                message_type=MessageType.TASK_ASSIGNMENT,
                content=f"审查任务: {task.title}\n\n实现预览:\n{dev_response[:2000] if dev_response else 'N/A'}",
            ))
            
            qa_feedbacks.append(qa_response)
            
            print_agent_message(
                AgentRole.QA_ENGINEER,
                "审查完成",
                "complete",
            )
            
            if self.verbose:
                print_colored("\n📋 QA 审查结果:", Colors.BLUE)
                print("-" * 40)
                print(qa_response[:600] + ("..." if len(qa_response) > 600 else ""))
                print("-" * 40)
            
            needs_revision = self._check_needs_revision(qa_response)
            
            if not needs_revision:
                print_agent_message(
                    AgentRole.QA_ENGINEER,
                    "✅ 代码审查通过，无需修改",
                    "complete",
                )
                break
            
            if revision_round >= max_revision_rounds:
                print_agent_message(
                    AgentRole.CEO,
                    f"已达到最大修改轮次 ({max_revision_rounds})，继续下一任务",
                    "warning",
                )
                break
            
            print_agent_message(
                AgentRole.QA_ENGINEER,
                f"⚠️ 发现需要修改的问题，将进行第 {revision_round + 1} 轮修改",
                "warning",
            )
            
            revision_round += 1
        
        print_agent_message(
            AgentRole.CEO,
            f"任务完成确认: {task.title}",
            "complete",
        )
        
        task.status = TaskStatus.COMPLETED
        
        return {
            "task_id": str(task.id),
            "task_title": task.title,
            "status": "completed",
            "saved_files": saved_files,
            "implementation_preview": dev_response[:500] if dev_response else "",
            "qa_feedback": qa_feedbacks[-1][:300] if qa_feedbacks else "",
            "revision_rounds": revision_round,
            "all_qa_feedbacks": [f[:200] for f in qa_feedbacks],
        }
    
    async def _generate_code(
        self,
        task: TaskContext,
        context: dict,
        task_index: int,
        previous_code: str = "",
    ) -> tuple[str, list[str]]:
        """Generate code for a task."""
        if self.use_claude_cli and self.claude_generator:
            print_agent_message(
                AgentRole.DEVELOPER,
                "使用 Claude CLI 生成代码...",
                "cli",
            )
            
            result = await self.claude_generator.generate_code(
                task=task.title,
                context=context,
                task_name=f"task_{task_index + 1}",
            )
            
            if result['success']:
                dev_response = result['response']
                saved_files = result['saved_files']
                
                print_agent_message(
                    AgentRole.DEVELOPER,
                    f"代码生成完成，保存了 {len(saved_files)} 个文件",
                    "complete",
                )
                
                self._print_saved_files(saved_files)
                
                return dev_response, saved_files
            else:
                dev_response = f"代码生成失败: {result.get('error', 'Unknown error')}"
                print_agent_message(
                    AgentRole.DEVELOPER,
                    dev_response,
                    "error",
                )
                return dev_response, []
        else:
            developer = self._get_agent(AgentRole.DEVELOPER)
            
            tech_context = ""
            if self.tech_stack:
                tech_context = "\n\n技术栈配置：\n" + "\n".join([f"- {k}: {v}" for k, v in self.tech_stack.items()])
            
            task_prompt = f"""请实现以下任务，直接生成代码：

任务: {task.title}

项目背景: {self.project.description}
{tech_context}

要求：
1. 直接生成可运行的代码
2. 在代码块第一行注释标注文件路径
3. 使用 ```language 代码块格式
4. 用中文注释说明关键逻辑
"""
            
            print_colored("\n💻 开发者正在实现...", Colors.GREEN)
            
            dev_response = await developer.process_message(AgentMessage(
                sender=AgentRole.CTO,
                receiver=AgentRole.DEVELOPER,
                message_type=MessageType.TASK_ASSIGNMENT,
                content=task_prompt,
            ))
            
            saved_files = self.code_manager.save_from_response(
                dev_response,
                task_name=f"task_{task_index + 1}",
            )
            
            print_agent_message(
                AgentRole.DEVELOPER,
                f"实现完成，保存了 {len(saved_files)} 个文件",
                "complete",
            )
            
            self._print_saved_files(saved_files)
            
            return dev_response, saved_files
    
    async def _revise_code(
        self,
        task: TaskContext,
        context: dict,
        task_index: int,
        previous_code: str,
        qa_feedback: str,
    ) -> tuple[str, list[str]]:
        """Revise code based on QA feedback."""
        if self.use_claude_cli and self.claude_generator:
            print_agent_message(
                AgentRole.DEVELOPER,
                "使用 Claude CLI 修改代码...",
                "cli",
            )
            
            revise_prompt = f"""请根据QA反馈修改代码：

原始任务: {task.title}

QA反馈意见:
{qa_feedback}

请直接修改代码，解决QA提出的问题。保持原有功能的同时修复问题。
"""
            
            result = await self.claude_generator.generate_code(
                task=revise_prompt,
                context=context,
                task_name=f"task_{task_index + 1}_rev",
            )
            
            if result['success']:
                dev_response = result['response']
                saved_files = result['saved_files']
                
                print_agent_message(
                    AgentRole.DEVELOPER,
                    f"代码修改完成，保存了 {len(saved_files)} 个文件",
                    "complete",
                )
                
                self._print_saved_files(saved_files)
                
                return dev_response, saved_files
            else:
                print_agent_message(
                    AgentRole.DEVELOPER,
                    f"代码修改失败: {result.get('error', 'Unknown error')}",
                    "error",
                )
                return previous_code, []
        else:
            developer = self._get_agent(AgentRole.DEVELOPER)
            
            revise_prompt = f"""请根据QA反馈修改代码：

原始任务: {task.title}

QA反馈意见:
{qa_feedback}

当前代码预览:
{previous_code[:2000]}

要求：
1. 根据QA反馈修改代码
2. 保持原有功能
3. 在代码块第一行注释标注文件路径
4. 使用 ```language 代码块格式
"""
            
            print_colored("\n� 开发者正在根据QA反馈修改...", Colors.GREEN)
            
            dev_response = await developer.process_message(AgentMessage(
                sender=AgentRole.QA_ENGINEER,
                receiver=AgentRole.DEVELOPER,
                message_type=MessageType.TASK_ASSIGNMENT,
                content=revise_prompt,
            ))
            
            saved_files = self.code_manager.save_from_response(
                dev_response,
                task_name=f"task_{task_index + 1}_rev",
            )
            
            print_agent_message(
                AgentRole.DEVELOPER,
                f"修改完成，保存了 {len(saved_files)} 个文件",
                "complete",
            )
            
            self._print_saved_files(saved_files)
            
            return dev_response, saved_files
    
    def _check_needs_revision(self, qa_response: str) -> bool:
        """Check if QA response indicates need for revision."""
        revision_keywords = [
            "需要修改", "建议修改", "应该修改", "必须修改",
            "存在问题", "发现问题", "有错误", "有bug",
            "需要修复", "需要改进", "需要优化",
            "不正确", "不完整", "不符合",
            "建议：", "问题：", "缺陷：",
            "needs revision", "needs fix", "has issues",
            "should be", "must be", "incorrect",
        ]
        
        pass_keywords = [
            "通过", "合格", "符合要求", "没有问题",
            "审查通过", "代码质量良好", "可以接受",
            "passed", "approved", "looks good",
        ]
        
        qa_lower = qa_response.lower()
        
        for keyword in pass_keywords:
            if keyword.lower() in qa_lower:
                return False
        
        for keyword in revision_keywords:
            if keyword.lower() in qa_lower:
                return True
        
        return False
    
    def _print_code_preview(self, code: str, round_num: int = 1) -> None:
        """Print code preview with smart truncation and file info."""
        print_colored(f"\n📝 实现预览 (第{round_num}轮):", Colors.GREEN)
        print("-" * 60)
        
        max_preview_length = 2500
        code_blocks = self.code_manager.extract_code_blocks(code)
        
        if code_blocks:
            total_blocks = len(code_blocks)
            print_colored(f"📦 共 {total_blocks} 个代码块", Colors.CYAN)
            print()
            
            for i, block in enumerate(code_blocks[:5]):
                lang = block.get('language', 'text')
                block_code = block.get('code', '')
                path = block.get('path', '')
                
                if path:
                    print_colored(f"📄 文件: {path}", Colors.YELLOW)
                else:
                    print_colored(f"📄 代码块 {i+1} ({lang})", Colors.YELLOW)
                
                block_preview = block_code[:600]
                if len(block_code) > 600:
                    block_preview += f"\n... (还有 {len(block_code) - 600} 字符)"
                
                print(f"```{lang}")
                print(block_preview)
                print("```")
                print()
            
            if total_blocks > 5:
                print_colored(f"... 还有 {total_blocks - 5} 个代码块未显示", Colors.YELLOW)
        else:
            if len(code) > max_preview_length:
                print(code[:max_preview_length])
                print()
                print_colored(f"... (内容已截断，总长度 {len(code)} 字符)", Colors.YELLOW)
            else:
                print(code)
        
        print("-" * 60)
    
    def _print_saved_files(self, saved_files: list[str]) -> None:
        """Print saved files with full paths."""
        if not saved_files:
            return
        
        print()
        print_colored("📁 代码已保存到以下位置:", Colors.YELLOW)
        for file_path in saved_files:
            abs_path = os.path.abspath(file_path)
            print_colored(f"   ✅ {abs_path}", Colors.GREEN)
    
    async def run_full_project(self, interactive: bool = False, prepare_deployment: bool = True) -> dict:
        """Run the complete project workflow with deployment preparation."""
        print_header(f"运行项目: {self.project.name}")
        
        self.workflow_state.current_stage = WorkflowStage.INITIALIZATION
        
        total_tasks = len(self.tasks)
        completed = 0
        results = []
        all_files = []
        total_revisions = 0
        
        abs_output_dir = os.path.abspath(self.output_dir)
        
        print()
        print_colored("=" * 60, Colors.BOLD)
        print_colored(f"📁 项目输出目录: {abs_output_dir}", Colors.BOLD + Colors.YELLOW)
        print_colored("=" * 60, Colors.BOLD)
        print()
        print_colored(f"📋 总任务数: {total_tasks}", Colors.BOLD)
        print()
        
        self.workflow_state.current_stage = WorkflowStage.CODE_GENERATION
        
        for i, task in enumerate(self.tasks):
            print_progress_bar(completed, total_tasks, "开发进度")
            print()
            
            result = await self.run_development_cycle(i, interactive)
            results.append(result)
            
            if result.get('saved_files'):
                all_files.extend(result['saved_files'])
            
            total_revisions += result.get('revision_rounds', 0)
            
            completed += 1
            
            if interactive:
                print_colored("\n按 Enter 继续下一个任务...", Colors.YELLOW)
                try:
                    input()
                except EOFError:
                    pass
        
        print_progress_bar(completed, total_tasks, "开发进度")
        print("\n")
        
        self.workflow_state.current_stage = WorkflowStage.FINAL_CONFIRMATION
        
        print_header("✅ 最终确认")
        
        print_agent_message(
            AgentRole.CEO,
            "正在进行最终代码审查和确认...",
            "progress",
        )
        
        ceo = self._get_agent(AgentRole.CEO)
        
        final_review = await ceo.process_message(AgentMessage(
            sender=AgentRole.CTO,
            receiver=AgentRole.CEO,
            message_type=MessageType.TASK_ASSIGNMENT,
            content=f"""请对项目进行最终确认：

项目名称: {self.project.name}
总任务数: {total_tasks}
生成文件数: {len(all_files)}
修改轮次: {total_revisions}

请确认：
1. 所有任务是否完成
2. 代码质量是否达标
3. 是否可以进入部署准备阶段

回复 "确认通过" 或提出需要修改的问题。
""",
        ))
        
        print_agent_message(
            AgentRole.CEO,
            "最终确认完成",
            "complete",
        )
        
        if self.verbose:
            print_colored("\n📋 CEO 最终确认:", Colors.MAGENTA)
            print("-" * 40)
            print(final_review[:400] + ("..." if len(final_review) > 400 else ""))
            print("-" * 40)
        
        deployment_files = []
        
        if prepare_deployment:
            self.workflow_state.current_stage = WorkflowStage.DEPLOYMENT_PREP
            
            print_header("🚀 部署准备")
            
            print_agent_message(
                AgentRole.CTO,
                "正在生成部署配置文件...",
                "progress",
            )
            
            if self.use_claude_cli and self.claude_generator:
                deployment_result = await self.claude_generator.prepare_deployment(
                    project_name=self.project.name,
                    tech_stack=self.tech_stack,
                    generated_files=all_files,
                )
                
                if deployment_result['success']:
                    deployment_files = deployment_result['saved_files']
                    all_files.extend(deployment_files)
                    
                    print_agent_message(
                        AgentRole.CTO,
                        f"部署配置已生成，共 {len(deployment_files)} 个文件",
                        "complete",
                    )
                    
                    self._print_saved_files(deployment_files)
            else:
                deployment_files = await self._generate_deployment_files_fallback()
                all_files.extend(deployment_files)
        
        self.workflow_state.current_stage = WorkflowStage.COMPLETED
        self.all_generated_files = all_files
        
        print_header("🎉 项目完成")
        
        print_agent_message(
            AgentRole.CEO,
            f"所有 {total_tasks} 个任务已完成！",
            "complete",
        )
        
        print()
        print_colored("=" * 60, Colors.BOLD + Colors.GREEN)
        print_colored("📊 项目统计", Colors.BOLD + Colors.GREEN)
        print_colored("=" * 60, Colors.BOLD + Colors.GREEN)
        print()
        print(f"  📋 总任务数: {total_tasks}")
        print(f"  📄 生成文件数: {len(all_files)}")
        print(f"  🔄 总修改轮次: {total_revisions}")
        print(f"  🚀 部署文件数: {len(deployment_files)}")
        print()
        
        print_colored("=" * 60, Colors.BOLD + Colors.CYAN)
        print_colored("📁 代码保存位置", Colors.BOLD + Colors.CYAN)
        print_colored("=" * 60, Colors.BOLD + Colors.CYAN)
        print()
        print_colored(f"  项目根目录: {abs_output_dir}", Colors.YELLOW)
        print()
        
        if all_files:
            print_colored("  已生成的文件:", Colors.GREEN)
            unique_files = list(dict.fromkeys(all_files))
            for f in unique_files[:15]:
                abs_path = os.path.abspath(f)
                print_colored(f"    ✅ {abs_path}", Colors.GREEN)
            if len(unique_files) > 15:
                print_colored(f"    ... 还有 {len(unique_files) - 15} 个文件", Colors.YELLOW)
            if len(unique_files) < len(all_files):
                print_colored(f"    (共 {len(all_files)} 个文件版本)", Colors.YELLOW)
        
        print()
        print_colored("=" * 60, Colors.BOLD)
        print_colored("💡 提示: 你可以使用以下命令查看生成的代码", Colors.YELLOW)
        print_colored(f"   cd {abs_output_dir}", Colors.WHITE)
        print_colored(f"   ls -la", Colors.WHITE)
        print_colored("=" * 60, Colors.BOLD)
        print()
        
        return {
            "project_id": str(self.project.id),
            "total_tasks": total_tasks,
            "completed_tasks": completed,
            "total_files": len(all_files),
            "total_revisions": total_revisions,
            "deployment_files": len(deployment_files),
            "saved_files": all_files,
            "output_dir": abs_output_dir,
            "results": results,
            "workflow_stage": self.workflow_state.current_stage.value,
        }
    
    async def _generate_deployment_files_fallback(self) -> list[str]:
        """Fallback method to generate deployment files without Claude CLI."""
        deployment_files = []
        
        requirements_content = """# 项目依赖
# 由多智能体系统自动生成

# 后端依赖
fastapi>=0.100.0
uvicorn>=0.22.0
pydantic>=2.0.0

# 数据库
sqlalchemy>=2.0.0

# 工具库
python-dotenv>=1.0.0
"""
        
        req_path = self.code_manager.save_code_block(
            code=requirements_content,
            language="text",
            filename="requirements.txt",
            description="Python依赖列表",
        )
        deployment_files.append(req_path)
        
        env_example = """# 环境变量配置
# 复制此文件为 .env 并填入实际值

# 应用配置
APP_NAME=MyApp
APP_ENV=development
APP_DEBUG=true

# 数据库配置
DATABASE_URL=sqlite:///./app.db

# API配置
API_HOST=0.0.0.0
API_PORT=8000
"""
        
        env_path = self.code_manager.save_code_block(
            code=env_example,
            language="text",
            filename=".env.example",
            description="环境变量模板",
        )
        deployment_files.append(env_path)
        
        readme_content = f"""# {self.project.name}

{self.project.description if self.project.description else 'Generated by Multi-Agent System'}

## Tech Stack
- Frontend: {self.tech_stack.get('frontend', 'Not specified')}
- Backend: {self.tech_stack.get('backend', 'Not specified')}
- Database: {self.tech_stack.get('database', 'Not specified')}

## Getting Started

```bash
# Navigate to project directory
cd {self.output_dir}

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

---
*Generated by Multi-Agent System*
"""
        
        readme_path = self.code_manager.save_code_block(
            code=readme_content,
            language="markdown",
            filename="README.md",
            description="项目说明文档",
        )
        deployment_files.append(readme_path)
        
        return deployment_files


def create_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="multi-agent",
        description="多智能体协作系统 CLI",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    run_parser = subparsers.add_parser(
        "run",
        help="运行新项目",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基本运行
  multi-agent run --name "我的应用" -r "构建一个待办应用"
  
  # 指定输出目录
  multi-agent run --name "我的应用" -r "..." -o ./my-project
  
  # 交互模式
  multi-agent run --name "我的应用" -r "..." --interactive
  
  # 指定技术栈
  multi-agent run --name "我的应用" -r "..." --tech-frontend React --tech-backend FastAPI
        """,
    )
    run_parser.add_argument("--name", required=True, help="项目名称")
    run_parser.add_argument("--requirements", "-r", help="项目需求描述")
    run_parser.add_argument("--file", "-f", help="包含需求的文件")
    run_parser.add_argument("--output", "-o", default="./output", help="输出目录 (默认: ./output)")
    run_parser.add_argument("--scope", nargs="*", default=[], help="范围边界")
    run_parser.add_argument("--interactive", "-i", action="store_true", help="交互模式")
    run_parser.add_argument("--verbose", "-v", action="store_true", default=True, help="详细输出")
    run_parser.add_argument("--tech-frontend", help="前端技术栈")
    run_parser.add_argument("--tech-backend", help="后端技术栈")
    run_parser.add_argument("--tech-database", help="数据库")
    run_parser.add_argument("--skip-analysis", action="store_true", help="跳过需求分析")
    run_parser.add_argument("--no-claude-cli", action="store_true", help="禁用 Claude CLI")
    
    init_parser = subparsers.add_parser("init", help="初始化新项目")
    init_parser.add_argument("--name", required=True, help="项目名称")
    init_parser.add_argument("--output", "-o", default="./output", help="输出目录")
    
    status_parser = subparsers.add_parser("status", help="显示系统状态")
    
    task_parser = subparsers.add_parser("task", help="任务管理")
    task_parser.add_argument("action", choices=["create", "list", "show"])
    task_parser.add_argument("--title", help="任务标题")
    task_parser.add_argument("--description", help="任务描述")
    task_parser.add_argument("--priority", choices=["critical", "high", "medium", "low"], default="medium")
    
    agent_parser = subparsers.add_parser("agent", help="智能体管理")
    agent_parser.add_argument("action", choices=["list", "models"])
    agent_parser.add_argument("--role", choices=[r.value for r in AgentRole])
    
    config_parser = subparsers.add_parser("config", help="配置管理")
    config_parser.add_argument("action", choices=["show", "models", "validate"])
    
    resume_parser = subparsers.add_parser(
        "resume",
        help="恢复中断的项目",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 查看可恢复的项目列表
  multi-agent resume --list
  
  # 检查项目状态
  multi-agent resume --check ./output/my-project
  
  # 恢复项目执行
  multi-agent resume ./output/my-project
  
  # 从指定检查点恢复
  multi-agent resume ./output/my-project --checkpoint cp_20240101_120000
        """,
    )
    resume_parser.add_argument("project_dir", nargs="?", help="项目目录")
    resume_parser.add_argument("--list", action="store_true", help="列出可恢复的项目")
    resume_parser.add_argument("--check", action="store_true", help="检查项目恢复状态")
    resume_parser.add_argument("--status", action="store_true", help="显示项目详细状态")
    resume_parser.add_argument("--checkpoint", help="从指定检查点恢复")
    resume_parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    
    return parser


def print_json(data: dict) -> None:
    """Print data as formatted JSON."""
    print(json.dumps(data, indent=2, default=str, ensure_ascii=False))


async def handle_run(args: argparse.Namespace) -> None:
    """Handle the run command."""
    requirements = args.requirements or ""
    
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                requirements = f.read()
        except FileNotFoundError:
            print_colored(f"错误: 文件未找到: {args.file}", Colors.RED)
            return
    
    if not requirements:
        print_colored("错误: 请通过 --requirements 或 --file 提供需求", Colors.RED)
        return
    
    errors = config.validate()
    if errors:
        print_colored("配置错误:", Colors.RED)
        for error in errors:
            print_colored(f"  - {error}", Colors.RED)
        return
    
    output_dir = os.path.join(args.output, args.name.replace(" ", "_"))
    abs_output_dir = os.path.abspath(output_dir)
    
    project = ProjectContext(
        name=args.name,
        description=requirements[:200],
        requirements=[requirements],
        scope_boundaries=args.scope,
    )
    
    use_claude_cli = not args.no_claude_cli
    
    session = ProjectSession(
        project=project,
        output_dir=output_dir,
        verbose=args.verbose,
        use_claude_cli=use_claude_cli,
    )
    
    print_header(f"启动项目: {args.name}")
    
    print()
    print_colored("=" * 60, Colors.BOLD + Colors.CYAN)
    print_colored("📁 代码将保存到:", Colors.BOLD + Colors.CYAN)
    print_colored(f"   {abs_output_dir}", Colors.YELLOW)
    print_colored("=" * 60, Colors.BOLD + Colors.CYAN)
    print()
    
    print_colored(f"📄 需求描述:\n{requirements[:500]}{'...' if len(requirements) > 500 else ''}\n", Colors.WHITE)
    
    if args.scope:
        print_colored(f"🎯 范围边界:\n{chr(10).join('- ' + s for s in args.scope)}\n", Colors.YELLOW)
    
    tech_stack = {}
    if args.tech_frontend:
        tech_stack["frontend"] = args.tech_frontend
    if args.tech_backend:
        tech_stack["backend"] = args.tech_backend
    if args.tech_database:
        tech_stack["database"] = args.tech_database
    
    try:
        if not args.skip_analysis:
            analysis = await session.analyze_requirements(requirements)
            
            if args.interactive:
                clarified = await session.ask_for_clarification(requirements, interactive=True)
                requirements = clarified["requirements"]
                if clarified.get("tech_stack"):
                    tech_stack.update(clarified["tech_stack"])
        
        if tech_stack:
            session.tech_stack = tech_stack
        
        plan_result = await session.publish_requirements(
            requirements,
            args.scope,
            tech_stack if tech_stack else None,
        )
        
        print_colored(f"\n✅ 创建了 {plan_result['tasks_created']} 个任务\n", Colors.GREEN)
        
        if args.interactive:
            print_colored("按 Enter 开始开发...", Colors.YELLOW)
            try:
                input()
            except EOFError:
                pass
        
        result = await session.run_full_project(interactive=args.interactive)
        
        print_colored("\n📊 最终结果:", Colors.BOLD)
        print_json({
            "project_id": result["project_id"],
            "total_tasks": result["total_tasks"],
            "total_files": result["total_files"],
            "total_revisions": result.get("total_revisions", 0),
            "output_dir": result["output_dir"],
        })
        
    except Exception as e:
        print_colored(f"\n❌ 错误: {str(e)}", Colors.RED)
        raise


async def handle_init(args: argparse.Namespace) -> None:
    """Handle the init command."""
    output_dir = os.path.join(args.output, args.name.replace(" ", "_"))
    
    code_manager = CodeManager(output_dir=output_dir)
    structure = code_manager.create_project_structure(args.name, {})
    
    print_json({
        "message": "项目初始化成功",
        "output_dir": output_dir,
        "directories": structure["directories"],
    })


async def handle_status(args: argparse.Namespace) -> None:
    """Handle the status command."""
    available, info = check_claude_cli_available()
    
    print_json({
        "claude_cli": {
            "available": available,
            "info": info,
        },
        "config": {
            "model": config.llm.model,
            "base_url": config.llm.base_url,
        },
    })


async def handle_task(args: argparse.Namespace) -> None:
    """Handle the task command."""
    print_json({"message": "请使用 'run' 命令创建和管理任务"})


async def handle_agent(args: argparse.Namespace) -> None:
    """Handle the agent command."""
    if args.action == "list":
        agents = [
            {"role": role.value, "name": role.value.upper()}
            for role in AgentRole
        ]
        print_json({"agents": agents})
    elif args.action == "models":
        summary = config.get_all_agent_configs_summary()
        print_json({"agent_models": summary})


async def handle_config(args: argparse.Namespace) -> None:
    """Handle the config command."""
    if args.action == "show":
        agent_models = config.get_all_agent_configs_summary()
        print_json({
            "llm": {
                "provider": config.llm.provider,
                "model": config.llm.model,
                "base_url": config.llm.base_url,
            },
            "agent_models": agent_models,
        })
    elif args.action == "models":
        summary = config.get_all_agent_configs_summary()
        print_json({"agent_models": summary})
    elif args.action == "validate":
        errors = config.validate()
        print_json({"valid": len(errors) == 0, "errors": errors})


async def handle_resume(args: argparse.Namespace) -> None:
    """Handle the resume command - 恢复中断的项目."""
    from multi_agent.recovery import (
        StatePersistence,
        ErrorRecovery,
        ProjectResumer,
        ProjectStatus,
    )
    
    if args.list:
        print_header("可恢复的项目列表")
        
        output_dir = Path("./output")
        if not output_dir.exists():
            print_colored("没有找到输出目录", Colors.YELLOW)
            return
        
        resumable_projects = []
        for project_dir in output_dir.iterdir():
            if not project_dir.is_dir():
                continue
            
            state_file = project_dir / ".multi_agent_state" / "project_state.json"
            if not state_file.exists():
                continue
            
            persistence = StatePersistence(str(project_dir))
            state = persistence.load_state()
            
            if state and state.status in [ProjectStatus.INTERRUPTED, ProjectStatus.PAUSED]:
                resume_info = persistence.get_resume_info()
                resumable_projects.append({
                    "path": str(project_dir),
                    "name": state.project_name,
                    "status": state.status.value,
                    "interrupt_reason": resume_info.get("interrupt_reason"),
                    "current_task": resume_info.get("current_task_index", 0),
                    "total_tasks": resume_info.get("total_tasks", 0),
                })
        
        if not resumable_projects:
            print_colored("没有可恢复的项目", Colors.YELLOW)
            return
        
        for proj in resumable_projects:
            print_colored(f"\n📁 {proj['name']}", Colors.BOLD + Colors.CYAN)
            print_colored(f"   路径: {proj['path']}", Colors.WHITE)
            print_colored(f"   状态: {proj['status']}", Colors.YELLOW)
            print_colored(f"   中断原因: {proj['interrupt_reason'] or '未知'}", Colors.RED)
            print_colored(f"   进度: {proj['current_task']}/{proj['total_tasks']}", Colors.GREEN)
        
        print_colored(f"\n使用 'multi-agent resume <项目路径>' 恢复项目", Colors.CYAN)
        return
    
    if not args.project_dir:
        print_colored("错误: 请指定项目目录或使用 --list 查看可恢复项目", Colors.RED)
        return
    
    project_dir = Path(args.project_dir)
    if not project_dir.exists():
        print_colored(f"错误: 项目目录不存在: {project_dir}", Colors.RED)
        return
    
    persistence = StatePersistence(str(project_dir))
    recovery = ErrorRecovery(persistence)
    resumer = ProjectResumer(persistence, recovery)
    
    if args.check or args.status:
        check_result = resumer.check_resumable()
        
        print_header(f"项目状态: {check_result.get('project_name', '未知')}")
        
        if check_result.get("resumable"):
            print_colored(f"✅ 可以恢复", Colors.GREEN)
            print_colored(f"   项目ID: {check_result.get('project_id')}", Colors.WHITE)
            print_colored(f"   当前任务: {check_result.get('current_task')}/{check_result.get('total_tasks')}", Colors.WHITE)
            print_colored(f"   已完成: {check_result.get('completed')}", Colors.GREEN)
            print_colored(f"   待处理: {check_result.get('pending')}", Colors.YELLOW)
            print_colored(f"   中断原因: {check_result.get('interrupt_reason')}", Colors.RED)
            print_colored(f"\n💡 恢复提示: {check_result.get('recovery_hint')}", Colors.CYAN)
        else:
            print_colored(f"❌ 无法恢复: {check_result.get('reason')}", Colors.RED)
        
        return
    
    prepare_result = resumer.prepare_resume()
    
    if not prepare_result.get("ready"):
        print_colored(f"无法恢复项目: {prepare_result.get('reason')}", Colors.RED)
        return
    
    print_header(f"恢复项目: {prepare_result['project_name']}")
    
    print_colored(f"项目ID: {prepare_result['project_id']}", Colors.WHITE)
    print_colored(f"从任务 {prepare_result['resume_from_index']} 继续", Colors.YELLOW)
    print_colored(f"待处理任务: {len(prepare_result['pending_tasks'])} 个", Colors.CYAN)
    
    if args.checkpoint:
        print_colored(f"从检查点恢复: {args.checkpoint}", Colors.YELLOW)
    
    print_colored("\n准备恢复项目执行...", Colors.GREEN)
    print_colored("注意: 完整的恢复功能需要重新运行项目会话", Colors.YELLOW)
    print_colored(f"\n建议使用以下命令重新运行:", Colors.CYAN)
    print_colored(f"  multi-agent run --name \"{prepare_result['project_name']}\" -r \"继续之前的任务\"", Colors.WHITE)


def main() -> None:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    handlers = {
        "run": handle_run,
        "init": handle_init,
        "status": handle_status,
        "task": handle_task,
        "agent": handle_agent,
        "config": handle_config,
        "resume": handle_resume,
    }
    
    handler = handlers.get(args.command)
    if handler:
        asyncio.run(handler(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
