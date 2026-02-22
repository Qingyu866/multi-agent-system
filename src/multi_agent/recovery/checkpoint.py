"""检查点管理器

管理项目执行过程中的检查点，支持：
- 创建检查点
- 加载检查点
- 列出所有检查点
- 从检查点恢复
"""

import json
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Any


@dataclass
class Checkpoint:
    """检查点数据结构"""
    checkpoint_id: str
    timestamp: str
    project_status: str
    current_task_index: int
    total_tasks: int
    completed_tasks: list[str] = field(default_factory=list)
    pending_tasks: list[str] = field(default_factory=list)
    interrupt_reason: Optional[str] = None
    error_details: Optional[str] = None
    recovery_hint: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "Checkpoint":
        return cls(**data)


class CheckpointManager:
    """检查点管理器"""
    
    CHECKPOINT_DIR = "checkpoints"
    
    def __init__(self, state_dir: Path):
        self.checkpoint_dir = state_dir / self.CHECKPOINT_DIR
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    def create(
        self,
        project_status: str,
        current_task_index: int,
        total_tasks: int,
        completed_tasks: list[str] = None,
        pending_tasks: list[str] = None,
        interrupt_reason: Optional[str] = None,
        error_details: Optional[str] = None,
        metadata: dict[str, Any] = None,
    ) -> Checkpoint:
        """创建新检查点"""
        checkpoint_id = f"cp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        recovery_hint = self._generate_recovery_hint(interrupt_reason)
        
        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            timestamp=datetime.now().isoformat(),
            project_status=project_status,
            current_task_index=current_task_index,
            total_tasks=total_tasks,
            completed_tasks=completed_tasks or [],
            pending_tasks=pending_tasks or [],
            interrupt_reason=interrupt_reason,
            error_details=error_details,
            recovery_hint=recovery_hint,
            metadata=metadata or {},
        )
        
        self._save_checkpoint(checkpoint)
        
        return checkpoint
    
    def _save_checkpoint(self, checkpoint: Checkpoint) -> None:
        """保存检查点到文件"""
        checkpoint_file = self.checkpoint_dir / f"{checkpoint.checkpoint_id}.json"
        with open(checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(checkpoint.to_dict(), f, ensure_ascii=False, indent=2)
    
    def load(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """加载指定检查点"""
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
        
        if not checkpoint_file.exists():
            return None
        
        with open(checkpoint_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return Checkpoint.from_dict(data)
    
    def get_latest(self) -> Optional[Checkpoint]:
        """获取最新的检查点"""
        checkpoints = self.list_all()
        
        if not checkpoints:
            return None
        
        return checkpoints[-1]
    
    def list_all(self) -> list[Checkpoint]:
        """列出所有检查点（按时间排序）"""
        checkpoints = []
        
        for cp_file in self.checkpoint_dir.glob("cp_*.json"):
            try:
                with open(cp_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                checkpoints.append(Checkpoint.from_dict(data))
            except Exception:
                continue
        
        checkpoints.sort(key=lambda x: x.timestamp)
        
        return checkpoints
    
    def delete(self, checkpoint_id: str) -> bool:
        """删除指定检查点"""
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
        
        if checkpoint_file.exists():
            checkpoint_file.unlink()
            return True
        
        return False
    
    def cleanup_old(self, keep_count: int = 10) -> int:
        """清理旧检查点，保留最新的N个"""
        checkpoints = self.list_all()
        
        if len(checkpoints) <= keep_count:
            return 0
        
        to_delete = checkpoints[:-keep_count]
        deleted_count = 0
        
        for cp in to_delete:
            if self.delete(cp.checkpoint_id):
                deleted_count += 1
        
        return deleted_count
    
    def _generate_recovery_hint(self, interrupt_reason: Optional[str]) -> str:
        """生成恢复提示"""
        hints = {
            "api_limit": "等待API限制重置后使用 'multi-agent resume' 继续",
            "network_error": "检查网络连接后使用 'multi-agent resume' 重试",
            "cli_error": "检查Claude CLI后使用 'multi-agent resume' 继续",
            "system_crash": "使用 'multi-agent resume' 从检查点恢复",
            "manual_stop": "使用 'multi-agent resume' 继续执行",
            "timeout": "使用 'multi-agent resume' 继续执行",
        }
        return hints.get(interrupt_reason, "使用 'multi-agent resume' 继续执行")
    
    def get_summary(self) -> dict:
        """获取检查点摘要"""
        checkpoints = self.list_all()
        
        if not checkpoints:
            return {
            "total": 0,
            "latest": None,
        }
        
        latest = checkpoints[-1]
        
        return {
            "total": len(checkpoints),
            "latest": {
                "id": latest.checkpoint_id,
                "timestamp": latest.timestamp,
                "status": latest.project_status,
                "task_index": latest.current_task_index,
                "interrupt_reason": latest.interrupt_reason,
            },
        }
