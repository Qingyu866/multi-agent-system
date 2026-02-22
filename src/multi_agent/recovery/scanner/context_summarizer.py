"""上下文摘要生成器

生成项目恢复上下文，帮助CTO理解项目当前状态：
1. 项目概况摘要
2. 已完成工作总结
3. 恢复建议
4. 任务上下文补充
"""

from typing import Optional
from pathlib import Path

from multi_agent.recovery.scanner.project_scanner import (
    ProjectScanner,
    ProjectContext,
    ModuleInfo,
    FileInfo,
)


class ContextSummarizer:
    """上下文摘要生成器"""
    
    def __init__(self, scanner: ProjectScanner):
        self.scanner = scanner
    
    def generate_resume_context(
        self,
        project_state: dict,
        interrupt_reason: Optional[str] = None,
    ) -> str:
        """生成恢复上下文"""
        context = self.scanner.scan()
        
        current_task_index = project_state.get("current_task_index", 0)
        total_tasks = project_state.get("total_tasks", 0)
        completed_tasks = project_state.get("completed_tasks", [])
        pending_tasks = project_state.get("pending_tasks", [])
        task_list = project_state.get("task_list", [])
        
        resume_context = f"""
# 项目恢复上下文

## 项目概况
{context.summary}

## 技术栈
{self._format_tech_stack(context.tech_stack)}

## 执行进度
- 已完成任务: {len(completed_tasks)}/{total_tasks}
- 当前任务索引: {current_task_index}
- 待处理任务: {len(pending_tasks)}

## 已完成任务详情
{self._format_completed_tasks(task_list, completed_tasks)}

## 待处理任务详情
{self._format_pending_tasks(task_list, pending_tasks)}

## 项目结构
{self._format_structure(context.modules)}

## 关键文件
{self._format_key_files(context.key_files)}

## 中断原因
{interrupt_reason or '未知'}

## 恢复建议
{self._generate_recovery_suggestions(interrupt_reason, context)}

## 代码风格参考
{self._extract_code_style(context)}

---
*此上下文由系统自动生成，用于帮助CTO理解项目当前状态*
"""
        return resume_context.strip()
    
    def _format_tech_stack(self, tech_stack: dict[str, str]) -> str:
        """格式化技术栈"""
        if not tech_stack:
            return "未检测到明确的技术栈"
        
        lines = []
        for category, tech in tech_stack.items():
            lines.append(f"- {category}: {tech}")
        return "\n".join(lines)
    
    def _format_completed_tasks(
        self,
        task_list: list[dict],
        completed_ids: list[str],
    ) -> str:
        """格式化已完成任务"""
        if not completed_ids:
            return "暂无已完成的任务"
        
        lines = []
        for task in task_list:
            task_id = task.get("id", "")
            if task_id in completed_ids:
                name = task.get("name", task.get("description", "")[:50])
                lines.append(f"- [{task_id}] {name}")
        
        return "\n".join(lines) if lines else "暂无已完成的任务"
    
    def _format_pending_tasks(
        self,
        task_list: list[dict],
        pending_ids: list[str],
    ) -> str:
        """格式化待处理任务"""
        if not pending_ids:
            return "暂无待处理任务"
        
        lines = []
        for task in task_list:
            task_id = task.get("id", "")
            if task_id in pending_ids:
                name = task.get("name", task.get("description", "")[:50])
                assignee = task.get("assignee", "未分配")
                lines.append(f"- [{task_id}] {name} (负责人: {assignee})")
        
        return "\n".join(lines) if lines else "暂无待处理任务"
    
    def _format_structure(self, modules: list[ModuleInfo]) -> str:
        """格式化项目结构"""
        if not modules:
            return "未识别到明确的模块结构"
        
        lines = []
        for module in modules:
            file_count = len(module.files)
            total_lines = sum(f.lines for f in module.files)
            lines.append(f"- {module.name}: {file_count} files, {total_lines} lines")
        return "\n".join(lines)
    
    def _format_key_files(self, key_files: list[FileInfo]) -> str:
        """格式化关键文件"""
        if not key_files:
            return "未识别到关键文件"
        
        lines = []
        for f in key_files:
            lines.append(f"- {f.path} ({f.language}, {f.lines} lines)")
            if f.description:
                lines.append(f"  描述: {f.description}")
        return "\n".join(lines)
    
    def _generate_recovery_suggestions(
        self,
        interrupt_reason: Optional[str],
        context: ProjectContext,
    ) -> str:
        """生成恢复建议"""
        suggestions = []
        
        if interrupt_reason == "api_limit":
            suggestions.append("- 等待API限制重置后继续执行")
            suggestions.append("- 考虑使用备用API密钥")
        elif interrupt_reason == "network_error":
            suggestions.append("- 检查网络连接状态")
            suggestions.append("- 考虑使用代理或VPN")
        elif interrupt_reason == "cli_error":
            suggestions.append("- 检查Claude CLI是否正常安装")
            suggestions.append("- 验证CLI版本兼容性")
        else:
            suggestions.append("- 检查项目状态文件完整性")
            suggestions.append("- 验证已生成代码的正确性")
        
        suggestions.append("- 审查已完成任务的代码质量")
        suggestions.append("- 确认待处理任务的优先级")
        
        return "\n".join(suggestions)
    
    def _extract_code_style(self, context: ProjectContext) -> str:
        """提取代码风格"""
        style_hints = []
        
        for module in context.modules[:3]:
            for file_info in module.files[:2]:
                if file_info.language == "Python":
                    style_hints.append("- Python: 使用类型注解，遵循PEP 8规范")
                    break
                elif file_info.language in ["TypeScript", "TypeScript React"]:
                    style_hints.append("- TypeScript: 使用接口定义，组件化开发")
                    break
        
        if not style_hints:
            style_hints.append("- 遵循项目已有代码的命名规范")
            style_hints.append("- 保持与现有模块的一致性")
        
        return "\n".join(style_hints)
    
    def generate_task_context(
        self,
        task_description: str,
        task_index: int,
        task_list: list[dict],
    ) -> str:
        """为特定任务生成上下文"""
        context = self.scanner.scan()
        
        relevant_modules = self._find_relevant_modules(task_description, context)
        relevant_files = self._find_relevant_files(task_description, context)
        related_tasks = self._find_related_tasks(task_description, task_index, task_list)
        
        task_context = f"""
# 任务上下文

## 当前任务
{task_description}

## 相关模块
{self._format_relevant_modules(relevant_modules)}

## 相关文件
{self._format_relevant_files(relevant_files)}

## 相关任务
{self._format_related_tasks(related_tasks)}

## 技术栈参考
{self._format_tech_stack(context.tech_stack)}

## 编码规范
- 遵循已有代码的命名规范
- 保持与现有模块的一致性
- 添加必要的注释和文档
"""
        return task_context.strip()
    
    def _find_relevant_modules(
        self,
        task_description: str,
        context: ProjectContext,
    ) -> list[ModuleInfo]:
        """查找与任务相关的模块"""
        keywords = task_description.lower().split()
        relevant = []
        
        for module in context.modules:
            module_name_lower = module.name.lower()
            if any(kw in module_name_lower for kw in keywords):
                relevant.append(module)
        
        return relevant
    
    def _find_relevant_files(
        self,
        task_description: str,
        context: ProjectContext,
    ) -> list[FileInfo]:
        """查找与任务相关的文件"""
        keywords = task_description.lower().split()
        relevant = []
        
        for file_info in context.key_files:
            path_lower = file_info.path.lower()
            desc_lower = file_info.description.lower()
            
            if any(kw in path_lower or kw in desc_lower for kw in keywords):
                relevant.append(file_info)
        
        return relevant[:5]
    
    def _find_related_tasks(
        self,
        task_description: str,
        task_index: int,
        task_list: list[dict],
    ) -> list[dict]:
        """查找相关任务"""
        keywords = set(task_description.lower().split())
        related = []
        
        for i, task in enumerate(task_list):
            if i == task_index:
                continue
            
            task_desc = task.get("description", "").lower()
            task_keywords = set(task_desc.split())
            
            if keywords & task_keywords:
                related.append(task)
        
        return related[:3]
    
    def _format_relevant_modules(self, modules: list[ModuleInfo]) -> str:
        """格式化相关模块"""
        if not modules:
            return "未找到直接相关的模块，请参考项目整体结构"
        
        lines = []
        for m in modules:
            lines.append(f"- {m.name}: {m.description}")
        return "\n".join(lines)
    
    def _format_relevant_files(self, files: list[FileInfo]) -> str:
        """格式化相关文件"""
        if not files:
            return "未找到直接相关的文件"
        
        lines = []
        for f in files:
            lines.append(f"- {f.path}")
        return "\n".join(lines)
    
    def _format_related_tasks(self, tasks: list[dict]) -> str:
        """格式化相关任务"""
        if not tasks:
            return "未找到相关任务"
        
        lines = []
        for t in tasks:
            task_id = t.get("id", "?")
            desc = t.get("description", "")[:50]
            status = t.get("status", "pending")
            lines.append(f"- [{task_id}] {desc} ({status})")
        return "\n".join(lines)
