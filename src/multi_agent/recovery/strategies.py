"""恢复策略模块

定义不同中断类型的恢复策略：
1. API限制 - 等待重置后重试
2. 网络错误 - 退避重试
3. CLI错误 - 备用方案
4. 系统崩溃 - 从检查点恢复
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Callable, Any
from enum import Enum
import time
import random


class RecoveryAction(str, Enum):
    """恢复动作类型"""
    WAIT_AND_RETRY = "wait_and_retry"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    RETRY_WITH_FALLBACK = "retry_with_fallback"
    RESTORE_FROM_CHECKPOINT = "restore_from_checkpoint"
    RESUME = "resume"
    MANUAL = "manual"


@dataclass
class RecoveryResult:
    """恢复结果"""
    success: bool
    action: RecoveryAction
    message: str
    wait_time: int = 0
    retry_count: int = 0
    should_wait: bool = False
    should_retry: bool = False
    fallback_data: Optional[dict] = None


class RecoveryStrategy(ABC):
    """恢复策略基类"""
    
    @abstractmethod
    def can_handle(self, error_type: str) -> bool:
        """是否可以处理该错误类型"""
        pass
    
    @abstractmethod
    def get_action(self) -> RecoveryAction:
        """获取恢复动作"""
        pass
    
    @abstractmethod
    def execute(self, context: dict) -> RecoveryResult:
        """执行恢复策略"""
        pass


class APILimitStrategy(RecoveryStrategy):
    """API限制恢复策略"""
    
    def __init__(self, max_wait: int = 3600):
        self.max_wait = max_wait
    
    def can_handle(self, error_type: str) -> bool:
        return error_type == "api_limit"
    
    def get_action(self) -> RecoveryAction:
        return RecoveryAction.WAIT_AND_RETRY
    
    def execute(self, context: dict) -> RecoveryResult:
        error_message = context.get("error_message", "")
        wait_time = self._extract_wait_time(error_message)
        
        return RecoveryResult(
            success=False,
            action=RecoveryAction.WAIT_AND_RETRY,
            message=f"API调用达到限制，建议等待 {wait_time // 60} 分钟后重试",
            wait_time=wait_time,
            should_wait=True,
            should_retry=True,
        )
    
    def _extract_wait_time(self, error_message: str) -> int:
        import re
        
        patterns = [
            (r"(\d+)\s*小时", 3600),
            (r"(\d+)\s*hour", 3600),
            (r"(\d+)\s*分钟", 60),
            (r"(\d+)\s*minute", 60),
            (r"重置.*?(\d+):(\d+)", None),
        ]
        
        for pattern, multiplier in patterns:
            match = re.search(pattern, error_message, re.IGNORECASE)
            if match:
                if multiplier is None and len(match.groups()) == 2:
                    return int(match.group(1)) * 3600 + int(match.group(2)) * 60
                elif multiplier:
                    return int(match.group(1)) * multiplier
        
        return self.max_wait


class NetworkErrorStrategy(RecoveryStrategy):
    """网络错误恢复策略"""
    
    def __init__(self, max_retries: int = 3, base_delay: int = 5):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    def can_handle(self, error_type: str) -> bool:
        return error_type == "network_error"
    
    def get_action(self) -> RecoveryAction:
        return RecoveryAction.RETRY_WITH_BACKOFF
    
    def execute(self, context: dict) -> RecoveryResult:
        retry_count = context.get("retry_count", 0)
        
        if retry_count >= self.max_retries:
            return RecoveryResult(
                success=False,
                action=RecoveryAction.RETRY_WITH_BACKOFF,
                message="网络错误重试次数已达上限",
                retry_count=retry_count,
                should_retry=False,
            )
        
        delay = self._calculate_backoff_delay(retry_count)
        
        return RecoveryResult(
            success=True,
            action=RecoveryAction.RETRY_WITH_BACKOFF,
            message=f"网络错误，{delay}秒后进行第{retry_count + 1}次重试",
            wait_time=delay,
            retry_count=retry_count + 1,
            should_wait=True,
            should_retry=True,
        )
    
    def _calculate_backoff_delay(self, retry_count: int) -> int:
        """计算退避延迟"""
        delay = self.base_delay * (2 ** retry_count)
        jitter = random.uniform(0, delay * 0.1)
        return int(delay + jitter)


class CLIErrorStrategy(RecoveryStrategy):
    """CLI错误恢复策略"""
    
    def __init__(self, max_retries: int = 2):
        self.max_retries = max_retries
    
    def can_handle(self, error_type: str) -> bool:
        return error_type == "cli_error"
    
    def get_action(self) -> RecoveryAction:
        return RecoveryAction.RETRY_WITH_FALLBACK
    
    def execute(self, context: dict) -> RecoveryResult:
        retry_count = context.get("retry_count", 0)
        
        if retry_count >= self.max_retries:
            return RecoveryResult(
                success=False,
                action=RecoveryAction.RETRY_WITH_FALLBACK,
                message="CLI错误重试次数已达上限，建议手动检查",
                retry_count=retry_count,
                should_retry=False,
            )
        
        return RecoveryResult(
            success=True,
            action=RecoveryAction.RETRY_WITH_FALLBACK,
            message=f"CLI错误，尝试备用方案（第{retry_count + 1}次）",
            retry_count=retry_count + 1,
            should_retry=True,
            fallback_data={"use_fallback": True},
        )


class TimeoutStrategy(RecoveryStrategy):
    """超时恢复策略"""
    
    def __init__(self, max_retries: int = 2, timeout_multiplier: float = 1.5):
        self.max_retries = max_retries
        self.timeout_multiplier = timeout_multiplier
    
    def can_handle(self, error_type: str) -> bool:
        return error_type == "timeout"
    
    def get_action(self) -> RecoveryAction:
        return RecoveryAction.RETRY_WITH_FALLBACK
    
    def execute(self, context: dict) -> RecoveryResult:
        retry_count = context.get("retry_count", 0)
        current_timeout = context.get("current_timeout", 300)
        
        if retry_count >= self.max_retries:
            return RecoveryResult(
                success=False,
                action=RecoveryAction.RETRY_WITH_FALLBACK,
                message="超时重试次数已达上限",
                retry_count=retry_count,
                should_retry=False,
            )
        
        new_timeout = int(current_timeout * self.timeout_multiplier)
        
        return RecoveryResult(
            success=True,
            action=RecoveryAction.RETRY_WITH_FALLBACK,
            message=f"超时，使用更长的超时时间({new_timeout}秒)重试",
            retry_count=retry_count + 1,
            should_retry=True,
            fallback_data={"new_timeout": new_timeout},
        )


class SystemCrashStrategy(RecoveryStrategy):
    """系统崩溃恢复策略"""
    
    def can_handle(self, error_type: str) -> bool:
        return error_type == "system_crash"
    
    def get_action(self) -> RecoveryAction:
        return RecoveryAction.RESTORE_FROM_CHECKPOINT
    
    def execute(self, context: dict) -> RecoveryResult:
        checkpoint_id = context.get("checkpoint_id")
        
        if not checkpoint_id:
            return RecoveryResult(
                success=False,
                action=RecoveryAction.RESTORE_FROM_CHECKPOINT,
                message="未找到可用的检查点",
                should_retry=False,
            )
        
        return RecoveryResult(
            success=True,
            action=RecoveryAction.RESTORE_FROM_CHECKPOINT,
            message=f"从检查点 {checkpoint_id} 恢复",
            fallback_data={"checkpoint_id": checkpoint_id},
        )


class ManualStopStrategy(RecoveryStrategy):
    """手动停止恢复策略"""
    
    def can_handle(self, error_type: str) -> bool:
        return error_type == "manual_stop"
    
    def get_action(self) -> RecoveryAction:
        return RecoveryAction.RESUME
    
    def execute(self, context: dict) -> RecoveryResult:
        return RecoveryResult(
            success=True,
            action=RecoveryAction.RESUME,
            message="从停止点继续执行",
            should_retry=True,
        )


class RecoveryStrategyManager:
    """恢复策略管理器"""
    
    def __init__(self):
        self._strategies: list[RecoveryStrategy] = [
            APILimitStrategy(),
            NetworkErrorStrategy(),
            CLIErrorStrategy(),
            TimeoutStrategy(),
            SystemCrashStrategy(),
            ManualStopStrategy(),
        ]
    
    def register_strategy(self, strategy: RecoveryStrategy) -> None:
        """注册新策略"""
        self._strategies.append(strategy)
    
    def get_strategy(self, error_type: str) -> Optional[RecoveryStrategy]:
        """获取适合的策略"""
        for strategy in self._strategies:
            if strategy.can_handle(error_type):
                return strategy
        return None
    
    def execute_recovery(
        self,
        error_type: str,
        context: dict,
    ) -> RecoveryResult:
        """执行恢复"""
        strategy = self.get_strategy(error_type)
        
        if not strategy:
            return RecoveryResult(
                success=False,
                action=RecoveryAction.MANUAL,
                message=f"未知错误类型: {error_type}，需要手动处理",
                should_retry=False,
            )
        
        return strategy.execute(context)
    
    def get_recovery_hint(self, error_type: str) -> str:
        """获取恢复提示"""
        hints = {
            "api_limit": "等待API限制重置后使用 'multi-agent resume' 继续",
            "network_error": "检查网络连接后使用 'multi-agent resume' 重试",
            "cli_error": "检查Claude CLI状态后使用 'multi-agent resume' 继续",
            "timeout": "使用 'multi-agent resume' 继续执行",
            "system_crash": "使用 'multi-agent resume' 从检查点恢复",
            "manual_stop": "使用 'multi-agent resume' 继续执行",
        }
        return hints.get(error_type, "使用 'multi-agent resume' 尝试恢复")
