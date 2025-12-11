"""
Model Selector - Complexity-based model selection for Gemini LLM
Uses n-1 strategy: stable models only (no experimental models in production)
Selects appropriate model based on issue complexity:
- 80%: gemini-2.5-flash (simple cases - stable, free tier)
- 15%: gemini-2.5-flash (moderate complexity - stable, free tier)
- 5%: gemini-2.5-pro (complex cases - stable, paid tier)
"""
import os
from typing import Optional, List
from app.core.logging import get_logger

logger = get_logger(__name__)


# Model priority list (in order of increasing capability/cost)
# Can be overridden via environment variables
def get_model_priority() -> List[str]:
    """Get model priority list from env or use defaults."""
    # Allow override via env var (comma-separated)
    env_models = os.getenv("GEMINI_MODEL_PRIORITY")
    if env_models:
        models = [m.strip() for m in env_models.split(",")]
        if len(models) >= 3:
            logger.info(f"Using custom model priority from env: {models}")
            return models
    
    # Default model priority (n-1 strategy: use stable models, not experimental)
    return [
        "gemini-2.5-flash",      # Primary (80% - stable, free tier)
        "gemini-2.5-flash",      # Moderate (15% - stable, free tier)
        "gemini-2.5-pro"         # Complex (5% - stable, paid tier)
    ]

MODEL_PRIORITY = get_model_priority()


class ModelSelector:
    """Selects appropriate Gemini model based on issue complexity."""
    
    @staticmethod
    def calculate_complexity(
        issue_description: str,
        risk: str,
        service_type: str,
        issue_length: Optional[int] = None
    ) -> float:
        """
        Calculate complexity score (0.0-1.0) for issue.
        
        Returns:
            float: Complexity score where:
                - 0.0-0.8: Use gemini-2.5-flash (80% of cases - stable)
                - 0.8-0.95: Use gemini-2.5-flash (15% of cases - stable)
                - 0.95-1.0: Use gemini-2.5-pro (5% of cases - stable)
        """
        score = 0.0
        issue_lower = issue_description.lower()
        
        # Risk-based scoring (0.0-0.7)
        risk_scores = {
            "low": 0.1,
            "medium": 0.3,
            "high": 0.5,
            "critical": 0.7
        }
        score += risk_scores.get(risk.lower(), 0.3)
        
        # Length/complexity indicators (0.0-0.2)
        if issue_length is None:
            issue_length = len(issue_description)
        
        if issue_length > 500:
            score += 0.15
        elif issue_length > 300:
            score += 0.1
        
        # Complexity keywords (0.0-0.2)
        complexity_keywords = [
            "complex", "multiple", "cascade", "intermittent", "sporadic",
            "escalate", "critical", "urgent", "production down", "outage",
            "correlated", "related", "chain", "sequence", "dependency"
        ]
        keyword_matches = sum(1 for keyword in complexity_keywords if keyword in issue_lower)
        if keyword_matches >= 3:
            score += 0.2
        elif keyword_matches >= 2:
            score += 0.15
        elif keyword_matches >= 1:
            score += 0.1
        
        # Service complexity (0.0-0.1)
        # Database and network issues tend to be more complex
        complex_services = ["database", "network"]
        if service_type in complex_services:
            score += 0.1
        
        # Cap at 1.0
        return min(score, 1.0)
    
    @staticmethod
    def select_model(
        issue_description: str,
        risk: str,
        service_type: str,
        issue_length: Optional[int] = None
    ) -> str:
        """
        Select appropriate model based on complexity.
        
        Args:
            issue_description: Issue description text
            risk: Risk level (low, medium, high, critical)
            service_type: Service type (server, network, database, web, storage)
            issue_length: Optional pre-calculated length
            
        Returns:
            str: Model name from MODEL_PRIORITY
        """
        complexity = ModelSelector.calculate_complexity(
            issue_description, risk, service_type, issue_length
        )
        
        # Get current model priority (may have changed via env)
        model_priority = get_model_priority()
        
        # Ensure we have at least 3 models
        if len(model_priority) < 3:
            logger.warning(f"Model priority list has only {len(model_priority)} models, need 3. Using defaults.")
            model_priority = [
                "gemini-2.0-flash-exp",
                "gemini-2.5-flash",
                "gemini-2.5-pro"
            ]
        
        # Model selection based on complexity thresholds
        if complexity >= 0.95:
            # 5% of cases - most complex, use Pro
            model = model_priority[2]  # Most capable model
            logger.info(f"[MODEL_SELECT] Complexity: {complexity:.2f} → {model} (complex)")
        elif complexity >= 0.8:
            # 15% of cases - moderate complexity, use Flash
            model = model_priority[1]  # Middle tier model
            logger.info(f"[MODEL_SELECT] Complexity: {complexity:.2f} → {model} (moderate)")
        else:
            # 80% of cases - simple, use stable Flash (n-1 strategy)
            model = model_priority[0]  # Stable, fast model
            logger.info(f"[MODEL_SELECT] Complexity: {complexity:.2f} → {model} (simple)")
        
        return model

