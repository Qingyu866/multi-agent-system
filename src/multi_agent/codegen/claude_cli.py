"""
Claude CLI integration for code generation.

工作流程规范：
1. 在指定的工作目录中执行Claude CLI
2. Claude CLI自动将创建的文件保存到工作目录
3. 代码生成完成后，CTO转发给QA审查
4. QA根据审查标准进行代码审查
5. 如有问题，开发者根据反馈修改代码
6. 最终确认后进入部署准备阶段
"""

import asyncio
import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Callable, Any, List
from enum import Enum

from multi_agent.codegen.manager import CodeManager, CodeFile


class WorkflowStage(Enum):
    """工作流程阶段"""
    INITIALIZATION = "initialization"
    CODE_GENERATION = "code_generation"
    QA_REVIEW = "qa_review"
    REVISION = "revision"
    FINAL_CONFIRMATION = "final_confirmation"
    DEPLOYMENT_PREP = "deployment_prep"
    COMPLETED = "completed"


@dataclass
class QAReviewCriteria:
    """QA审查标准"""
    check_syntax: bool = True
    check_code_style: bool = True
    check_security: bool = True
    check_performance: bool = True
    check_best_practices: bool = True
    check_documentation: bool = True
    check_error_handling: bool = True
    check_test_coverage: bool = False
    
    def get_review_prompt(self) -> str:
        """生成审查提示"""
        criteria = []
        if self.check_syntax:
            criteria.append("- 语法正确性：代码无语法错误，可以正常编译/运行")
        if self.check_code_style:
            criteria.append("- 代码风格：符合语言规范（如PEP8、ESLint等）")
        if self.check_security:
            criteria.append("- 安全性：无安全漏洞（如SQL注入、XSS等）")
        if self.check_performance:
            criteria.append("- 性能优化：无明显性能问题")
        if self.check_best_practices:
            criteria.append("- 最佳实践：遵循行业最佳实践")
        if self.check_documentation:
            criteria.append("- 文档注释：关键代码有清晰的注释")
        if self.check_error_handling:
            criteria.append("- 错误处理：异常情况得到妥善处理")
        if self.check_test_coverage:
            criteria.append("- 测试覆盖：关键功能有单元测试")
        
        return "\n".join(criteria)


@dataclass
class WorkflowState:
    """工作流程状态"""
    current_stage: WorkflowStage = WorkflowStage.INITIALIZATION
    revision_count: int = 0
    max_revisions: int = 3
    qa_feedbacks: List[str] = field(default_factory=list)
    approved: bool = False
    
    def can_revise(self) -> bool:
        return self.revision_count < self.max_revisions
    
    def advance(self) -> None:
        stages = list(WorkflowStage)
        current_idx = stages.index(self.current_stage)
        if current_idx < len(stages) - 1:
            self.current_stage = stages[current_idx + 1]


@dataclass
class ClaudeCLIConfig:
    """Configuration for Claude CLI."""
    
    cli_path: str = "claude"
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 100000
    timeout: int = 300
    working_dir: Optional[str] = None
    auto_save: bool = True


class ClaudeCLIExecutor:
    """
    Executes Claude CLI for code generation.
    
    Provides real-time output streaming and code extraction.
    
    使用 --dangerously-skip-permissions 让Claude CLI能够自动创建文件。
    """
    
    def __init__(
        self,
        config: Optional[ClaudeCLIConfig] = None,
        output_callback: Optional[Callable[[str, str], None]] = None,
    ):
        self.config = config or ClaudeCLIConfig()
        self.output_callback = output_callback
        self._process: Optional[asyncio.subprocess.Process] = None
    
    async def execute(
        self,
        prompt: str,
        working_dir: Optional[str] = None,
        allow_file_creation: bool = True,
    ) -> str:
        """
        Execute Claude CLI with a prompt.
        
        Args:
            prompt: The prompt to send to Claude
            working_dir: Working directory for execution
            allow_file_creation: Whether to allow Claude to create files
            
        Returns:
            The complete response
        """
        work_dir = working_dir or self.config.working_dir or os.getcwd()
        
        cmd = [
            self.config.cli_path,
            "--print",
            "-p", prompt,
        ]
        
        if allow_file_creation:
            cmd.append("--dangerously-skip-permissions")
        
        if self.output_callback:
            cmd_display = f"claude --print --dangerously-skip-permissions -p [prompt...]" if allow_file_creation else f"claude --print -p [prompt...]"
            self.output_callback("info", f"执行 Claude CLI: {cmd_display}")
        
        try:
            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=work_dir,
            )
            
            stdout, stderr = await asyncio.wait_for(
                self._process.communicate(),
                timeout=self.config.timeout,
            )
            
            output = stdout.decode('utf-8', errors='replace')
            error = stderr.decode('utf-8', errors='replace')
            
            if self._process.returncode != 0:
                if self.output_callback:
                    self.output_callback("error", f"Claude CLI 错误: {error}")
                raise RuntimeError(f"Claude CLI 失败: {error}")
            
            if self.output_callback:
                self.output_callback("complete", "Claude CLI 执行完成")
            
            return output
            
        except asyncio.TimeoutError:
            if self._process:
                self._process.kill()
            raise RuntimeError("Claude CLI 执行超时")
        except FileNotFoundError:
            raise RuntimeError(f"找不到 Claude CLI: {self.config.cli_path}")
    
    def cancel(self) -> None:
        """Cancel the current execution."""
        if self._process:
            self._process.kill()


class ClaudeCodeGenerator:
    """
    Code generator using Claude CLI.
    
    完整工作流程：
    1. 初始化 - 设置工作目录和项目结构
    2. 代码生成 - Claude CLI在指定目录执行并保存文件
    3. QA审查 - 根据审查标准检查代码
    4. 修改循环 - 根据QA反馈修改代码（最多3轮）
    5. 最终确认 - CEO确认代码质量
    6. 部署准备 - 生成部署配置和文档
    """
    
    SYSTEM_PROMPT = """你是一个专业的软件工程师。

## 重要：你有权限直接创建和修改文件！

当被要求生成代码时，请直接使用文件操作工具创建文件，而不是只输出代码块。

### 文件组织规范：
1. **代码文件**：
   - Python代码放在 `backend/` 或项目根目录
   - 前端代码放在 `frontend/src/`
   - 测试代码放在 `tests/`

2. **文档文件**：
   - 所有文档（.md文件）统一放在 `docs/` 文件夹
   - README.md 放在项目根目录
   - 快速上手指南等放在 `docs/`

3. **配置文件**：
   - requirements.txt, package.json 等放在根目录
   - Dockerfile, docker-compose.yml 放在根目录
   - .env.example 放在根目录

### 工作流程：
1. 分析任务需求
2. 规划文件结构
3. 直接创建文件（使用 Write 或 Edit 工具）
4. 确保文件内容完整、可运行

### 代码规范：
1. 代码完整可运行
2. 包含必要的导入和配置
3. 用中文注释说明关键逻辑
4. 遵循语言的最佳实践

不要只是输出代码块，要实际创建文件！
"""
    
    QA_REVIEW_PROMPT = """作为QA工程师，请对以下代码进行全面审查。

## 审查标准
{review_criteria}

## 代码内容
{code_content}

## 审查要求
1. 逐项检查上述标准，给出评分（通过/需修改）
2. 列出发现的具体问题
3. 提供修改建议
4. 给出最终结论：通过 / 需要修改

请用中文回复，格式如下：
## 审查结果
### 1. 语法正确性
[评估结果]

### 2. 代码风格
[评估结果]

### 3. 安全性
[评估结果]

### 4. 性能优化
[评估结果]

### 5. 最佳实践
[评估结果]

### 6. 文档注释
[评估结果]

### 7. 错误处理
[评估结果]

## 问题列表
1. [问题描述]
2. [问题描述]

## 修改建议
1. [建议]
2. [建议]

## 最终结论
[通过 / 需要修改]
"""
    
    DEPLOYMENT_PREP_PROMPT = """请为以下项目生成部署准备文件：

## 项目信息
- 项目名称: {project_name}
- 技术栈: {tech_stack}

## 已生成的代码文件
{file_list}

## 需要生成的部署文件
1. requirements.txt 或 package.json（依赖管理）
2. Dockerfile（容器化配置）
3. docker-compose.yml（服务编排）
4. .env.example（环境变量模板）
5. README.md（部署说明）

请生成完整的部署配置文件。
"""
    
    def __init__(
        self,
        code_manager: CodeManager,
        cli_config: Optional[ClaudeCLIConfig] = None,
        output_callback: Optional[Callable[[str, str, str], None]] = None,
        qa_criteria: Optional[QAReviewCriteria] = None,
    ):
        self.code_manager = code_manager
        self.cli_config = cli_config or ClaudeCLIConfig()
        self.output_callback = output_callback
        self.qa_criteria = qa_criteria or QAReviewCriteria()
        self.workflow_state = WorkflowState()
        self.executor = ClaudeCLIExecutor(
            config=self.cli_config,
            output_callback=self._handle_cli_output,
        )
    
    def _handle_cli_output(self, msg_type: str, message: str) -> None:
        """Handle CLI output and forward to callback."""
        if self.output_callback:
            self.output_callback("cli", msg_type, message)
    
    def set_working_directory(self, working_dir: str) -> None:
        """设置Claude CLI的工作目录"""
        self.cli_config.working_dir = working_dir
        self.executor.config.working_dir = working_dir
        self.code_manager.output_dir = Path(working_dir)
    
    async def generate_code(
        self,
        task: str,
        context: dict,
        task_name: str = "",
    ) -> dict:
        """
        Generate code for a task using Claude CLI.
        
        Claude CLI直接在工作目录中创建和修改文件，不需要通过CodeManager保存。
        """
        self.workflow_state.current_stage = WorkflowStage.CODE_GENERATION
        
        tech_stack = context.get('tech_stack', {})
        project_name = context.get('project_name', 'project')
        working_dir = self.cli_config.working_dir or str(self.code_manager.output_dir)
        
        prompt = f"""{self.SYSTEM_PROMPT}

## 项目信息
- 项目名称: {project_name}
- 工作目录: {working_dir}
- 前端技术: {tech_stack.get('frontend', 'React + TypeScript')}
- 后端技术: {tech_stack.get('backend', 'Python + FastAPI')}
- 数据库: {tech_stack.get('database', 'SQLite')}

## 任务
{task}

请生成完整的代码实现，确保：
1. 代码完整可运行
2. 包含所有必要的文件
3. 遵循最佳实践
4. 文件保存到工作目录: {working_dir}

重要：直接创建或修改文件，不要只是输出代码块。
"""
        
        if self.output_callback:
            self.output_callback("agent", "info", f"📂 工作目录: {working_dir}")
            self.output_callback("agent", "info", f"开始生成代码: {task_name or task[:50]}")
        
        try:
            response = await self.executor.execute(prompt, working_dir=working_dir)
            
            actual_files = self._scan_created_files(working_dir)
            
            if self.output_callback:
                self.output_callback("agent", "complete", f"代码生成完成，发现 {len(actual_files)} 个文件")
            
            return {
                'success': True,
                'response': response,
                'saved_files': actual_files,
                'file_count': len(actual_files),
                'working_dir': working_dir,
                'workflow_stage': self.workflow_state.current_stage.value,
            }
            
        except Exception as e:
            if self.output_callback:
                self.output_callback("agent", "error", f"代码生成失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'saved_files': [],
                'working_dir': working_dir,
            }
    
    def _scan_created_files(self, working_dir: str) -> list[str]:
        """扫描工作目录中实际存在的代码文件"""
        code_extensions = {'.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.go', '.rs', 
                          '.html', '.css', '.scss', '.json', '.yaml', '.yml', '.md', 
                          '.sh', '.sql', '.txt', '.env', '.example', '.toml', '.dockerfile'}
        
        files = []
        working_path = Path(working_dir)
        
        existing_paths = {f.path for f in self.code_manager.files}
        
        if working_path.exists():
            for file_path in working_path.rglob('*'):
                if file_path.is_file():
                    suffix = file_path.suffix.lower()
                    name_lower = file_path.name.lower()
                    
                    is_code_file = suffix in code_extensions
                    is_config_file = name_lower.startswith('.') or name_lower in {
                        'dockerfile', 'makefile', 'readme.md', 'requirements.txt'
                    }
                    
                    if is_code_file or is_config_file:
                        str_path = str(file_path)
                        files.append(str_path)
                        
                        if str_path not in existing_paths:
                            self.code_manager.files.append(CodeFile(
                                path=str_path,
                                content='',
                                language=suffix[1:] if suffix else 'text',
                                description="Created by Claude CLI",
                            ))
                            existing_paths.add(str_path)
        
        return files
    
    async def generate_revision(
        self,
        original_code: str,
        qa_feedback: str,
        context: dict,
        task_name: str = "",
    ) -> dict:
        """
        根据QA反馈修改代码。
        
        Args:
            original_code: 原始代码
            qa_feedback: QA反馈意见
            context: 上下文信息
            task_name: 任务名称
            
        Returns:
            修改后的代码和保存的文件
        """
        self.workflow_state.current_stage = WorkflowStage.REVISION
        self.workflow_state.revision_count += 1
        
        working_dir = self.cli_config.working_dir or str(self.code_manager.output_dir)
        
        prompt = f"""{self.SYSTEM_PROMPT}

## 任务：根据QA反馈修改代码

### 原始代码
{original_code[:3000]}

### QA反馈意见
{qa_feedback}

### 修改要求
1. 根据QA反馈逐项修改代码
2. 保持原有功能不变
3. 解决所有提出的问题
4. 确保修改后的代码可以运行

请生成修改后的完整代码。
"""
        
        if self.output_callback:
            self.output_callback("agent", "info", f"开始第 {self.workflow_state.revision_count} 轮修改...")
        
        try:
            response = await self.executor.execute(prompt, working_dir=working_dir)
            
            saved_files = self.code_manager.save_from_response(
                response,
                task_name=f"{task_name}_rev{self.workflow_state.revision_count}",
            )
            
            if self.output_callback:
                self.output_callback("agent", "complete", f"修改完成，保存了 {len(saved_files)} 个文件")
            
            return {
                'success': True,
                'response': response,
                'saved_files': saved_files,
                'revision_count': self.workflow_state.revision_count,
            }
            
        except Exception as e:
            if self.output_callback:
                self.output_callback("agent", "error", f"修改失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'saved_files': [],
            }
    
    def get_qa_review_prompt(self, code_content: str) -> str:
        """生成QA审查提示"""
        return self.QA_REVIEW_PROMPT.format(
            review_criteria=self.qa_criteria.get_review_prompt(),
            code_content=code_content[:5000],
        )
    
    async def prepare_deployment(
        self,
        project_name: str,
        tech_stack: dict,
        generated_files: list,
    ) -> dict:
        """
        准备部署配置文件。
        
        生成：
        - requirements.txt / package.json
        - Dockerfile
        - docker-compose.yml
        - .env.example
        - 部署说明文档
        """
        self.workflow_state.current_stage = WorkflowStage.DEPLOYMENT_PREP
        
        working_dir = self.cli_config.working_dir or str(self.code_manager.output_dir)
        file_list = "\n".join([f"- {f}" for f in generated_files[:20]])
        
        prompt = self.DEPLOYMENT_PREP_PROMPT.format(
            project_name=project_name,
            tech_stack=tech_stack,
            file_list=file_list,
        )
        
        if self.output_callback:
            self.output_callback("agent", "info", "正在准备部署配置...")
        
        try:
            response = await self.executor.execute(prompt, working_dir=working_dir)
            
            saved_files = self.code_manager.save_from_response(
                response,
                task_name="deployment",
            )
            
            if self.output_callback:
                self.output_callback("agent", "complete", f"部署配置已生成，保存了 {len(saved_files)} 个文件")
            
            return {
                'success': True,
                'response': response,
                'saved_files': saved_files,
            }
            
        except Exception as e:
            if self.output_callback:
                self.output_callback("agent", "error", f"部署准备失败: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'saved_files': [],
            }
    
    def get_workflow_summary(self) -> dict:
        """获取工作流程摘要"""
        return {
            'current_stage': self.workflow_state.current_stage.value,
            'revision_count': self.workflow_state.revision_count,
            'max_revisions': self.workflow_state.max_revisions,
            'can_revise': self.workflow_state.can_revise(),
            'qa_feedbacks_count': len(self.workflow_state.qa_feedbacks),
            'approved': self.workflow_state.approved,
        }
    
    async def generate_project_structure(
        self,
        project_name: str,
        tech_stack: dict,
    ) -> dict:
        """
        Generate initial project structure.
        
        在工作目录中创建项目结构。
        """
        self.workflow_state.current_stage = WorkflowStage.INITIALIZATION
        return self.code_manager.create_project_structure(project_name, tech_stack)


def check_claude_cli_available() -> tuple[bool, str]:
    """
    Check if Claude CLI is available.
    
    Returns:
        Tuple of (is_available, path_or_error_message)
    """
    claude_path = shutil.which('claude')
    
    if claude_path:
        return True, claude_path
    
    return False, (
        "Claude CLI 未安装。请先安装 Claude CLI:\n"
        "  macOS/Linux: brew install claude\n"
        "  或访问: https://docs.anthropic.com/claude/docs/claude-cli\n"
        "安装后，系统将使用 Claude CLI 进行代码生成。"
    )
