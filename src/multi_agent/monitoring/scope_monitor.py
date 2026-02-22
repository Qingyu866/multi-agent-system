"""
Scope monitoring system for detecting project scope drift.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from multi_agent.core.types import AgentRole, ProjectContext


@dataclass
class DriftIndicator:
    """Indicator of potential scope drift."""
    
    keyword: str
    context: str
    severity: str
    suggestion: str


class ScopeMonitor:
    """
    Monitors agent interactions for scope drift from original project requirements.
    
    Detection methods:
    1. Keyword matching against scope boundaries
    2. Topic deviation analysis
    3. Requirement relevance scoring
    
    When drift is detected, issues alerts and provides guidance for returning to scope.
    """
    
    DRIFT_KEYWORDS: dict[str, list[str]] = {
        "feature_creep": [
            "also add",
            "while we're at it",
            "it would be nice",
            "extra feature",
            "one more thing",
            "additionally",
            "could we also",
        ],
        "scope_expansion": [
            "expand the scope",
            "beyond original",
            "new requirement",
            "change the requirement",
            "different approach",
            "instead of the original",
        ],
        "off_topic": [
            "unrelated",
            "by the way",
            "separate project",
            "different system",
            "another application",
        ],
    }
    
    SCOPE_BOUNDARY_KEYWORDS: dict[str, list[str]] = {
        "excluded": [
            "not included",
            "out of scope",
            "excluded",
            "won't implement",
            "future phase",
        ],
        "constraints": [
            "must not",
            "cannot",
            "limited to",
            "restricted",
            "boundary",
        ],
    }
    
    def __init__(
        self,
        project_context: ProjectContext,
        drift_threshold: float = 0.7,
    ):
        self.project_context = project_context
        self.drift_threshold = drift_threshold
        
        self._drift_history: list[dict] = []
        self._keyword_patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> dict[str, re.Pattern]:
        """Compile regex patterns for drift detection."""
        patterns = {}
        
        for category, keywords in self.DRIFT_KEYWORDS.items():
            pattern = "|".join(re.escape(kw) for kw in keywords)
            patterns[category] = re.compile(pattern, re.IGNORECASE)
        
        for category, keywords in self.SCOPE_BOUNDARY_KEYWORDS.items():
            pattern = "|".join(re.escape(kw) for kw in keywords)
            patterns[f"boundary_{category}"] = re.compile(pattern, re.IGNORECASE)
        
        return patterns
    
    def check_content(
        self,
        content: str,
        task_id: Optional[str] = None,
        agent_role: Optional[AgentRole] = None,
    ) -> tuple[bool, Optional[DriftIndicator]]:
        """
        Check content for scope drift indicators.
        
        Returns (is_drift_detected, drift_indicator).
        """
        drift_indicators = []
        
        for category, pattern in self._keyword_patterns.items():
            if category.startswith("boundary_"):
                continue
            
            matches = pattern.findall(content)
            if matches:
                severity = self._calculate_severity(category, matches)
                indicator = DriftIndicator(
                    keyword=matches[0] if matches else "",
                    context=self._extract_context(content, matches[0] if matches else ""),
                    severity=severity,
                    suggestion=self._generate_suggestion(category),
                )
                drift_indicators.append(indicator)
        
        if drift_indicators:
            most_severe = max(drift_indicators, key=lambda x: self._severity_score(x.severity))
            
            self._record_drift(
                task_id=task_id,
                agent_role=agent_role,
                content=content,
                indicator=most_severe,
            )
            
            return True, most_severe
        
        return False, None
    
    def _calculate_severity(self, category: str, matches: list[str]) -> str:
        """Calculate severity based on category and match count."""
        severity_map = {
            "feature_creep": "medium",
            "scope_expansion": "high",
            "off_topic": "low",
        }
        
        base_severity = severity_map.get(category, "low")
        
        if len(matches) >= 3:
            severity_upgrade = {"low": "medium", "medium": "high", "high": "critical"}
            return severity_upgrade.get(base_severity, base_severity)
        
        return base_severity
    
    def _severity_score(self, severity: str) -> int:
        """Convert severity to numeric score for comparison."""
        scores = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        return scores.get(severity, 0)
    
    def _extract_context(self, content: str, keyword: str, context_chars: int = 50) -> str:
        """Extract context around the detected keyword."""
        try:
            idx = content.lower().find(keyword.lower())
            if idx == -1:
                return keyword
            
            start = max(0, idx - context_chars)
            end = min(len(content), idx + len(keyword) + context_chars)
            
            return "..." + content[start:end] + "..."
        except Exception:
            return keyword
    
    def _generate_suggestion(self, category: str) -> str:
        """Generate a suggestion for addressing the drift."""
        suggestions = {
            "feature_creep": (
                "Consider adding this to a future phase or separate task. "
                "Focus on completing the current scope first."
            ),
            "scope_expansion": (
                "This appears to expand beyond the original scope. "
                "Please consult with CEO before proceeding."
            ),
            "off_topic": (
                "This discussion appears to be off-topic. "
                "Please return to the current task objectives."
            ),
        }
        return suggestions.get(category, "Please review the original project scope.")
    
    def _record_drift(
        self,
        task_id: Optional[str],
        agent_role: Optional[AgentRole],
        content: str,
        indicator: DriftIndicator,
    ) -> None:
        """Record a scope drift incident."""
        self._drift_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "task_id": task_id,
            "agent_role": agent_role.value if agent_role else None,
            "keyword": indicator.keyword,
            "severity": indicator.severity,
            "suggestion": indicator.suggestion,
        })
    
    def get_original_scope(self) -> list[str]:
        """Get the original project scope boundaries."""
        return self.project_context.scope_boundaries
    
    def get_requirements(self) -> list[str]:
        """Get the project requirements."""
        return self.project_context.requirements
    
    def check_relevance(
        self,
        content: str,
        requirements: Optional[list[str]] = None,
    ) -> float:
        """
        Calculate relevance score of content to project requirements.
        
        Returns a score between 0 and 1.
        """
        reqs = requirements or self.project_context.requirements
        if not reqs:
            return 1.0
        
        content_lower = content.lower()
        relevant_count = 0
        
        for req in reqs:
            req_keywords = req.lower().split()
            if any(kw in content_lower for kw in req_keywords if len(kw) > 3):
                relevant_count += 1
        
        return relevant_count / len(reqs)
    
    def get_drift_history(self, limit: int = 50) -> list[dict]:
        """Get recent drift detection history."""
        return self._drift_history[-limit:]
    
    def get_drift_statistics(self) -> dict:
        """Get statistics about scope drift detection."""
        if not self._drift_history:
            return {
                "total_incidents": 0,
                "by_severity": {},
                "by_agent": {},
            }
        
        by_severity: dict[str, int] = {}
        by_agent: dict[str, int] = {}
        
        for incident in self._drift_history:
            severity = incident.get("severity", "unknown")
            by_severity[severity] = by_severity.get(severity, 0) + 1
            
            agent = incident.get("agent_role", "unknown")
            by_agent[agent] = by_agent.get(agent, 0) + 1
        
        return {
            "total_incidents": len(self._drift_history),
            "by_severity": by_severity,
            "by_agent": by_agent,
        }
    
    def clear_history(self) -> None:
        """Clear drift detection history."""
        self._drift_history = []
