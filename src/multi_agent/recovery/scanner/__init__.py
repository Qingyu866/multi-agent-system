"""项目扫描模块

提供项目文件扫描和上下文生成功能：
1. ProjectScanner - 扫描项目文件和结构
2. ContextSummarizer - 生成项目上下文摘要
3. 智能识别模块和技术栈

使用方式:
    from multi_agent.recovery.scanner import ProjectScanner, ContextSummarizer
    
    # 扫描项目
    scanner = ProjectScanner('./my-project')
    context = scanner.scan()
    
    # 生成恢复上下文
    summarizer = ContextSummarizer(scanner)
    resume_context = summarizer.generate_resume_context(project_state)
"""

from multi_agent.recovery.scanner.project_scanner import (
    ProjectScanner,
    ProjectContext,
    ModuleInfo,
    FileInfo,
)
from multi_agent.recovery.scanner.context_summarizer import ContextSummarizer

__all__ = [
    "ProjectScanner",
    "ContextSummarizer",
    "ProjectContext",
    "ModuleInfo",
    "FileInfo",
]
