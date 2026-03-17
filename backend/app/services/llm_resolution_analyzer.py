"""
LLM Resolution Analyzer — LLM-based analysis of execution step outputs for resolution determination
"""
import json
import re
from typing import Dict, Optional, Any, List
from app.core.logging import get_logger
from app.models.ticket import Ticket
from app.models.execution_session import ExecutionSession, ExecutionStep

logger = get_logger(__name__)


class LLMResolutionAnalyzer:
    """Uses LLM to analyze step outputs and determine if an issue is resolved"""

    async def analyze_resolution(
        self,
        ticket: Ticket,
        session: ExecutionSession,
        all_steps: List[ExecutionStep],
        initial_resolved: bool,
        initial_confidence: float,
        initial_reasoning: str,
    ) -> Optional[Dict[str, Any]]:
        try:
            from app.services.llm_service import get_llm_service

            steps_with_outputs = [s for s in all_steps if s.output and s.completed]
            if not steps_with_outputs:
                logger.debug("No step outputs to analyze with LLM, skipping LLM analysis")
                return None

            llm_service = get_llm_service()
            if not hasattr(llm_service, "_chat_once_with_system"):
                logger.warning("LLM service does not support _chat_once_with_system, skipping LLM analysis")
                return None

            step_summaries = [
                {
                    "step_name": step.step_name or f"Step {step.step_number}",
                    "success": step.success,
                    "output": step.output[:1000] if step.output else "",
                    "error": step.error_message[:500] if step.error_message else None,
                }
                for step in steps_with_outputs[:10]
            ]

            prompt = f"""Analyze whether the following issue has been resolved based on the execution steps.

Issue: {ticket.description or ticket.title}
Ticket: {ticket.title}

Execution Summary:
- Total steps: {len(all_steps)}
- Successful: {len([s for s in all_steps if s.success])}
- Failed: {len([s for s in all_steps if s.success is False])}
- Initial assessment: {"Resolved" if initial_resolved else "Not Resolved"} (confidence: {initial_confidence:.2f})
- Initial reasoning: {initial_reasoning}

Step Details:
{json.dumps(step_summaries, indent=2)}

Based on the step outputs and execution results, determine:
1. Is the issue actually resolved? (yes/no)
2. What is your confidence level? (0.0 to 1.0)
3. Provide reasoning for your assessment.

Respond in JSON format:
{{
    "resolved": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "detailed explanation"
}}"""

            response_text = await llm_service._chat_once_with_system(
                system="You are an expert IT operations analyst. Analyze execution results to determine if issues are resolved.",
                user=prompt,
                tenant_id=ticket.tenant_id,
            )

            if not response_text:
                logger.warning("LLM returned empty response for resolution analysis")
                return None

            try:
                json_match = re.search(r'\{[^{}]*"resolved"[^{}]*\}', response_text, re.DOTALL)
                analysis_result = json.loads(json_match.group(0)) if json_match else json.loads(response_text)

                if isinstance(analysis_result, dict):
                    resolved = analysis_result.get("resolved", initial_resolved)
                    confidence = max(0.0, min(1.0, float(analysis_result.get("confidence", initial_confidence))))
                    reasoning = analysis_result.get("reasoning", initial_reasoning)
                    logger.info(
                        f"LLM analysis for ticket {ticket.id}: resolved={resolved}, "
                        f"confidence={confidence:.2f}, reasoning={reasoning[:100]}..."
                    )
                    return {"resolved": resolved, "confidence": confidence, "reasoning": reasoning}

            except (json.JSONDecodeError, ValueError, KeyError) as parse_error:
                logger.warning(f"Failed to parse LLM response for resolution analysis: {parse_error}")
                return None

        except Exception as e:
            logger.error(f"Error in LLM resolution analysis: {e}", exc_info=True)
            return None

    def parse_llm_response(self, response: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
        try:
            json_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", response, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                result = {
                    "resolved": bool(parsed.get("resolved", fallback.get("resolved", False))),
                    "confidence": max(0.0, min(1.0, float(parsed.get("confidence", fallback.get("confidence", 0.5))))),
                    "reasoning": str(parsed.get("reasoning", fallback.get("reasoning", "LLM analysis completed"))),
                    "key_indicators": parsed.get("key_indicators", []),
                }
                return result
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}. Response: {response[:200]}")

        response_lower = response.lower()
        resolved = any(kw in response_lower for kw in ["resolved", "fixed", "success", "completed"])
        not_resolved = any(kw in response_lower for kw in ["not resolved", "failed", "error", "issue persists"])

        if resolved and not not_resolved:
            return {"resolved": True, "confidence": 0.7, "reasoning": f"LLM analysis suggests resolved: {response[:200]}", "key_indicators": []}
        elif not_resolved:
            return {"resolved": False, "confidence": 0.7, "reasoning": f"LLM analysis suggests not resolved: {response[:200]}", "key_indicators": []}
        else:
            return {
                "resolved": fallback.get("resolved", False),
                "confidence": fallback.get("confidence", 0.5),
                "reasoning": f"LLM analysis inconclusive, using base verification: {response[:200]}",
                "key_indicators": [],
            }
