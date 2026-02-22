"""状态持久化和恢复核心模块"""

import json
import threading
import hashlib
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Callable
from enum import Enum
import re


class ProjectStatus(str, Enum):
    """项目状态"""
    RUNNING = "running"
    PAUSED = "paused"
    INTERRUPTED = "interrupted"
    COMPLETED = "completed"
    FAILED = "failed"


class InterruptReason(str, Enum):
    """中断原因"""
    API_LIMIT = "api_limit"
    NETWORK_ERROR = "network_error"
    CLI_ERROR = "cli_error"
    SYSTEM_CRASH = "system_crash"
    MANUAL_STOP = "manual_stop"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class TaskProgress:
    """任务进度"""
    task_id: str
    task_name: str
    status: str = "pending"
    progress: float = 0.0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    output_files: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Checkpoint:
    """检查点"""
    checkpoint_id: str
    timestamp: str
    project_status: str
    current_task_index: int
    total_tasks: int
    completed_tasks: list[str] = field(default_factory=list)
    pending_tasks: list[str] = field(default_factory=list)
    task_progress: dict[str, TaskProgress] = field(default_factory=dict)
    interrupt_reason: Optional[str] = None
    error_details: Optional[str] = None
    recovery_hint: Optional[str] = None
    
    def to_dict(self) -> dict:
        result = asdict(self)
        result["task_progress"] = {k: v.to_dict() for k, v in self.task_progress.items()}
        return result


@dataclass
class ProjectState:
    """项目状态"""
    project_id: str
    project_name: str
    output_dir: str
    status: ProjectStatus = ProjectStatus.RUNNING
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    checkpoints: list[Checkpoint] = field(default_factory=list)
    requirements: str = ""
    tech_stack: dict[str, str] = field(default_factory=dict)
    total_tasks: int = 0
    current_task_index: int = 0
    task_list: list[dict] = field(default_factory=list)
    generated_files: list[str] = field(default_factory=list)
    error_history: list[dict] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        result = asdict(self)
        result["status"] = self.status.value
        result["checkpoints"] = [c.to_dict() for c in self.checkpoints]
        return result


class StatePersistence:
    """状态持久化管理器"""
    
    STATE_DIR = ".multi_agent_state"
    STATE_FILE = "project_state.json"
    CHECKPOINT_DIR = "checkpoints"
    
    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self.state_dir = self.project_dir / self.STATE_DIR
        self.state_file = self.state_dir / self.STATE_FILE
        self.checkpoint_dir = self.state_dir / self.CHECKPOINT_DIR
        
        self._ensure_dirs()
        self._state: Optional[ProjectState] = None
        self._auto_save_thread: Optional[threading.Thread] = None
        self._stop_auto_save = threading.Event()
        self._lock = threading.Lock()
    
    def _ensure_dirs(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    def create_project(
        self,
        project_name: str,
        output_dir: str,
        requirements: str = "",
        tech_stack: dict[str, str] = None,
    ) -> ProjectState:
        project_id = self._generate_project_id(project_name)
        
        self._state = ProjectState(
            project_id=project_id,
            project_name=project_name,
            output_dir=output_dir,
            requirements=requirements,
            tech_stack=tech_stack or {},
        )
        
        self.save_state()
        return self._state
    
    def _generate_project_id(self, name: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hash_input = f"{name}_{timestamp}".encode()
        short_hash = hashlib.md5(hash_input).hexdigest()[:8]
        return f"proj_{timestamp}_{short_hash}"
    
    def load_state(self) -> Optional[ProjectState]:
        with self._lock:
            if not self.state_file.exists():
                return None
            
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                data["status"] = ProjectStatus(data.get("status", "running"))
                
                checkpoints = []
                for cp_data in data.get("checkpoints", []):
                    task_progress = {}
                    for tid, tp_data in cp_data.get("task_progress", {}).items():
                        task_progress[tid] = TaskProgress(**tp_data)
                    cp_data["task_progress"] = task_progress
                    checkpoints.append(Checkpoint(**cp_data))
                data["checkpoints"] = checkpoints
                
                self._state = ProjectState(**data)
                return self._state
            except Exception as e:
                print(f"加载状态失败: {e}")
                return None
    
    def save_state(self) -> None:
        with self._lock:
            if not self._state:
                return
            
            self._state.updated_at = datetime.now().isoformat()
            
            try:
                with open(self.state_file, "w", encoding="utf-8") as f:
                    json.dump(self._state.to_dict(), f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"保存状态失败: {e}")
    
    def set_task_list(self, tasks: list[dict]) -> None:
        if not self._state:
            return
        
        self._state.task_list = tasks
        self._state.total_tasks = len(tasks)
        self._state.current_task_index = 0
        self.save_state()
    
    def create_checkpoint(
        self,
        interrupt_reason: Optional[InterruptReason] = None,
        error_details: Optional[str] = None,
    ) -> Checkpoint:
        if not self._state:
            raise ValueError("没有活动的项目状态")
        
        checkpoint_id = f"cp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        completed_tasks = [
            t.get("id", str(i))
            for i, t in enumerate(self._state.task_list[:self._state.current_task_index])
        ]
        
        pending_tasks = [
            t.get("id", str(i + self._state.current_task_index))
            for i, t in enumerate(self._state.task_list[self._state.current_task_index:])
        ]
        
        task_progress = {}
        for i, task in enumerate(self._state.task_list):
            task_id = task.get("id", str(i))
            task_progress[task_id] = TaskProgress(
                task_id=task_id,
                task_name=task.get("name", task.get("description", "")[:50]),
                status=task.get("status", "pending"),
                progress=task.get("progress", 0.0),
                error_message=task.get("error_message"),
                output_files=task.get("output_files", []),
            )
        
        recovery_hint = self._generate_recovery_hint(interrupt_reason)
        
        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            timestamp=datetime.now().isoformat(),
            project_status=self._state.status.value,
            current_task_index=self._state.current_task_index,
            total_tasks=self._state.total_tasks,
            completed_tasks=completed_tasks,
            pending_tasks=pending_tasks,
            task_progress=task_progress,
            interrupt_reason=interrupt_reason.value if interrupt_reason else None,
            error_details=error_details,
            recovery_hint=recovery_hint,
        )
        
        self._state.checkpoints.append(checkpoint)
        
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
        with open(checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(checkpoint.to_dict(), f, ensure_ascii=False, indent=2)
        
        self.save_state()
        
        return checkpoint
    
    def _generate_recovery_hint(
        self,
        interrupt_reason: Optional[InterruptReason],
    ) -> str:
        hints = {
            InterruptReason.API_LIMIT: "等待API限制重置后使用 'multi-agent resume' 继续",
            InterruptReason.NETWORK_ERROR: "检查网络连接后使用 'multi-agent resume' 重试",
            InterruptReason.CLI_ERROR: "检查Claude CLI后使用 'multi-agent resume' 继续",
            InterruptReason.SYSTEM_CRASH: "使用 'multi-agent resume' 从检查点恢复",
            InterruptReason.MANUAL_STOP: "使用 'multi-agent resume' 继续执行",
            InterruptReason.TIMEOUT: "使用 'multi-agent resume' 继续执行",
            InterruptReason.UNKNOWN: "使用 'multi-agent resume' 尝试恢复",
        }
        return hints.get(interrupt_reason, "使用 'multi-agent resume' 继续执行")
    
    def update_task_progress(
        self,
        task_index: int,
        status: str,
        progress: float = 0.0,
        error_message: Optional[str] = None,
        output_files: list[str] = None,
    ) -> None:
        if not self._state:
            return
        
        self._state.current_task_index = task_index
        
        if task_index < len(self._state.task_list):
            task = self._state.task_list[task_index]
            task["status"] = status
            task["progress"] = progress
            if error_message:
                task["error_message"] = error_message
            if output_files:
                task["output_files"] = output_files
        
        self.save_state()
    
    def add_generated_file(self, file_path: str) -> None:
        if not self._state:
            return
        
        if file_path not in self._state.generated_files:
            self._state.generated_files.append(file_path)
            self.save_state()
    
    def record_error(
        self,
        error_type: str,
        error_message: str,
        task_index: Optional[int] = None,
        recovery_action: Optional[str] = None,
    ) -> None:
        if not self._state:
            return
        
        error_record = {
            "timestamp": datetime.now().isoformat(),
            "type": error_type,
            "message": error_message,
            "task_index": task_index,
            "recovery_action": recovery_action,
        }
        
        self._state.error_history.append(error_record)
        self.save_state()
    
    def start_auto_save(self, interval: int = 30) -> None:
        def auto_save_loop():
            while not self._stop_auto_save.is_set():
                self.save_state()
                self._stop_auto_save.wait(interval)
        
        self._stop_auto_save.clear()
        self._auto_save_thread = threading.Thread(target=auto_save_loop, daemon=True)
        self._auto_save_thread.start()
    
    def stop_auto_save(self) -> None:
        self._stop_auto_save.set()
        if self._auto_save_thread:
            self._auto_save_thread.join(timeout=5)
            self._auto_save_thread = None
    
    def can_resume(self) -> bool:
        if not self._state:
            return False
        
        return (
            self._state.status in [ProjectStatus.INTERRUPTED, ProjectStatus.PAUSED]
            and self._state.current_task_index < self._state.total_tasks
        )
    
    def get_resume_info(self) -> dict:
        if not self._state or not self._state.checkpoints:
            return {}
        
        latest_checkpoint = self._state.checkpoints[-1]
        
        return {
            "project_id": self._state.project_id,
            "project_name": self._state.project_name,
            "status": self._state.status.value,
            "current_task_index": self._state.current_task_index,
            "total_tasks": self._state.total_tasks,
            "completed_count": len(latest_checkpoint.completed_tasks),
            "pending_count": len(latest_checkpoint.pending_tasks),
            "interrupt_reason": latest_checkpoint.interrupt_reason,
            "recovery_hint": latest_checkpoint.recovery_hint,
        }
    
    def set_status(self, status: ProjectStatus) -> None:
        if not self._state:
            return
        self._state.status = status
        self.save_state()


class ErrorRecovery:
    """错误恢复处理器"""
    
    ERROR_PATTERNS = {
        InterruptReason.API_LIMIT: [
            r"使用上限",
            r"rate limit",
            r"quota exceeded",
            r"too many requests",
            r"429",
            r"限额",
            r"限制",
        ],
        InterruptReason.NETWORK_ERROR: [
            r"network error",
            r"connection refused",
            r"connection reset",
            r"网络错误",
            r"连接失败",
        ],
        InterruptReason.CLI_ERROR: [
            r"cli error",
            r"claude cli",
            r"command failed",
            r"执行失败",
        ],
        InterruptReason.TIMEOUT: [
            r"timeout",
            r"timed out",
            r"超时",
        ],
    }
    
    RECOVERY_STRATEGIES = {
        InterruptReason.API_LIMIT: {
            "action": "wait_and_retry",
            "message": "API调用达到限制，等待重置后重试",
            "max_wait": 3600,
        },
        InterruptReason.NETWORK_ERROR: {
            "action": "retry_with_backoff",
            "message": "网络错误，使用退避策略重试",
            "max_retries": 3,
        },
        InterruptReason.CLI_ERROR: {
            "action": "retry_with_fallback",
            "message": "CLI错误，尝试备用方案",
            "max_retries": 2,
        },
        InterruptReason.TIMEOUT: {
            "action": "retry_with_longer_timeout",
            "message": "超时，使用更长的超时时间重试",
            "max_retries": 2,
        },
        InterruptReason.SYSTEM_CRASH: {
            "action": "restore_from_checkpoint",
            "message": "从最近的检查点恢复",
        },
        InterruptReason.MANUAL_STOP: {
            "action": "resume",
            "message": "从停止点继续执行",
        },
        InterruptReason.UNKNOWN: {
            "action": "retry",
            "message": "未知错误，尝试重试",
            "max_retries": 1,
        },
    }
    
    def __init__(self, persistence: StatePersistence):
        self.persistence = persistence
        self._output_callback: Optional[Callable[[str, str], None]] = None
    
    def set_output_callback(self, callback: Callable[[str, str], None]) -> None:
        self._output_callback = callback
    
    def _log(self, level: str, message: str) -> None:
        if self._output_callback:
            self._output_callback(level, message)
    
    def detect_error_type(self, error_message: str) -> InterruptReason:
        error_lower = error_message.lower()
        
        for error_type, patterns in self.ERROR_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, error_lower, re.IGNORECASE):
                    return InterruptReason(error_type)
        
        return InterruptReason.UNKNOWN
    
    def handle_error(
        self,
        error: Exception,
        task_index: Optional[int] = None,
    ) -> dict:
        error_message = str(error)
        error_type = self.detect_error_type(error_message)
        
        self._log("error", f"检测到错误: {error_type.value} - {error_message}")
        
        self.persistence.record_error(
            error_type=error_type.value,
            error_message=error_message,
            task_index=task_index,
        )
        
        checkpoint = self.persistence.create_checkpoint(
            interrupt_reason=error_type,
            error_details=error_message,
        )
        
        strategy = self.RECOVERY_STRATEGIES.get(error_type, {})
        
        self.persistence.set_status(ProjectStatus.INTERRUPTED)
        
        return {
            "error_type": error_type.value,
            "error_message": error_message,
            "checkpoint_id": checkpoint.checkpoint_id,
            "recovery_action": strategy.get("action", "retry"),
            "recovery_message": strategy.get("message", "请使用 resume 命令恢复"),
            "can_auto_recover": error_type in [InterruptReason.NETWORK_ERROR, InterruptReason.TIMEOUT],
            "resume_hint": checkpoint.recovery_hint,
        }
    
    def get_wait_time(self, error_message: str) -> int:
        patterns = [
            (r"(\d+)\s*小时", 3600),
            (r"(\d+)\s*hour", 3600),
            (r"(\d+)\s*分钟", 60),
            (r"(\d+)\s*minute", 60),
        ]
        
        for pattern, multiplier in patterns:
            match = re.search(pattern, error_message, re.IGNORECASE)
            if match:
                return int(match.group(1)) * multiplier
        
        return 3600


class ProjectResumer:
    """项目恢复器"""
    
    def __init__(
        self,
        persistence: StatePersistence,
        recovery: ErrorRecovery,
        output_callback: Optional[Callable[[str, str, str], None]] = None,
    ):
        self.persistence = persistence
        self.recovery = recovery
        self.output_callback = output_callback
    
    def _log(self, level: str, message: str) -> None:
        if self.output_callback:
            self.output_callback("resumer", level, message)
    
    def check_resumable(self, project_dir: str = None) -> dict:
        if project_dir:
            self.persistence = StatePersistence(project_dir)
        
        state = self.persistence.load_state()
        
        if not state:
            return {
                "resumable": False,
                "reason": "未找到项目状态文件",
            }
        
        if state.status == ProjectStatus.COMPLETED:
            return {
                "resumable": False,
                "reason": "项目已完成",
                "project_name": state.project_name,
            }
        
        resume_info = self.persistence.get_resume_info()
        
        return {
            "resumable": True,
            "project_id": state.project_id,
            "project_name": state.project_name,
            "status": state.status.value,
            "current_task": resume_info["current_task_index"],
            "total_tasks": resume_info["total_tasks"],
            "completed": resume_info["completed_count"],
            "pending": resume_info["pending_count"],
            "interrupt_reason": resume_info["interrupt_reason"],
            "recovery_hint": resume_info["recovery_hint"],
            "output_dir": state.output_dir,
        }
    
    def prepare_resume(self, project_dir: str = None) -> dict:
        check_result = self.check_resumable(project_dir)
        
        if not check_result.get("resumable"):
            return check_result
        
        state = self.persistence.load_state()
        
        pending_tasks = []
        if state.checkpoints:
            latest_checkpoint = state.checkpoints[-1]
            for task_id in latest_checkpoint.pending_tasks:
                for task in state.task_list:
                    if task.get("id") == task_id:
                        pending_tasks.append(task)
                        break
        
        self._log("info", f"准备恢复项目: {state.project_name}")
        self._log("info", f"从任务 {state.current_task_index} 继续")
        
        return {
            "ready": True,
            "project_id": state.project_id,
            "project_name": state.project_name,
            "resume_from_index": state.current_task_index,
            "pending_tasks": pending_tasks,
            "generated_files": state.generated_files,
            "output_dir": state.output_dir,
            "requirements": state.requirements,
            "tech_stack": state.tech_stack,
        }
    
    def mark_running(self) -> None:
        self.persistence.set_status(ProjectStatus.RUNNING)
        self._log("info", "项目状态已更新为运行中")
    
    def mark_completed(self) -> None:
        self.persistence.set_status(ProjectStatus.COMPLETED)
        self.persistence.create_checkpoint()
        self._log("info", "项目已完成")
    
    def mark_interrupted(self, reason: InterruptReason, error: str) -> None:
        self.persistence.set_status(ProjectStatus.INTERRUPTED)
        self.persistence.create_checkpoint(
            interrupt_reason=reason,
            error_details=error,
        )
        self._log("warning", f"项目已中断: {reason.value}")
