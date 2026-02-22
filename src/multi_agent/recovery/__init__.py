"""中断恢复机制模块

提供项目执行过程中的中断恢复能力：
1. 状态持久化 - 保存项目执行状态到磁盘
2. 检查点机制 - 定期保存执行进度
3. 错误检测 - 识别不同类型的错误
4. 恢复策略 - 根据错误类型选择恢复方案
5. 断点续传 - 从中断点继续执行

使用方式:
    # 检查可恢复的项目
    multi-agent resume --check ./output/my-project
    
    # 恢复项目执行
    multi-agent resume ./output/my-project
    
    # 查看项目状态
    multi-agent resume --status ./output/my-project
"""

from multi_agent.recovery.state import (
    StatePersistence,
    ErrorRecovery,
    ProjectResumer,
    ProjectStatus,
    InterruptReason,
)
from multi_agent.recovery.checkpoint import CheckpointManager
from multi_agent.recovery.strategies import RecoveryStrategyManager

__all__ = [
    "StatePersistence",
    "ErrorRecovery",
    "ProjectResumer",
    "ProjectStatus",
    "InterruptReason",
    "CheckpointManager",
    "RecoveryStrategyManager",
]
