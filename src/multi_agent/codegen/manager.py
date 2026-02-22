"""
Code manager for saving and organizing generated code files.

文件组织规范：
1. 支持用户自定义输出目录
2. 按文件类型自动分类（backend/frontend/config/tests/docs/scripts）
3. 智能检测文件路径并保存到正确位置
4. 支持相对路径和绝对路径
"""

import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable
from enum import Enum


class FileCategory(Enum):
    """文件分类"""
    BACKEND = "backend"
    FRONTEND = "frontend"
    CONFIG = "config"
    TESTS = "tests"
    DOCS = "docs"
    SCRIPTS = "scripts"
    DATABASE = "database"
    OTHER = "other"


@dataclass
class CodeFile:
    """Represents a generated code file."""
    
    path: str
    content: str
    language: str
    category: FileCategory = FileCategory.OTHER
    description: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def get_relative_path(self, base_dir: str) -> str:
        """获取相对于基础目录的路径"""
        return os.path.relpath(self.path, base_dir)


class FileClassifier:
    """文件分类器 - 根据文件名和内容判断文件类型"""
    
    BACKEND_PATTERNS = {
        'api': FileCategory.BACKEND,
        'app': FileCategory.BACKEND,
        'main': FileCategory.BACKEND,
        'server': FileCategory.BACKEND,
        'router': FileCategory.BACKEND,
        'model': FileCategory.BACKEND,
        'schema': FileCategory.BACKEND,
        'service': FileCategory.BACKEND,
        'controller': FileCategory.BACKEND,
        'middleware': FileCategory.BACKEND,
        'utils': FileCategory.BACKEND,
        'helpers': FileCategory.BACKEND,
    }
    
    FRONTEND_PATTERNS = {
        'component': FileCategory.FRONTEND,
        'page': FileCategory.FRONTEND,
        'hook': FileCategory.FRONTEND,
        'context': FileCategory.FRONTEND,
        'style': FileCategory.FRONTEND,
        'layout': FileCategory.FRONTEND,
    }
    
    TEST_PATTERNS = {
        'test': FileCategory.TESTS,
        'spec': FileCategory.TESTS,
    }
    
    CONFIG_FILES = {
        'config': FileCategory.CONFIG,
        'settings': FileCategory.CONFIG,
        'env': FileCategory.CONFIG,
        'requirements': FileCategory.CONFIG,
        'package': FileCategory.CONFIG,
        'dockerfile': FileCategory.CONFIG,
        'docker-compose': FileCategory.CONFIG,
    }
    
    @classmethod
    def classify(cls, filename: str, content: str = "", language: str = "") -> FileCategory:
        """根据文件名和内容判断文件类型"""
        filename_lower = filename.lower()
        name_without_ext = os.path.splitext(filename_lower)[0]
        
        for pattern, category in cls.TEST_PATTERNS.items():
            if pattern in name_without_ext:
                return FileCategory.TESTS
        
        for pattern, category in cls.BACKEND_PATTERNS.items():
            if pattern in name_without_ext:
                return category
        
        for pattern, category in cls.FRONTEND_PATTERNS.items():
            if pattern in name_without_ext:
                return category
        
        for pattern, category in cls.CONFIG_FILES.items():
            if pattern in name_without_ext:
                return FileCategory.CONFIG
        
        if language.lower() in ['python', 'py']:
            if 'test' in content.lower()[:500]:
                return FileCategory.TESTS
            return FileCategory.BACKEND
        elif language.lower() in ['javascript', 'typescript', 'jsx', 'tsx']:
            if 'component' in content.lower()[:500]:
                return FileCategory.FRONTEND
            return FileCategory.FRONTEND
        
        return FileCategory.OTHER


class CodeManager:
    """
    Manages saving and organizing generated code files.
    
    Features:
    - Extracts code blocks from LLM responses
    - Saves files to appropriate directories
    - Maintains project structure
    - Tracks generated files
    """
    
    def __init__(self, output_dir: str = "./output"):
        self.output_dir = Path(output_dir)
        self.files: list[CodeFile] = []
        self._ensure_output_dir()
    
    def _ensure_output_dir(self) -> None:
        """Ensure output directory exists."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_code_blocks(self, text: str) -> list[dict]:
        """
        Extract code blocks from LLM response.
        
        Args:
            text: The text containing code blocks
            
        Returns:
            List of dicts with 'language', 'code', and optional 'path'
        """
        blocks = []
        
        # Pattern to match code blocks with optional file path
        # ```language
        # // path/to/file.ext
        # code...
        # ```
        pattern = r'```(\w+)?\s*\n(.*?)```'
        
        matches = re.findall(pattern, text, re.DOTALL)
        
        for lang, code in matches:
            if not lang:
                lang = "text"
            
            code = code.strip()
            
            # Try to extract file path from first line comment
            path = None
            lines = code.split('\n')
            if lines:
                first_line = lines[0].strip()
                # Match various comment styles for file paths
                path_patterns = [
                    r'^//\s*(.+?\.\w+)\s*$',
                    r'^#\s*(.+?\.\w+)\s*$',
                    r'^<!--\s*(.+?\.\w+)\s*-->$',
                    r'^/\*\s*(.+?\.\w+)\s*\*/$',
                    r'^\*\s*(.+?\.\w+)\s*$',
                ]
                
                for p in path_patterns:
                    match = re.match(p, first_line)
                    if match:
                        path = match.group(1).strip()
                        # Remove the path line from code
                        code = '\n'.join(lines[1:]).strip()
                        break
            
            blocks.append({
                'language': lang,
                'code': code,
                'path': path,
            })
        
        return blocks
    
    def save_code_block(
        self,
        code: str,
        language: str,
        filename: str,
        sub_dir: Optional[str] = None,
        description: str = "",
    ) -> str:
        """
        Save a code block to a file.
        
        Args:
            code: The code content
            language: Programming language
            filename: Output filename
            sub_dir: Optional subdirectory
            description: File description
            
        Returns:
            The full path to the saved file
        """
        if sub_dir:
            target_dir = self.output_dir / sub_dir
        else:
            target_dir = self.output_dir
        
        target_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = target_dir / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(code)
        
        code_file = CodeFile(
            path=str(file_path),
            content=code,
            language=language,
            description=description,
        )
        self.files.append(code_file)
        
        return str(file_path)
    
    def save_from_response(
        self,
        response: str,
        task_name: str = "",
    ) -> list[str]:
        """
        Extract and save all code blocks from an LLM response.
        
        Args:
            response: The LLM response text
            task_name: Name of the task (for organizing)
            
        Returns:
            List of saved file paths
        """
        blocks = self.extract_code_blocks(response)
        saved_paths = []
        
        for i, block in enumerate(blocks):
            code = block['code']
            language = block['language']
            path = block['path']
            
            if path:
                # Use the path from the code comment
                filename = os.path.basename(path)
                sub_dir = os.path.dirname(path)
            else:
                # Generate a filename
                ext = self._get_extension(language)
                filename = f"{task_name}_{i+1}{ext}" if task_name else f"code_{i+1}{ext}"
                sub_dir = None
            
            saved_path = self.save_code_block(
                code=code,
                language=language,
                filename=filename,
                sub_dir=sub_dir,
                description=f"Generated from task: {task_name}",
            )
            saved_paths.append(saved_path)
        
        return saved_paths
    
    def _get_extension(self, language: str) -> str:
        """Get file extension for a language."""
        extensions = {
            'python': '.py',
            'javascript': '.js',
            'typescript': '.ts',
            'tsx': '.tsx',
            'jsx': '.jsx',
            'java': '.java',
            'go': '.go',
            'rust': '.rs',
            'c': '.c',
            'cpp': '.cpp',
            'csharp': '.cs',
            'ruby': '.rb',
            'php': '.php',
            'swift': '.swift',
            'kotlin': '.kt',
            'scala': '.scala',
            'html': '.html',
            'css': '.css',
            'scss': '.scss',
            'sass': '.sass',
            'less': '.less',
            'json': '.json',
            'yaml': '.yaml',
            'yml': '.yml',
            'xml': '.xml',
            'sql': '.sql',
            'sh': '.sh',
            'bash': '.sh',
            'dockerfile': '.dockerfile',
            'docker': '.dockerfile',
            'markdown': '.md',
            'md': '.md',
        }
        return extensions.get(language.lower(), '.txt')
    
    def create_project_structure(
        self,
        project_name: str,
        tech_stack: dict,
    ) -> dict:
        """
        Initialize the project directory.
        
        只创建项目根目录，不提前创建子目录结构。
        子目录会在代码生成时根据需要自动创建。
        
        Args:
            project_name: Name of the project
            tech_stack: Technology stack configuration
            
        Returns:
            Dict with project info
        """
        project_dir = self.output_dir
        project_dir.mkdir(parents=True, exist_ok=True)
        
        return {
            'project_dir': str(project_dir),
            'project_name': project_name,
            'directories': [],
            'files': [],
        }
    
    def generate_readme(
        self,
        project_name: str,
        tech_stack: dict,
        description: str = "",
    ) -> str:
        """
        Generate README.md based on actual files in the output directory.
        
        直接扫描工作目录中的实际文件生成README，不依赖self.files列表。
        
        Args:
            project_name: Name of the project
            tech_stack: Technology stack configuration
            description: Project description
            
        Returns:
            Path to the generated README.md
        """
        actual_files = self._scan_actual_files()
        
        file_list = []
        for f in actual_files:
            rel_path = os.path.relpath(f, self.output_dir)
            file_list.append(f"- `{rel_path}`")
        
        tech_info = ""
        if tech_stack:
            tech_info = f"""
## Tech Stack
- Frontend: {tech_stack.get('frontend', 'Not specified')}
- Backend: {tech_stack.get('backend', 'Not specified')}
- Database: {tech_stack.get('database', 'Not specified')}
"""
        
        structure_tree = self._generate_structure_tree_from_paths(actual_files)
        
        main_file = self._find_main_file_from_paths(actual_files)
        
        readme_content = f"""# {project_name}

{description if description else 'Generated by Multi-Agent System'}
{tech_info}
## Files Generated

{chr(10).join(file_list) if file_list else 'No files generated yet.'}

## Project Structure

```
{project_name}/
{structure_tree}
```

## Getting Started

```bash
# Navigate to project directory
cd {self.output_dir}

# Install dependencies (if requirements.txt exists)
pip install -r requirements.txt

# Run the application
python {main_file}
```

---
*Generated by Multi-Agent System*
"""
        
        readme_path = self.output_dir / 'README.md'
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        return str(readme_path)
    
    def _scan_actual_files(self) -> list[str]:
        """Scan actual files in the output directory."""
        code_extensions = {'.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.go', '.rs', 
                          '.html', '.css', '.scss', '.json', '.yaml', '.yml', '.sh', '.sql'}
        
        ignore_patterns = {'__pycache__', '.git', 'node_modules', '.venv', 'venv', '.env'}
        
        files = []
        
        if self.output_dir.exists():
            for file_path in self.output_dir.rglob('*'):
                if file_path.is_file():
                    rel_path = file_path.relative_to(self.output_dir)
                    if any(ignore in rel_path.parts for ignore in ignore_patterns):
                        continue
                    if file_path.suffix.lower() in code_extensions:
                        files.append(str(file_path))
        
        return sorted(files)
    
    def _find_main_file_from_paths(self, file_paths: list[str]) -> str:
        """Find the main entry file from file paths."""
        for f in file_paths:
            if 'main.py' in f.lower():
                return os.path.relpath(f, self.output_dir)
            if 'app.py' in f.lower():
                return os.path.relpath(f, self.output_dir)
        for f in file_paths:
            if f.endswith('.py'):
                return os.path.relpath(f, self.output_dir)
        return "main.py"
    
    def _generate_structure_tree_from_paths(self, file_paths: list[str]) -> str:
        """Generate structure tree from file paths."""
        dirs = set()
        files = set()
        
        for f in file_paths:
            rel_path = os.path.relpath(f, self.output_dir)
            parts = Path(rel_path).parts
            
            for i, part in enumerate(parts[:-1]):
                dirs.add(tuple(parts[:i+1]))
            
            files.add(rel_path)
        
        lines = []
        sorted_dirs = sorted(dirs)
        sorted_files = sorted(files)
        
        dir_printed = set()
        for d in sorted_dirs:
            indent = "  " * (len(d) - 1)
            dir_name = d[-1]
            if d not in dir_printed:
                lines.append(f"{indent}├── {dir_name}/")
                dir_printed.add(d)
        
        for f in sorted_files:
            parts = Path(f).parts
            if len(parts) > 1:
                indent = "  " * (len(parts) - 1)
                lines.append(f"{indent}├── {parts[-1]}")
            else:
                lines.append(f"├── {parts[0]}")
        
        if not lines:
            lines.append("└── (empty)")
        
        return "\n".join(lines)
    
    def _find_main_file(self, files: list) -> str:
        """Find the main entry file."""
        for f in files:
            if 'main.py' in f.path.lower():
                return os.path.relpath(f.path, self.output_dir)
            if 'app.py' in f.path.lower():
                return os.path.relpath(f.path, self.output_dir)
        for f in files:
            if f.path.endswith('.py'):
                return os.path.relpath(f.path, self.output_dir)
        return "main.py"
    
    def _get_actual_directory_structure(self) -> dict:
        """Get the actual directory structure."""
        structure = {}
        for f in self.files:
            rel_path = os.path.relpath(f.path, self.output_dir)
            parts = Path(rel_path).parts
            current = structure
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
        return structure
    
    def _generate_structure_tree(self, files: list = None, prefix: str = "") -> str:
        """Generate a tree representation of the actual directory structure."""
        files = files or self.files
        
        dirs = set()
        file_set = set()
        
        seen_paths = set()
        for f in files:
            if f.path in seen_paths:
                continue
            seen_paths.add(f.path)
            
            rel_path = os.path.relpath(f.path, self.output_dir)
            parts = Path(rel_path).parts
            
            for i, part in enumerate(parts[:-1]):
                dirs.add(tuple(parts[:i+1]))
            
            file_set.add(rel_path)
        
        lines = []
        sorted_dirs = sorted(dirs)
        sorted_files = sorted(file_set)
        
        dir_printed = set()
        for d in sorted_dirs:
            indent = "  " * (len(d) - 1)
            dir_name = d[-1]
            if d not in dir_printed:
                lines.append(f"{indent}├── {dir_name}/")
                dir_printed.add(d)
        
        for f in sorted_files:
            parts = Path(f).parts
            if len(parts) > 1:
                indent = "  " * (len(parts) - 1)
                lines.append(f"{indent}├── {parts[-1]}")
            else:
                lines.append(f"├── {parts[0]}")
        
        if not lines:
            lines.append("└── (empty)")
        
        return "\n".join(lines)
    
    def get_summary(self) -> dict:
        """Get summary of generated files."""
        return {
            'total_files': len(self.files),
            'files': [
                {
                    'path': f.path,
                    'language': f.language,
                    'lines': len(f.content.split('\n')),
                    'description': f.description,
                }
                for f in self.files
            ],
        }
    
    def get_all_code(self) -> str:
        """Get all generated code as a single string."""
        parts = []
        for f in self.files:
            parts.append(f"\n\n# {'='*50}\n# File: {f.path}\n# {'='*50}\n\n{f.content}")
        return '\n'.join(parts)
