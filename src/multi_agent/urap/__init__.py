"""
U.R.A.P v4.0 - 通用逆向分析与智能文档构建协议

核心设计哲学：
1. 动态自适应 - 基于项目指纹动态调整分析策略
2. 工具智能决策 - 选择最直接解决问题的工具
3. 全景知识观 - 宏观有全貌，微观有细节

工作流程：
Phase 1: 环境指纹识别 -> 技术栈指纹报告
Phase 2: 智能策略生成 -> 分析策略声明+文档规划
Phase 3: 文档架构设计 -> 文档骨架+导航索引
Phase 4: 执行与知识填充 -> 完整文档体系
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Callable, Any
from pathlib import Path
import os
import re


class ProjectType(Enum):
    """项目类型"""
    MVC_FRAMEWORK = "mvc_framework"
    SCRIPT_EMBEDDED = "script_embedded"
    LEGACY_CODE = "legacy_code"
    MICROSERVICE = "microservice"
    FRONTEND = "frontend"
    DATA_PIPELINE = "data_pipeline"
    UNKNOWN = "unknown"


class AnalysisStrategy(Enum):
    """分析策略"""
    ROUTE_MAPPING = "route_mapping"
    ENTRY_DRIVEN = "entry_driven"
    DATA_FLOW_DRIVEN = "data_flow_driven"
    SERVICE_BOUNDARY = "service_boundary"
    COMPONENT_TREE = "component_tree"
    HYBRID = "hybrid"


@dataclass
class TechStackFingerprint:
    """技术栈指纹"""
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    databases: list[str] = field(default_factory=list)
    build_tools: list[str] = field(default_factory=list)
    runtimes: list[str] = field(default_factory=list)
    package_managers: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "languages": self.languages,
            "frameworks": self.frameworks,
            "databases": self.databases,
            "build_tools": self.build_tools,
            "runtimes": self.runtimes,
            "package_managers": self.package_managers,
        }


@dataclass
class EnvironmentFingerprint:
    """环境指纹"""
    project_type: ProjectType = ProjectType.UNKNOWN
    tech_stack: TechStackFingerprint = field(default_factory=TechStackFingerprint)
    root_path: str = ""
    has_docker: bool = False
    has_tests: bool = False
    has_docs: bool = False
    entry_points: list[str] = field(default_factory=list)
    config_files: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "project_type": self.project_type.value,
            "tech_stack": self.tech_stack.to_dict(),
            "root_path": self.root_path,
            "has_docker": self.has_docker,
            "has_tests": self.has_tests,
            "has_docs": self.has_docs,
            "entry_points": self.entry_points,
            "config_files": self.config_files,
        }


@dataclass
class AnalysisPlan:
    """分析计划"""
    strategy: AnalysisStrategy = AnalysisStrategy.HYBRID
    entry_point: str = ""
    tracking_targets: list[str] = field(default_factory=list)
    document_plan: list[str] = field(default_factory=list)
    estimated_complexity: str = "medium"
    
    def to_dict(self) -> dict:
        return {
            "strategy": self.strategy.value,
            "entry_point": self.entry_point,
            "tracking_targets": self.tracking_targets,
            "document_plan": self.document_plan,
            "estimated_complexity": self.estimated_complexity,
        }


@dataclass
class DocumentStructure:
    """文档结构"""
    master_doc: str = "00_SYSTEM_OVERVIEW.md"
    sub_docs: list[str] = field(default_factory=list)
    created_files: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "master_doc": self.master_doc,
            "sub_docs": self.sub_docs,
            "created_files": self.created_files,
        }


class EnvironmentProfiler:
    """
    Phase 1: 环境指纹识别
    
    扫描项目配置文件、构建脚本、依赖清单，识别技术栈指纹。
    """
    
    CONFIG_PATTERNS = {
        "python": ["requirements.txt", "setup.py", "pyproject.toml", "Pipfile", "poetry.lock"],
        "node": ["package.json", "yarn.lock", "pnpm-lock.yaml"],
        "java": ["pom.xml", "build.gradle", "gradlew", "mvnw"],
        "go": ["go.mod", "go.sum"],
        "rust": ["Cargo.toml", "Cargo.lock"],
        "ruby": ["Gemfile", "Gemfile.lock"],
        "php": ["composer.json", "composer.lock"],
        "dotnet": ["*.csproj", "*.sln"],
    }
    
    FRAMEWORK_SIGNATURES = {
        "spring": ["pom.xml", "build.gradle"],
        "django": ["settings.py", "wsgi.py"],
        "flask": ["app.py", "wsgi.py"],
        "fastapi": ["main.py", "app/main.py"],
        "react": ["package.json"],
        "vue": ["package.json"],
        "angular": ["angular.json"],
        "next": ["next.config.js"],
        "express": ["package.json"],
    }
    
    DATABASE_SIGNATURES = {
        "mysql": ["mysql", "mariadb"],
        "postgresql": ["postgres", "psql", "pg"],
        "mongodb": ["mongo", "mongodb"],
        "redis": ["redis"],
        "sqlite": ["sqlite", ".db", ".sqlite"],
        "elasticsearch": ["elasticsearch", "elastic"],
    }
    
    def __init__(self, output_callback: Optional[Callable[[str, str], None]] = None):
        self.output_callback = output_callback
    
    def _log(self, level: str, message: str) -> None:
        if self.output_callback:
            self.output_callback(level, message)
    
    def profile(self, project_path: str) -> EnvironmentFingerprint:
        """
        执行环境指纹识别
        
        Args:
            project_path: 项目根目录路径
            
        Returns:
            EnvironmentFingerprint: 环境指纹对象
        """
        self._log("info", f"开始环境指纹识别: {project_path}")
        
        fingerprint = EnvironmentFingerprint(root_path=project_path)
        path = Path(project_path)
        
        if not path.exists():
            self._log("error", f"项目路径不存在: {project_path}")
            return fingerprint
        
        fingerprint.tech_stack = self._identify_tech_stack(path)
        fingerprint.project_type = self._determine_project_type(fingerprint.tech_stack)
        fingerprint.has_docker = self._check_docker(path)
        fingerprint.has_tests = self._check_tests(path)
        fingerprint.has_docs = self._check_docs(path)
        fingerprint.entry_points = self._find_entry_points(path, fingerprint.tech_stack)
        fingerprint.config_files = self._find_config_files(path)
        
        self._log("complete", f"环境指纹识别完成: {fingerprint.project_type.value}")
        
        return fingerprint
    
    def _identify_tech_stack(self, path: Path) -> TechStackFingerprint:
        """识别技术栈"""
        tech_stack = TechStackFingerprint()
        
        for lang, patterns in self.CONFIG_PATTERNS.items():
            for pattern in patterns:
                matches = list(path.glob(f"**/{pattern}"))
                if matches:
                    tech_stack.languages.append(lang)
                    if lang not in tech_stack.package_managers:
                        tech_stack.package_managers.append(lang)
                    break
        
        for framework, signatures in self.FRAMEWORK_SIGNATURES.items():
            for sig in signatures:
                matches = list(path.glob(f"**/{sig}"))
                if matches:
                    tech_stack.frameworks.append(framework)
                    break
        
        all_files = list(path.rglob("*"))
        file_contents = ""
        for f in all_files[:50]:
            if f.is_file() and f.suffix in [".py", ".js", ".ts", ".java", ".go", ".json", ".yaml", ".yml", ".xml"]:
                try:
                    content = f.read_text(encoding="utf-8", errors="ignore")
                    file_contents += content.lower()
                except:
                    pass
        
        for db, keywords in self.DATABASE_SIGNATURES.items():
            for keyword in keywords:
                if keyword.lower() in file_contents:
                    tech_stack.databases.append(db)
                    break
        
        docker_files = list(path.glob("**/Dockerfile*")) + list(path.glob("**/docker-compose*"))
        if docker_files:
            tech_stack.build_tools.append("docker")
        
        tech_stack.languages = list(set(tech_stack.languages))
        tech_stack.frameworks = list(set(tech_stack.frameworks))
        tech_stack.databases = list(set(tech_stack.databases))
        tech_stack.build_tools = list(set(tech_stack.build_tools))
        
        return tech_stack
    
    def _determine_project_type(self, tech_stack: TechStackFingerprint) -> ProjectType:
        """确定项目类型"""
        frameworks = [f.lower() for f in tech_stack.frameworks]
        languages = [l.lower() for l in tech_stack.languages]
        
        if any(f in frameworks for f in ["spring", "django", "flask", "fastapi", "express"]):
            return ProjectType.MVC_FRAMEWORK
        
        if any(f in frameworks for f in ["react", "vue", "angular", "next"]):
            return ProjectType.FRONTEND
        
        if "python" in languages and not frameworks:
            return ProjectType.SCRIPT_EMBEDDED
        
        if "java" in languages and "spring" not in frameworks:
            return ProjectType.LEGACY_CODE
        
        if any(f in frameworks for f in ["microservice", "grpc"]):
            return ProjectType.MICROSERVICE
        
        return ProjectType.UNKNOWN
    
    def _check_docker(self, path: Path) -> bool:
        """检查是否有Docker配置"""
        docker_files = list(path.glob("**/Dockerfile*")) + list(path.glob("**/docker-compose*"))
        return len(docker_files) > 0
    
    def _check_tests(self, path: Path) -> bool:
        """检查是否有测试"""
        test_dirs = list(path.glob("**/test*")) + list(path.glob("**/*test*"))
        test_files = list(path.glob("**/*_test.py")) + list(path.glob("**/*.test.js")) + list(path.glob("**/*Test.java"))
        return len(test_dirs) > 0 or len(test_files) > 0
    
    def _check_docs(self, path: Path) -> bool:
        """检查是否有文档"""
        doc_files = list(path.glob("**/*.md")) + list(path.glob("**/docs/*"))
        return len(doc_files) > 0
    
    def _find_entry_points(self, path: Path, tech_stack: TechStackFingerprint) -> list[str]:
        """查找入口点"""
        entry_points = []
        
        entry_patterns = [
            "main.py", "app.py", "run.py", "server.py", "wsgi.py", "asgi.py",
            "index.js", "app.js", "server.js", "main.js",
            "Main.java", "Application.java",
            "main.go",
            "index.ts", "main.ts", "app.ts",
        ]
        
        for pattern in entry_patterns:
            matches = list(path.glob(f"**/{pattern}"))
            entry_points.extend([str(m.relative_to(path)) for m in matches])
        
        return list(set(entry_points))
    
    def _find_config_files(self, path: Path) -> list[str]:
        """查找配置文件"""
        config_patterns = [
            "*.json", "*.yaml", "*.yml", "*.toml", "*.ini", "*.cfg",
            ".env*", "config/*", "settings/*",
        ]
        
        config_files = []
        for pattern in config_patterns:
            matches = list(path.glob(f"**/{pattern}"))
            config_files.extend([str(m.relative_to(path)) for m in matches[:10]])
        
        return list(set(config_files))


class StrategyGenerator:
    """
    Phase 2: 智能策略生成
    
    基于技术栈指纹动态生成分析方案。
    """
    
    STRATEGY_MATRIX = {
        ProjectType.MVC_FRAMEWORK: {
            "strategy": AnalysisStrategy.ROUTE_MAPPING,
            "entry_pattern": "Controller层路由",
            "tracking": ["Controller -> Service -> Repository"],
        },
        ProjectType.SCRIPT_EMBEDDED: {
            "strategy": AnalysisStrategy.ENTRY_DRIVEN,
            "entry_pattern": "Main函数/启动脚本",
            "tracking": ["函数调用链"],
        },
        ProjectType.LEGACY_CODE: {
            "strategy": AnalysisStrategy.DATA_FLOW_DRIVEN,
            "entry_pattern": "核心数据结构",
            "tracking": ["Struct/Class传递路径"],
        },
        ProjectType.MICROSERVICE: {
            "strategy": AnalysisStrategy.SERVICE_BOUNDARY,
            "entry_pattern": "API Gateway",
            "tracking": ["服务间依赖", "数据流向"],
        },
        ProjectType.FRONTEND: {
            "strategy": AnalysisStrategy.COMPONENT_TREE,
            "entry_pattern": "根组件/入口文件",
            "tracking": ["组件层级", "状态管理流"],
        },
    }
    
    DOCUMENT_TEMPLATES = {
        "master": "00_SYSTEM_OVERVIEW.md",
        "flows": "01_CORE_FLOWS.md",
        "api": "02_API_DICTIONARY.md",
        "data": "03_DATA_SCHEMA.md",
        "dev_notes": "04_DEV_NOTES.md",
    }
    
    def __init__(self, output_callback: Optional[Callable[[str, str], None]] = None):
        self.output_callback = output_callback
    
    def _log(self, level: str, message: str) -> None:
        if self.output_callback:
            self.output_callback(level, message)
    
    def generate(self, fingerprint: EnvironmentFingerprint) -> AnalysisPlan:
        """
        生成分析计划
        
        Args:
            fingerprint: 环境指纹
            
        Returns:
            AnalysisPlan: 分析计划
        """
        self._log("info", f"开始生成分析策略: {fingerprint.project_type.value}")
        
        plan = AnalysisPlan()
        
        strategy_config = self.STRATEGY_MATRIX.get(
            fingerprint.project_type,
            {"strategy": AnalysisStrategy.HYBRID, "entry_pattern": "项目根目录", "tracking": ["全量分析"]}
        )
        
        plan.strategy = strategy_config["strategy"]
        plan.tracking_targets = strategy_config["tracking"]
        
        if fingerprint.entry_points:
            plan.entry_point = fingerprint.entry_points[0]
        else:
            plan.entry_point = strategy_config["entry_pattern"]
        
        plan.document_plan = self._generate_document_plan(fingerprint)
        plan.estimated_complexity = self._estimate_complexity(fingerprint)
        
        self._log("complete", f"分析策略生成完成: {plan.strategy.value}")
        
        return plan
    
    def _generate_document_plan(self, fingerprint: EnvironmentFingerprint) -> list[str]:
        """生成文档规划"""
        docs = [self.DOCUMENT_TEMPLATES["master"]]
        
        if fingerprint.project_type in [ProjectType.MVC_FRAMEWORK, ProjectType.MICROSERVICE]:
            docs.append(self.DOCUMENT_TEMPLATES["flows"])
            docs.append(self.DOCUMENT_TEMPLATES["api"])
        
        if fingerprint.tech_stack.databases:
            docs.append(self.DOCUMENT_TEMPLATES["data"])
        
        if fingerprint.project_type == ProjectType.LEGACY_CODE:
            docs.append(self.DOCUMENT_TEMPLATES["dev_notes"])
        
        return docs
    
    def _estimate_complexity(self, fingerprint: EnvironmentFingerprint) -> str:
        """评估复杂度"""
        score = 0
        
        score += len(fingerprint.tech_stack.languages) * 2
        score += len(fingerprint.tech_stack.frameworks) * 3
        score += len(fingerprint.tech_stack.databases) * 2
        
        if fingerprint.has_docker:
            score += 2
        if fingerprint.has_tests:
            score += 1
        
        if score < 5:
            return "low"
        elif score < 15:
            return "medium"
        else:
            return "high"


class DocumentArchitect:
    """
    Phase 3: 文档架构设计
    
    建立分层文档体系，确保宏观有全貌、微观有细节。
    """
    
    MASTER_TEMPLATE = """# {project_name} 系统概览

> 本文档由 U.R.A.P v4.0 自动生成

## 系统定位

{system_description}

## 技术全景

### 编程语言
{languages}

### 框架/基座
{frameworks}

### 数据/中间件
{databases}

### 构建/部署
{build_tools}

## 目录拓扑

```
{directory_structure}
```

## 文档索引

{doc_index}

---
*生成时间: {timestamp}*
"""

    FLOWS_TEMPLATE = """# 核心流程文档

> 本文档记录系统的核心业务流程

## 流程概览

{flow_overview}

## 详细流程

{flow_details}

## 时序图

```
{sequence_diagram}
```

---
*生成时间: {timestamp}*
"""

    API_TEMPLATE = """# API字典

> 本文档记录系统的对外接口定义

## 接口列表

{api_list}

## 详细定义

{api_details}

---
*生成时间: {timestamp}*
"""

    DATA_TEMPLATE = """# 数据结构文档

> 本文档记录系统的数据模型和结构

## 数据模型

{data_models}

## 关系图

```
{relationship_diagram}
```

---
*生成时间: {timestamp}*
"""

    DEV_NOTES_TEMPLATE = """# 开发笔记

> 本文档记录系统的设计模式和实现细节

## 设计模式

{design_patterns}

## 技术亮点

{highlights}

## 配置说明

{config_notes}

---
*生成时间: {timestamp}*
"""

    def __init__(self, output_callback: Optional[Callable[[str, str], None]] = None):
        self.output_callback = output_callback
    
    def _log(self, level: str, message: str) -> None:
        if self.output_callback:
            self.output_callback(level, message)
    
    def design(
        self,
        fingerprint: EnvironmentFingerprint,
        plan: AnalysisPlan,
        output_dir: str,
    ) -> DocumentStructure:
        """
        设计文档架构
        
        Args:
            fingerprint: 环境指纹
            plan: 分析计划
            output_dir: 输出目录
            
        Returns:
            DocumentStructure: 文档结构
        """
        self._log("info", "开始设计文档架构")
        
        structure = DocumentStructure()
        docs_path = Path(output_dir) / "docs"
        docs_path.mkdir(parents=True, exist_ok=True)
        
        structure.master_doc = self._create_master_doc(docs_path, fingerprint, plan)
        structure.created_files.append(structure.master_doc)
        
        for doc_name in plan.document_plan:
            if doc_name != structure.master_doc:
                doc_path = self._create_sub_doc(docs_path, doc_name, fingerprint)
                if doc_path:
                    structure.sub_docs.append(doc_path)
                    structure.created_files.append(doc_path)
        
        self._log("complete", f"文档架构设计完成，创建了 {len(structure.created_files)} 个文档")
        
        return structure
    
    def _create_master_doc(
        self,
        docs_path: Path,
        fingerprint: EnvironmentFingerprint,
        plan: AnalysisPlan,
    ) -> str:
        """创建主记录文档"""
        from datetime import datetime
        
        project_name = Path(fingerprint.root_path).name
        
        content = self.MASTER_TEMPLATE.format(
            project_name=project_name,
            system_description=f"项目类型: {fingerprint.project_type.value}",
            languages="\n".join([f"- {lang}" for lang in fingerprint.tech_stack.languages]) or "- 未识别",
            frameworks="\n".join([f"- {fw}" for fw in fingerprint.tech_stack.frameworks]) or "- 未识别",
            databases="\n".join([f"- {db}" for db in fingerprint.tech_stack.databases]) or "- 未识别",
            build_tools="\n".join([f"- {bt}" for bt in fingerprint.tech_stack.build_tools]) or "- 未识别",
            directory_structure="项目目录结构待分析...",
            doc_index="\n".join([f"- [{doc}]({doc})" for doc in plan.document_plan]),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        
        doc_path = docs_path / "00_SYSTEM_OVERVIEW.md"
        doc_path.write_text(content, encoding="utf-8")
        
        return str(doc_path)
    
    def _create_sub_doc(
        self,
        docs_path: Path,
        doc_name: str,
        fingerprint: EnvironmentFingerprint,
    ) -> Optional[str]:
        """创建子文档"""
        from datetime import datetime
        
        templates = {
            "01_CORE_FLOWS.md": self.FLOWS_TEMPLATE,
            "02_API_DICTIONARY.md": self.API_TEMPLATE,
            "03_DATA_SCHEMA.md": self.DATA_TEMPLATE,
            "04_DEV_NOTES.md": self.DEV_NOTES_TEMPLATE,
        }
        
        template = templates.get(doc_name)
        if not template:
            return None
        
        content = template.format(
            flow_overview="待分析...",
            flow_details="待分析...",
            sequence_diagram="待分析...",
            api_list="待分析...",
            api_details="待分析...",
            data_models="待分析...",
            relationship_diagram="待分析...",
            design_patterns="待分析...",
            highlights="待分析...",
            config_notes="待分析...",
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        
        doc_path = docs_path / doc_name
        doc_path.write_text(content, encoding="utf-8")
        
        return str(doc_path)


class URAPAnalyzer:
    """
    U.R.A.P 分析器
    
    整合四个阶段的分析流程：
    1. 环境指纹识别
    2. 智能策略生成
    3. 文档架构设计
    4. 执行与知识填充
    """
    
    def __init__(self, output_callback: Optional[Callable[[str, str, str], None]] = None):
        self.output_callback = output_callback
        
        def _wrap_callback(level: str, message: str) -> None:
            if output_callback:
                output_callback("urap", level, message)
        
        self.profiler = EnvironmentProfiler(_wrap_callback)
        self.strategy_generator = StrategyGenerator(_wrap_callback)
        self.document_architect = DocumentArchitect(_wrap_callback)
    
    async def analyze(
        self,
        project_path: str,
        output_dir: Optional[str] = None,
    ) -> dict:
        """
        执行完整的URAP分析
        
        Args:
            project_path: 项目路径
            output_dir: 输出目录（默认为项目路径下的docs目录）
            
        Returns:
            分析结果字典
        """
        if output_callback := self.output_callback:
            output_callback("urap", "info", f"开始URAP分析: {project_path}")
        
        fingerprint = self.profiler.profile(project_path)
        
        plan = self.strategy_generator.generate(fingerprint)
        
        if output_dir is None:
            output_dir = project_path
        
        structure = self.document_architect.design(fingerprint, plan, output_dir)
        
        result = {
            "success": True,
            "fingerprint": fingerprint.to_dict(),
            "plan": plan.to_dict(),
            "documents": structure.to_dict(),
            "project_path": project_path,
            "output_dir": output_dir,
        }
        
        if output_callback := self.output_callback:
            output_callback("urap", "complete", "URAP分析完成")
        
        return result
    
    def get_tool_recommendation(self, task_type: str) -> dict:
        """
        获取工具推荐
        
        Args:
            task_type: 任务类型
            
        Returns:
            工具推荐字典
        """
        recommendations = {
            "read_code": {"primary": "Read", "fallback": "Grep"},
            "find_files": {"primary": "Glob", "fallback": "Bash find"},
            "search_content": {"primary": "Grep", "fallback": "Read + 手动查找"},
            "modify_file": {"primary": "Edit", "fallback": "Write"},
            "deep_thinking": {"primary": "Sequential Thinking", "fallback": None},
            "query_docs": {"primary": "Context7", "fallback": "WebSearch"},
            "analyze_image": {"primary": "ZAI analyze_image", "fallback": "手动查看"},
            "generate_word": {"primary": "Skill docx", "fallback": "Write (Markdown)"},
            "complex_problem": {"primary": "Aurai-Advisor", "fallback": "Context7"},
        }
        
        return recommendations.get(task_type, {"primary": "Unknown", "fallback": None})
