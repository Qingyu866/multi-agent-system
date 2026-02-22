"""项目扫描器

扫描项目目录结构和文件，识别：
1. 项目模块
2. 技术栈
3. 关键文件
4. 代码统计
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


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
