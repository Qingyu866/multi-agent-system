"""
Loop detection system for identifying task circulation patterns.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from multi_agent.core.types import AgentRole


@dataclass
class TaskFlowRecord:
    """Record of a single task flow between agents."""
    
    from_agent: AgentRole
    to_agent: AgentRole
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class LoopPattern:
    """Detected loop pattern."""
    
    task_id: str
    pattern: list[AgentRole]
    occurrences: int
    first_detected: datetime
    last_detected: datetime


class LoopDetector:
    """
    Detects circular task flows that indicate deadlock or loop conditions.
    
    Detection criteria:
    - Same task flowing between CTO -> Developer -> QA more than 3 times
    - Identical agent sequence repeating
    - Task stuck in the same state for extended period
    
    When a loop is detected, triggers advisor intervention.
    """
    
    DEFAULT_MAX_ITERATIONS = 3
    DEFAULT_PATTERN_WINDOW = 10
    
    def __init__(
        self,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        pattern_window: int = DEFAULT_PATTERN_WINDOW,
        time_window_hours: int = 24,
    ):
        self.max_iterations = max_iterations
        self.pattern_window = pattern_window
        self.time_window_hours = time_window_hours
        
        self._task_flows: dict[str, list[TaskFlowRecord]] = defaultdict(list)
        self._detected_loops: dict[str, LoopPattern] = {}
        self._iteration_counts: dict[str, dict[tuple[AgentRole, AgentRole], int]] = defaultdict(
            lambda: defaultdict(int)
        )
    
    def check_and_record(
        self,
        task_id: str,
        from_agent: AgentRole,
        to_agent: AgentRole,
    ) -> bool:
        """
        Record a task flow and check if it creates a loop.
        
        Returns True if a loop is detected.
        """
        record = TaskFlowRecord(from_agent=from_agent, to_agent=to_agent)
        self._task_flows[task_id].append(record)
        
        flow_key = (from_agent, to_agent)
        self._iteration_counts[task_id][flow_key] += 1
        
        self._cleanup_old_records(task_id)
        
        return self._detect_loop(task_id)
    
    def _detect_loop(self, task_id: str) -> bool:
        """
        Detect if a task has entered a loop.
        
        Checks:
        1. Same agent pair repeated more than max_iterations
        2. Circular pattern in recent flow history
        """
        flows = self._task_flows[task_id]
        if len(flows) < self.max_iterations:
            return False
        
        for flow_key, count in self._iteration_counts[task_id].items():
            if count >= self.max_iterations:
                self._record_loop(task_id, flows)
                return True
        
        recent_flows = flows[-self.pattern_window:]
        pattern = [f.to_agent for f in recent_flows]
        
        if self._has_repeating_pattern(pattern):
            self._record_loop(task_id, flows)
            return True
        
        return False
    
    def _has_repeating_pattern(self, pattern: list[AgentRole]) -> bool:
        """Check if the pattern has repeating subsequences."""
        if len(pattern) < 4:
            return False
        
        for length in range(2, len(pattern) // 2 + 1):
            for start in range(len(pattern) - length * 2 + 1):
                subsequence = pattern[start:start + length]
                next_sequence = pattern[start + length:start + length * 2]
                
                if subsequence == next_sequence:
                    return True
        
        return False
    
    def _record_loop(self, task_id: str, flows: list[TaskFlowRecord]) -> None:
        """Record a detected loop pattern."""
        pattern = [f.to_agent for f in flows[-self.pattern_window:]]
        
        if task_id in self._detected_loops:
            self._detected_loops[task_id].occurrences += 1
            self._detected_loops[task_id].last_detected = datetime.utcnow()
        else:
            self._detected_loops[task_id] = LoopPattern(
                task_id=task_id,
                pattern=pattern,
                occurrences=1,
                first_detected=datetime.utcnow(),
                last_detected=datetime.utcnow(),
            )
    
    def _cleanup_old_records(self, task_id: str) -> None:
        """Remove records older than the time window."""
        cutoff = datetime.utcnow() - timedelta(hours=self.time_window_hours)
        
        self._task_flows[task_id] = [
            record for record in self._task_flows[task_id]
            if record.timestamp > cutoff
        ]
        
        for flow_key in list(self._iteration_counts[task_id].keys()):
            recent_count = sum(
                1 for record in self._task_flows[task_id]
                if (record.from_agent, record.to_agent) == flow_key
            )
            if recent_count == 0:
                del self._iteration_counts[task_id][flow_key]
    
    def get_loop_status(self, task_id: str) -> Optional[dict]:
        """Get the loop status for a specific task."""
        if task_id not in self._detected_loops:
            return None
        
        loop = self._detected_loops[task_id]
        return {
            "task_id": task_id,
            "pattern": [agent.value for agent in loop.pattern],
            "occurrences": loop.occurrences,
            "first_detected": loop.first_detected.isoformat(),
            "last_detected": loop.last_detected.isoformat(),
        }
    
    def get_all_loops(self) -> list[dict]:
        """Get all detected loops."""
        return [
            self.get_loop_status(task_id)
            for task_id in self._detected_loops
        ]
    
    def clear_task_history(self, task_id: str) -> None:
        """Clear history for a specific task."""
        if task_id in self._task_flows:
            del self._task_flows[task_id]
        if task_id in self._iteration_counts:
            del self._iteration_counts[task_id]
        if task_id in self._detected_loops:
            del self._detected_loops[task_id]
    
    def get_iteration_count(
        self,
        task_id: str,
        from_agent: AgentRole,
        to_agent: AgentRole,
    ) -> int:
        """Get the iteration count for a specific agent pair."""
        return self._iteration_counts[task_id].get((from_agent, to_agent), 0)
    
    def get_statistics(self) -> dict:
        """Get overall loop detection statistics."""
        return {
            "total_tasks_tracked": len(self._task_flows),
            "loops_detected": len(self._detected_loops),
            "max_iterations_threshold": self.max_iterations,
            "time_window_hours": self.time_window_hours,
        }
