"""
Advisor committee for deadlock resolution and expert analysis.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from multi_agent.core.types import AgentRole, TaskContext
from multi_agent.memory.long_term import LongTermMemoryManager


@dataclass
class AdvisorRuling:
    """A ruling from the advisor committee."""
    
    task_id: str
    recommendation: str
    rationale: str
    similar_cases: list[dict]
    confidence: float
    suggested_actions: list[str]
    created_at: datetime
    
    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "recommendation": self.recommendation,
            "rationale": self.rationale,
            "similar_cases": self.similar_cases,
            "confidence": self.confidence,
            "suggested_actions": self.suggested_actions,
            "created_at": self.created_at.isoformat(),
        }


class AdvisorCommittee:
    """
    Advisor committee for resolving deadlocks and providing expert analysis.
    
    Responsibilities:
    - Analyze deadlocked tasks
    - Search historical data for similar situations
    - Provide binding recommendations
    - Suggest scope adjustments
    
    Activation:
    - Triggered by CTO when loops are detected
    - Triggered by CEO for strategic decisions
    - Never self-activates
    """
    
    RULING_TEMPLATES: dict[str, str] = {
        "loop_detected": (
            "Task {task_id} has exceeded maximum iterations. "
            "Based on analysis of {similar_count} similar cases, "
            "I recommend: {recommendation}"
        ),
        "scope_drift": (
            "Scope drift detected in task {task_id}. "
            "Original scope: {original_scope}. "
            "Recommendation: {recommendation}"
        ),
        "technical_deadlock": (
            "Technical deadlock identified in task {task_id}. "
            "Root cause analysis: {root_cause}. "
            "Recommended resolution: {recommendation}"
        ),
        "resource_conflict": (
            "Resource conflict in task {task_id}. "
            "Conflicting agents: {conflicting_agents}. "
            "Resolution strategy: {recommendation}"
        ),
    }
    
    RESOLUTION_STRATEGIES: dict[str, list[str]] = {
        "loop_detected": [
            "Reduce task complexity by breaking into smaller subtasks",
            "Reassign to different agent with fresh perspective",
            "Lower feature priority and move to backlog",
            "Implement simplified version first",
        ],
        "scope_drift": [
            "Return to original scope boundaries",
            "Document new requirements for future phase",
            "Escalate scope change to CEO for approval",
            "Create separate task for out-of-scope items",
        ],
        "technical_deadlock": [
            "Alternative technical approach",
            "Third-party library integration",
            "Architecture modification",
            "Defer feature to next iteration",
        ],
        "resource_conflict": [
            "Prioritize based on business value",
            "Parallel execution with clear boundaries",
            "Sequential execution with dependencies",
            "Resource reallocation",
        ],
    }
    
    def __init__(
        self,
        long_term_memory: LongTermMemoryManager,
        min_confidence: float = 0.6,
    ):
        self.long_term_memory = long_term_memory
        self.min_confidence = min_confidence
        self._ruling_history: list[AdvisorRuling] = []
    
    async def analyze_and_rule(
        self,
        task: TaskContext,
        context: dict[str, Any],
    ) -> dict:
        """
        Analyze a problematic task and provide a ruling.
        
        This is the main entry point for advisor intervention.
        """
        issue_type = context.get("issue_type", "loop_detected")
        
        similar_cases = await self._find_similar_cases(task, context)
        
        recommendation = self._generate_recommendation(
            task=task,
            issue_type=issue_type,
            similar_cases=similar_cases,
            context=context,
        )
        
        confidence = self._calculate_confidence(similar_cases, context)
        
        ruling = AdvisorRuling(
            task_id=str(task.id),
            recommendation=recommendation["recommendation"],
            rationale=recommendation["rationale"],
            similar_cases=[c for c in similar_cases[:3]],
            confidence=confidence,
            suggested_actions=recommendation["actions"],
            created_at=datetime.utcnow(),
        )
        
        self._ruling_history.append(ruling)
        
        await self._store_ruling(ruling)
        
        return ruling.to_dict()
    
    async def _find_similar_cases(
        self,
        task: TaskContext,
        context: dict[str, Any],
    ) -> list[dict]:
        """Search for similar historical cases in long-term memory."""
        query = self._build_search_query(task, context)
        
        try:
            similar = await self.long_term_memory.find_similar_issues(
                query=query,
                n_results=5,
            )
            return similar
        except Exception:
            return []
    
    def _build_search_query(
        self,
        task: TaskContext,
        context: dict[str, Any],
    ) -> str:
        """Build a search query for finding similar cases."""
        issue_type = context.get("issue_type", "")
        task_description = task.description
        
        query_parts = [issue_type, task.title, task_description[:200]]
        
        if "pattern" in context:
            query_parts.append(str(context["pattern"]))
        
        return " ".join(query_parts)
    
    def _generate_recommendation(
        self,
        task: TaskContext,
        issue_type: str,
        similar_cases: list[dict],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a recommendation based on analysis."""
        strategies = self.RESOLUTION_STRATEGIES.get(issue_type, [])
        
        if similar_cases:
            for case in similar_cases:
                if "resolution" in case.get("metadata", {}):
                    return {
                        "recommendation": case["metadata"]["resolution"],
                        "rationale": f"Based on similar historical case: {case.get('id', 'unknown')}",
                        "actions": [case["metadata"]["resolution"]],
                    }
        
        if strategies:
            primary_strategy = strategies[0]
            return {
                "recommendation": primary_strategy,
                "rationale": f"Standard resolution strategy for {issue_type}",
                "actions": strategies[:3],
            }
        
        return {
            "recommendation": "Escalate to CEO for strategic decision",
            "rationale": "No clear resolution path identified",
            "actions": [
                "Document current state",
                "Prepare escalation report",
                "Await CEO decision",
            ],
        }
    
    def _calculate_confidence(
        self,
        similar_cases: list[dict],
        context: dict[str, Any],
    ) -> float:
        """Calculate confidence level for the recommendation."""
        base_confidence = 0.5
        
        if similar_cases:
            case_bonus = min(len(similar_cases) * 0.1, 0.3)
            base_confidence += case_bonus
        
        if context.get("issue_type") in self.RESOLUTION_STRATEGIES:
            base_confidence += 0.1
        
        return min(base_confidence, 1.0)
    
    async def _store_ruling(self, ruling: AdvisorRuling) -> None:
        """Store the ruling in long-term memory for future reference."""
        try:
            await self.long_term_memory.store_decision(
                decision=ruling.recommendation,
                context={
                    "task_id": ruling.task_id,
                    "confidence": ruling.confidence,
                    "similar_cases_count": len(ruling.similar_cases),
                },
                made_by=AgentRole.ADVISOR,
                task_id=ruling.task_id,
            )
        except Exception:
            pass
    
    def get_ruling_history(self, limit: int = 50) -> list[dict]:
        """Get recent ruling history."""
        return [r.to_dict() for r in self._ruling_history[-limit:]]
    
    def get_statistics(self) -> dict:
        """Get advisor committee statistics."""
        if not self._ruling_history:
            return {
                "total_rulings": 0,
                "average_confidence": 0.0,
            }
        
        total = len(self._ruling_history)
        avg_confidence = sum(r.confidence for r in self._ruling_history) / total
        
        return {
            "total_rulings": total,
            "average_confidence": avg_confidence,
        }
