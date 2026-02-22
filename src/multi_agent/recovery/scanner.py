"""项目上下文扫描模块

功能：
1. 扫描项目目录结构和代码文件
2. 分析已完成的工作
3. 生成项目上下文摘要
4. 为恢复执行提供上下文信息

使用场景：
- 项目中断后恢复时，CTO需要了解当前进度
- 新任务需要参考已有代码
- 智能补充后续任务的提示词
"""

import os
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional
import json


@dataclass
class FileInfo:
    """文件信息"""
    path: str
    language: str
    size: int
    lines: int
    description: str = ""
    
    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "language": self.language,
            "size": self.size,
            "lines": self.lines,
            "description": self.description,
        }


@dataclass
class ModuleInfo:
    """模块信息"""
    name: str
    path: str
    files: list[FileInfo] = field(default_factory=list)
    description: str = ""
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": self.path,
            "files": [f.to_dict() for f in self.files],
            "description": self.description,
        }


@dataclass
class ProjectContext:
    """项目上下文"""
    project_name: str
    project_dir: str
    total_files: int
    total_lines: int
    modules: list[ModuleInfo] = field(default_factory=list)
    tech_stack: dict[str, str] = field(default_factory=dict)
    key_files: list[FileInfo] = field(default_factory=list)
    summary: str = ""
    
    def to_dict(self) -> dict:
        return {
            "project_name": self.project_name,
            "project_dir": self.project_dir,
            "total_files": self.total_files,
            "total_lines": self.total_lines,
            "modules": [m.to_dict() for m in self.modules],
            "tech_stack": self.tech_stack,
            "key_files": [f.to_dict() for f in self.key_files],
            "summary": self.summary,
        }


class ProjectScanner:
    """项目扫描器"""
    
    LANGUAGE_MAP = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".tsx": "TypeScript React",
        ".jsx": "JavaScript React",
        ".vue": "Vue",
        ".html": "HTML",
        ".css": "CSS",
        ".scss": "SCSS",
        ".json": "JSON",
        ".md": "Markdown",
        ".yaml": "YAML",
        ".yml": "YAML",
        ".sql": "SQL",
        ".sh": "Shell",
        ".dockerfile": "Docker",
        "Dockerfile": "Docker",
        ".env": "Environment",
    }
    
    IGNORE_DIRS = {
        "node_modules",
        "__pycache__",
        ".git",
        ".venv",
        "venv",
        "dist",
        "build",
        ".next",
        ".multi_agent_state",
        "test_",
    }
    
    IGNORE_FILES = {
        ".DS_Store",
        "Thumbs.db",
        ".gitignore",
        ".env.local",
        "package-lock.json",
        "yarn.lock",
    }
    
    KEY_FILES = {
        "README.md",
        "package.json",
        "requirements.txt",
        "main.py",
        "app.py",
        "index.ts",
        "index.tsx",
        "App.tsx",
        "docker-compose.yml",
        "Dockerfile",
    }
    
    MODULE_PATTERNS = {
        "backend": ["api", "core", "models", "schemas", "crud", "services", "routes"],
        "frontend": ["components", "pages", "services", "hooks", "utils", "styles", "assets"],
        "tests": ["tests", "test", "__tests__"],
        "docs": ["docs", "documentation"],
        "config": ["config", "settings"],
    }
    
    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self._files: list[FileInfo] = []
        self._modules: list[ModuleInfo] = []
    
    def scan(self) -> ProjectContext:
        """扫描项目"""
        self._files = []
        self._modules = []
        
        self._scan_directory(self.project_dir)
        
        modules = self._identify_modules()
        key_files = self._identify_key_files()
        tech_stack = self._detect_tech_stack()
        summary = self._generate_summary()
        
        total_lines = sum(f.lines for f in self._files)
        
        return ProjectContext(
            project_name=self.project_dir.name,
            project_dir=str(self.project_dir),
            total_files=len(self._files),
            total_lines=total_lines,
            modules=modules,
            tech_stack=tech_stack,
            key_files=key_files,
            summary=summary,
        )
    
    def _scan_directory(self, directory: Path, depth: int = 0) -> None:
        """递归扫描目录"""
        if depth > 5:
            return
        
        for item in directory.iterdir():
            if item.is_dir():
                if self._should_ignore_dir(item.name):
                    continue
                self._scan_directory(item, depth + 1)
            elif item.is_file():
                if self._should_ignore_file(item.name):
                    continue
                file_info = self._analyze_file(item)
                if file_info:
                    self._files.append(file_info)
    
    def _should_ignore_dir(self, name: str) -> bool:
        """检查是否应该忽略目录"""
        name_lower = name.lower()
        for ignore in self.IGNORE_DIRS:
            if ignore in name_lower:
                return True
        return False
    
    def _should_ignore_file(self, name: str) -> bool:
        """检查是否应该忽略文件"""
        if name in self.IGNORE_FILES:
            return True
        if name.startswith(".") and not name.endswith(".env"):
            return True
        return False
    
    def _analyze_file(self, file_path: Path) -> Optional[FileInfo]:
        """分析文件"""
        suffix = file_path.suffix.lower()
        if file_path.name == "Dockerfile":
            language = "Docker"
        else:
            language = self.LANGUAGE_MAP.get(suffix, "Unknown")
        
        if language == "Unknown":
            return None
        
        try:
            size = file_path.stat().st_size
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            lines = content.count("\n") + 1
        except Exception:
            return None
        
        description = self._extract_description(content, language)
        
        return FileInfo(
            path=str(file_path.relative_to(self.project_dir)),
            language=language,
            size=size,
            lines=lines,
            description=description,
        )
    
    def _extract_description(self, content: str, language: str) -> str:
        """提取文件描述"""
        lines = content.strip().split("\n")
        
        for line in lines[:10]:
            line = line.strip()
            
            if language == "Python":
                if line.startswith('"""') or line.startswith("'''"):
                    return line.strip('"""').strip("'''").strip()
                if line.startswith("# "):
                    return line[2:].strip()
            
            elif language in ["JavaScript", "TypeScript", "TypeScript React", "JavaScript React"]:
                if line.startswith("/**") or line.startswith("*"):
                    return line.replace("/**", "").replace("*/", "").replace("*", "").strip()
                if line.startswith("// "):
                    return line[3:].strip()
            
            elif language == "Markdown":
                if line.startswith("# "):
                    return line[2:].strip()
        
        return ""
    
    def _identify_modules(self) -> list[ModuleInfo]:
        """识别模块"""
        modules = []
        
        for module_type, patterns in self.MODULE_PATTERNS.items():
            for pattern in patterns:
                module_dir = self.project_dir / pattern
                if module_dir.exists() and module_dir.is_dir():
                    module_files = [
                        f for f in self._files
                        if f.path.startswith(pattern + "/")
                    ]
                    
                    if module_files:
                        modules.append(ModuleInfo(
                            name=f"{module_type}/{pattern}",
                            path=pattern,
                            files=module_files,
                            description=f"{module_type.capitalize()} module: {pattern}",
                        ))
        
        return modules
    
    def _identify_key_files(self) -> list[FileInfo]:
        """识别关键文件"""
        key_files = []
        
        for file_info in self._files:
            file_name = Path(file_info.path).name
            if file_name in self.KEY_FILES:
                key_files.append(file_info)
        
        return key_files
    
    def _detect_tech_stack(self) -> dict[str, str]:
        """检测技术栈"""
        tech_stack = {}
        
        has_package_json = any(
            f.path == "package.json" for f in self._files
        )
        has_requirements_txt = any(
            f.path == "requirements.txt" for f in self._files
        )
        has_dockerfile = any(
            "Dockerfile" in f.path for f in self._files
        )
        
        for file_info in self._files:
            path = file_info.path.lower()
            
            if "react" in path or ".tsx" in path or ".jsx" in path:
                tech_stack["frontend"] = "React"
            elif ".vue" in path:
                tech_stack["frontend"] = "Vue"
            
            if "fastapi" in path or "main.py" in path:
                tech_stack["backend"] = "FastAPI"
            elif "django" in path:
                tech_stack["backend"] = "Django"
            elif "express" in path:
                tech_stack["backend"] = "Express"
            
            if ".sql" in path or "models" in path:
                if "postgres" in file_info.description.lower():
                    tech_stack["database"] = "PostgreSQL"
                elif "mongo" in file_info.description.lower():
                    tech_stack["database"] = "MongoDB"
                else:
                    tech_stack["database"] = "SQL Database"
        
        if has_package_json:
            tech_stack.setdefault("frontend", "Node.js")
        if has_requirements_txt:
            tech_stack.setdefault("backend", "Python")
        if has_dockerfile:
            tech_stack["containerization"] = "Docker"
        
        return tech_stack
    
    def _generate_summary(self) -> str:
        """生成项目摘要"""
        total_files = len(self._files)
        total_lines = sum(f.lines for f in self._files)
        
        languages = {}
        for f in self._files:
            languages[f.language] = languages.get(f.language, 0) + 1
        
        top_languages = sorted(languages.items(), key=lambda x: x[1], reverse=True)[:3]
        
        modules = [m.name for m in self._identify_modules()]
        
        summary = f"""
项目: {self.project_dir.name}
文件数: {total_files}
代码行数: {total_lines}
主要语言: {', '.join([f'{l} ({c} files)' for l, c in top_languages])}
模块: {', '.join(modules) if modules else '未识别到模块'}
""".strip()
        
        return summary


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
        
        resume_context = f"""
# 项目恢复上下文

## 项目概况
{context.summary}

## 技术栈
{self._format_tech_stack(context.tech_stack)}

## 已完成的工作
- 已完成任务: {len(completed_tasks)}/{total_tasks}
- 当前任务索引: {current_task_index}
- 待处理任务: {len(pending_tasks)}

## 项目结构
{self._format_structure(context.modules)}

## 关键文件
{self._format_key_files(context.key_files)}

## 中断原因
{interrupt_reason or '未知'}

## 恢复建议
{self._generate_recovery_suggestions(interrupt_reason, context)}

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
    
    def generate_task_context(
        self,
        task_description: str,
        task_index: int,
    ) -> str:
        """为特定任务生成上下文"""
        context = self.scanner.scan()
        
        relevant_modules = self._find_relevant_modules(task_description, context)
        relevant_files = self._find_relevant_files(task_description, context)
        
        task_context = f"""
# 任务上下文

## 当前任务
{task_description}

## 相关模块
{self._format_relevant_modules(relevant_modules)}

## 相关文件
{self._format_relevant_files(relevant_files)}

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
