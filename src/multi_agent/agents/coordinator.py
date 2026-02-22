"""
任务分配与结果整合机制

实现智能任务分配，根据任务特征自动路由到最合适的细分Agent，
并提供结果整合机制，确保各细分Agent协同工作。

核心功能：
1. 任务分析 - 分析任务特征，识别所需技能
2. 智能路由 - 根据任务特征分配给合适的Agent
3. 结果整合 - 汇总各Agent的工作成果
4. 冲突解决 - 处理Agent间的协作冲突
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable, Any
import re

from multi_agent.core.types import AgentRole, TaskContext, TaskPriority


class TaskCategory(str, Enum):
    """任务类别"""
    FRONTEND = "frontend"
    BACKEND = "backend"
    FULLSTACK = "fullstack"
    MOBILE = "mobile"
    DATABASE = "database"
    DEVOPS = "devops"
    DESIGN = "design"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    UNKNOWN = "unknown"


class TaskComplexity(str, Enum):
    """任务复杂度"""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


@dataclass
class TaskAnalysis:
    """任务分析结果"""
    category: TaskCategory = TaskCategory.UNKNOWN
    complexity: TaskComplexity = TaskComplexity.MEDIUM
    required_skills: list[str] = field(default_factory=list)
    suggested_agents: list[AgentRole] = field(default_factory=list)
    estimated_time: str = "medium"
    dependencies: list[str] = field(default_factory=list)
    tech_stack: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "category": self.category.value,
            "complexity": self.complexity.value,
            "required_skills": self.required_skills,
            "suggested_agents": [a.value for a in self.suggested_agents],
            "estimated_time": self.estimated_time,
            "dependencies": self.dependencies,
            "tech_stack": self.tech_stack,
        }


@dataclass
class AgentAssignment:
    """Agent任务分配"""
    agent_role: AgentRole
    task_id: str
    sub_task: str
    priority: TaskPriority = TaskPriority.MEDIUM
    dependencies: list[str] = field(default_factory=list)
    estimated_tokens: int = 4000
    
    def to_dict(self) -> dict:
        return {
            "agent_role": self.agent_role.value,
            "task_id": self.task_id,
            "sub_task": self.sub_task,
            "priority": self.priority.value,
            "dependencies": self.dependencies,
            "estimated_tokens": self.estimated_tokens,
        }


@dataclass
class IntegrationResult:
    """结果整合"""
    success: bool
    integrated_files: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    resolutions: list[str] = field(default_factory=list)
    summary: str = ""
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "integrated_files": self.integrated_files,
            "conflicts": self.conflicts,
            "resolutions": self.resolutions,
            "summary": self.summary,
        }


class TaskAnalyzer:
    """
    任务分析器
    
    分析任务特征，识别所需技能和合适的Agent。
    """
    
    KEYWORD_MAPPINGS = {
        TaskCategory.FRONTEND: [
            "前端", "frontend", "ui", "界面", "页面", "组件", "react", "vue", "angular",
            "css", "样式", "响应式", "动画", "交互", "用户体验", "ux",
            "html", "javascript", "typescript", "tailwind", "sass",
        ],
        TaskCategory.BACKEND: [
            "后端", "backend", "api", "接口", "服务", "server", "rest", "graphql",
            "数据库", "database", "sql", "orm", "认证", "auth", "授权",
            "python", "fastapi", "django", "flask", "express", "spring",
        ],
        TaskCategory.FULLSTACK: [
            "全栈", "fullstack", "完整功能", "端到端", "e2e", "全流程",
            "前后端", "整体实现", "完整模块",
        ],
        TaskCategory.MOBILE: [
            "移动端", "mobile", "app", "ios", "android", "手机", "平板",
            "react native", "flutter", "swift", "kotlin", "移动应用",
        ],
        TaskCategory.DATABASE: [
            "数据库", "database", "sql", "表", "索引", "查询优化", "迁移",
            "postgresql", "mysql", "mongodb", "redis", "数据模型", "schema",
        ],
        TaskCategory.DEVOPS: [
            "部署", "deploy", "docker", "kubernetes", "k8s", "ci/cd", "cicd",
            "容器", "运维", "监控", "日志", "自动化", "pipeline",
        ],
        TaskCategory.DESIGN: [
            "设计", "design", "ui设计", "ux设计", "原型", "视觉", "交互设计",
            "figma", "sketch", "设计稿", "用户体验设计",
        ],
        TaskCategory.TESTING: [
            "测试", "test", "单元测试", "集成测试", "e2e测试", "自动化测试",
            "jest", "pytest", "cypress", "测试用例",
        ],
        TaskCategory.DOCUMENTATION: [
            "文档", "documentation", "readme", "说明", "注释", "api文档",
            "使用指南", "教程",
        ],
    }
    
    TECH_STACK_MAPPINGS = {
        "react": [AgentRole.FRONTEND_DEVELOPER],
        "vue": [AgentRole.FRONTEND_DEVELOPER],
        "angular": [AgentRole.FRONTEND_DEVELOPER],
        "next.js": [AgentRole.FULLSTACK_DEVELOPER],
        "nuxt": [AgentRole.FULLSTACK_DEVELOPER],
        "fastapi": [AgentRole.BACKEND_DEVELOPER],
        "django": [AgentRole.BACKEND_DEVELOPER],
        "flask": [AgentRole.BACKEND_DEVELOPER],
        "express": [AgentRole.BACKEND_DEVELOPER],
        "spring": [AgentRole.BACKEND_DEVELOPER],
        "react native": [AgentRole.MOBILE_DEVELOPER],
        "flutter": [AgentRole.MOBILE_DEVELOPER],
        "docker": [AgentRole.DEVOPS_ENGINEER],
        "kubernetes": [AgentRole.DEVOPS_ENGINEER],
        "postgresql": [AgentRole.DATABASE_DEVELOPER],
        "mysql": [AgentRole.DATABASE_DEVELOPER],
        "mongodb": [AgentRole.DATABASE_DEVELOPER],
        "redis": [AgentRole.DATABASE_DEVELOPER],
    }
    
    def __init__(self, output_callback: Optional[Callable[[str, str, str], None]] = None):
        self.output_callback = output_callback
    
    def _log(self, level: str, message: str) -> None:
        if self.output_callback:
            self.output_callback("task_analyzer", level, message)
    
    def analyze(self, task: TaskContext) -> TaskAnalysis:
        """
        分析任务特征
        
        Args:
            task: 任务上下文
            
        Returns:
            TaskAnalysis: 任务分析结果
        """
        self._log("info", f"开始分析任务: {task.title}")
        
        analysis = TaskAnalysis()
        
        content = f"{task.title} {task.description}".lower()
        
        category_scores = {}
        for category, keywords in self.KEYWORD_MAPPINGS.items():
            score = sum(1 for kw in keywords if kw in content)
            if score > 0:
                category_scores[category] = score
        
        if category_scores:
            analysis.category = max(category_scores, key=category_scores.get)
        
        for tech, agents in self.TECH_STACK_MAPPINGS.items():
            if tech in content:
                analysis.tech_stack.append(tech)
                for agent in agents:
                    if agent not in analysis.suggested_agents:
                        analysis.suggested_agents.append(agent)
        
        if not analysis.suggested_agents:
            analysis.suggested_agents = self._get_default_agents(analysis.category)
        
        analysis.required_skills = self._extract_required_skills(content)
        analysis.complexity = self._estimate_complexity(task)
        analysis.estimated_time = self._estimate_time(analysis.complexity)
        
        self._log("complete", f"任务分析完成: 类别={analysis.category.value}, 建议={len(analysis.suggested_agents)}个Agent")
        
        return analysis
    
    def _get_default_agents(self, category: TaskCategory) -> list[AgentRole]:
        """获取默认Agent分配"""
        defaults = {
            TaskCategory.FRONTEND: [AgentRole.FRONTEND_DEVELOPER],
            TaskCategory.BACKEND: [AgentRole.BACKEND_DEVELOPER],
            TaskCategory.FULLSTACK: [AgentRole.FULLSTACK_DEVELOPER],
            TaskCategory.MOBILE: [AgentRole.MOBILE_DEVELOPER],
            TaskCategory.DATABASE: [AgentRole.DATABASE_DEVELOPER],
            TaskCategory.DEVOPS: [AgentRole.DEVOPS_ENGINEER],
            TaskCategory.DESIGN: [AgentRole.UI_UX_DESIGNER],
            TaskCategory.TESTING: [AgentRole.QA_ENGINEER],
            TaskCategory.DOCUMENTATION: [AgentRole.DOCUMENTATION],
            TaskCategory.UNKNOWN: [AgentRole.FULLSTACK_DEVELOPER],
        }
        return defaults.get(category, [AgentRole.FULLSTACK_DEVELOPER])
    
    def _extract_required_skills(self, content: str) -> list[str]:
        """提取所需技能"""
        skills = []
        skill_patterns = [
            r'\b(python|javascript|typescript|java|go|rust)\b',
            r'\b(react|vue|angular|next\.?js|nuxt)\b',
            r'\b(fastapi|django|flask|express|spring)\b',
            r'\b(postgresql|mysql|mongodb|redis|sqlite)\b',
            r'\b(docker|kubernetes|nginx)\b',
            r'\b(tailwind|css|scss|sass)\b',
        ]
        
        for pattern in skill_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            skills.extend(matches)
        
        return list(set(skills))
    
    def _estimate_complexity(self, task: TaskContext) -> TaskComplexity:
        """评估任务复杂度"""
        score = 0
        
        if len(task.description) > 500:
            score += 2
        elif len(task.description) > 200:
            score += 1
        
        if task.priority == TaskPriority.CRITICAL:
            score += 2
        elif task.priority == TaskPriority.HIGH:
            score += 1
        
        if len(task.dependencies) > 2:
            score += 2
        elif len(task.dependencies) > 0:
            score += 1
        
        if score >= 4:
            return TaskComplexity.COMPLEX
        elif score >= 2:
            return TaskComplexity.MEDIUM
        else:
            return TaskComplexity.SIMPLE
    
    def _estimate_time(self, complexity: TaskComplexity) -> str:
        """预估时间"""
        time_estimates = {
            TaskComplexity.SIMPLE: "short (15-30 min)",
            TaskComplexity.MEDIUM: "medium (30-60 min)",
            TaskComplexity.COMPLEX: "long (1-2 hours)",
        }
        return time_estimates.get(complexity, "medium")


class TaskRouter:
    """
    任务路由器
    
    根据任务分析结果，将任务分配给最合适的Agent。
    """
    
    def __init__(self, output_callback: Optional[Callable[[str, str, str], None]] = None):
        self.output_callback = output_callback
        self.analyzer = TaskAnalyzer(output_callback)
    
    def _log(self, level: str, message: str) -> None:
        if self.output_callback:
            self.output_callback("task_router", level, message)
    
    def route(self, task: TaskContext) -> list[AgentAssignment]:
        """
        路由任务到合适的Agent
        
        Args:
            task: 任务上下文
            
        Returns:
            list[AgentAssignment]: Agent分配列表
        """
        self._log("info", f"开始路由任务: {task.title}")
        
        analysis = self.analyzer.analyze(task)
        assignments = []
        
        if len(analysis.suggested_agents) == 1:
            agent = analysis.suggested_agents[0]
            assignments.append(AgentAssignment(
                agent_role=agent,
                task_id=str(task.id),
                sub_task=task.description,
                priority=task.priority,
                estimated_tokens=self._estimate_tokens(analysis),
            ))
        else:
            sub_tasks = self._split_task(task, analysis)
            
            for i, (agent, sub_task) in enumerate(zip(analysis.suggested_agents, sub_tasks)):
                dependencies = []
                if i > 0:
                    dependencies = [str(task.id)]
                
                assignments.append(AgentAssignment(
                    agent_role=agent,
                    task_id=f"{task.id}_{i+1}",
                    sub_task=sub_task,
                    priority=task.priority,
                    dependencies=dependencies,
                    estimated_tokens=self._estimate_tokens(analysis),
                ))
        
        self._log("complete", f"任务路由完成: 分配给 {len(assignments)} 个Agent")
        
        return assignments
    
    def _split_task(self, task: TaskContext, analysis: TaskAnalysis) -> list[str]:
        """拆分任务"""
        if len(analysis.suggested_agents) <= 1:
            return [task.description]
        
        sub_tasks = []
        agents = analysis.suggested_agents
        
        for i, agent in enumerate(agents):
            if agent == AgentRole.FRONTEND_DEVELOPER:
                sub_tasks.append(f"前端部分: {task.description}")
            elif agent == AgentRole.BACKEND_DEVELOPER:
                sub_tasks.append(f"后端部分: {task.description}")
            elif agent == AgentRole.DATABASE_DEVELOPER:
                sub_tasks.append(f"数据库部分: {task.description}")
            elif agent == AgentRole.UI_UX_DESIGNER:
                sub_tasks.append(f"设计部分: {task.description}")
            else:
                sub_tasks.append(f"部分{i+1}: {task.description}")
        
        return sub_tasks
    
    def _estimate_tokens(self, analysis: TaskAnalysis) -> int:
        """预估Token消耗"""
        base_tokens = {
            TaskComplexity.SIMPLE: 2000,
            TaskComplexity.MEDIUM: 4000,
            TaskComplexity.COMPLEX: 8000,
        }
        return base_tokens.get(analysis.complexity, 4000)


class ResultIntegrator:
    """
    结果整合器
    
    整合多个Agent的工作成果，处理冲突。
    """
    
    def __init__(self, output_callback: Optional[Callable[[str, str, str], None]] = None):
        self.output_callback = output_callback
    
    def _log(self, level: str, message: str) -> None:
        if self.output_callback:
            self.output_callback("result_integrator", level, message)
    
    def integrate(
        self,
        task: TaskContext,
        agent_results: dict[AgentRole, dict],
    ) -> IntegrationResult:
        """
        整合Agent结果
        
        Args:
            task: 任务上下文
            agent_results: 各Agent的结果
            
        Returns:
            IntegrationResult: 整合结果
        """
        self._log("info", f"开始整合任务结果: {task.title}")
        
        result = IntegrationResult(success=True)
        
        all_files = []
        for agent_role, agent_result in agent_results.items():
            if "saved_files" in agent_result:
                all_files.extend(agent_result["saved_files"])
        
        result.integrated_files = list(set(all_files))
        
        conflicts = self._detect_conflicts(agent_results)
        if conflicts:
            result.conflicts = conflicts
            result.resolutions = self._resolve_conflicts(conflicts)
        
        result.summary = self._generate_summary(task, agent_results)
        
        self._log("complete", f"结果整合完成: {len(result.integrated_files)} 个文件")
        
        return result
    
    def _detect_conflicts(self, agent_results: dict[AgentRole, dict]) -> list[str]:
        """检测冲突"""
        conflicts = []
        
        file_owners = {}
        for agent_role, result in agent_results.items():
            for file_path in result.get("saved_files", []):
                if file_path in file_owners:
                    conflicts.append(f"文件冲突: {file_path} 被 {file_owners[file_path]} 和 {agent_role} 同时修改")
                else:
                    file_owners[file_path] = agent_role
        
        return conflicts
    
    def _resolve_conflicts(self, conflicts: list[str]) -> list[str]:
        """解决冲突"""
        resolutions = []
        for conflict in conflicts:
            resolutions.append(f"自动解决: {conflict} - 保留最新版本")
        return resolutions
    
    def _generate_summary(
        self,
        task: TaskContext,
        agent_results: dict[AgentRole, dict],
    ) -> str:
        """生成整合摘要"""
        total_files = sum(
            len(r.get("saved_files", []))
            for r in agent_results.values()
        )
        
        agents_involved = list(agent_results.keys())
        
        summary = f"""
任务: {task.title}
状态: 完成
参与Agent: {', '.join([a.value for a in agents_involved])}
生成文件: {total_files} 个
"""
        return summary.strip()


class SubAgentCoordinator:
    """
    细分Agent协调器
    
    统一管理任务分配和结果整合。
    """
    
    def __init__(self, output_callback: Optional[Callable[[str, str, str], None]] = None):
        self.output_callback = output_callback
        self.analyzer = TaskAnalyzer(output_callback)
        self.router = TaskRouter(output_callback)
        self.integrator = ResultIntegrator(output_callback)
    
    async def process_task(
        self,
        task: TaskContext,
        agent_executor: Callable[[AgentRole, str], Any],
    ) -> IntegrationResult:
        """
        处理任务：分析 -> 路由 -> 执行 -> 整合
        
        Args:
            task: 任务上下文
            agent_executor: Agent执行函数
            
        Returns:
            IntegrationResult: 整合结果
        """
        if self.output_callback:
            self.output_callback("coordinator", "info", f"开始处理任务: {task.title}")
        
        assignments = self.router.route(task)
        
        agent_results = {}
        for assignment in assignments:
            if self.output_callback:
                self.output_callback("coordinator", "info", f"分配给 {assignment.agent_role.value}")
            
            result = await agent_executor(assignment.agent_role, assignment.sub_task)
            agent_results[assignment.agent_role] = result
        
        integration = self.integrator.integrate(task, agent_results)
        
        if self.output_callback:
            self.output_callback("coordinator", "complete", f"任务处理完成: {integration.summary}")
        
        return integration
    
    def get_agent_for_task(self, task: TaskContext) -> AgentRole:
        """
        获取最适合处理任务的Agent
        
        Args:
            task: 任务上下文
            
        Returns:
            AgentRole: 建议的Agent角色
        """
        analysis = self.analyzer.analyze(task)
        if analysis.suggested_agents:
            return analysis.suggested_agents[0]
        return AgentRole.FULLSTACK_DEVELOPER
