"""
Post-Execution Analysis Service
Analyzes runbook execution outputs after completion to determine if remediation is needed
Single LLM call per failed runbook (cost-optimized)
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.core.logging import get_logger
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.models.ticket import Ticket
import json

logger = get_logger(__name__)


class PostExecutionAnalysisService:
    """Service for analyzing execution outputs and determining remediation needs"""
    
    async def analyze_execution(
        self,
        db: Session,
        session_id: int,
        ticket: Ticket
    ) -> Dict[str, Any]:
        """
        Analyze execution session outputs to determine if remediation is needed
        
        Args:
            db: Database session
            session_id: Execution session ID
            ticket: Associated ticket
            
        Returns:
            {
                "remediation_needed": bool,
                "confidence": float (0.0-1.0),
                "analysis": str,
                "recommended_actions": List[str],
                "root_cause": Optional[str],
                "error_patterns": List[str]
            }
        """
        try:
            # Get execution session
            session = db.query(ExecutionSession).filter(
                ExecutionSession.id == session_id
            ).first()
            
            if not session:
                raise ValueError(f"Execution session {session_id} not found")
            
            # Get all execution steps
            all_steps = db.query(ExecutionStep).filter(
                ExecutionStep.session_id == session_id
            ).order_by(ExecutionStep.step_number).all()
            
            if not all_steps:
                return {
                    "remediation_needed": False,
                    "confidence": 0.0,
                    "analysis": "No execution steps found",
                    "recommended_actions": [],
                    "root_cause": None,
                    "error_patterns": []
                }
            
            # Build execution context for LLM analysis
            execution_context = self._build_execution_context(session, all_steps, ticket)
            
            # Single LLM call to analyze everything
            analysis_result = await self._llm_analyze_execution(
                execution_context=execution_context,
                ticket=ticket,
                tenant_id=ticket.tenant_id
            )
            
            logger.info(
                f"Post-execution analysis for session {session_id}: "
                f"remediation_needed={analysis_result.get('remediation_needed')}, "
                f"confidence={analysis_result.get('confidence', 0.0):.2f}"
            )
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error in post-execution analysis for session {session_id}: {e}", exc_info=True)
            return {
                "remediation_needed": False,
                "confidence": 0.0,
                "analysis": f"Analysis failed: {str(e)}",
                "recommended_actions": [],
                "root_cause": None,
                "error_patterns": []
            }
    
    def _build_execution_context(
        self,
        session: ExecutionSession,
        steps: List[ExecutionStep],
        ticket: Ticket
    ) -> Dict[str, Any]:
        """Build execution context from session and steps"""
        
        # Categorize steps
        successful_steps = [s for s in steps if s.completed and s.success]
        failed_steps = [s for s in steps if s.completed and s.success is False]
        incomplete_steps = [s for s in steps if not s.completed]
        
        # Extract step details
        step_details = []
        for step in steps:
            step_info = {
                "step_number": step.step_number,
                "step_name": step.step_name or f"Step {step.step_number}",
                "step_type": step.step_type,
                "command": step.command or "",
                "completed": step.completed,
                "success": step.success,
                "output": (step.output or "")[:1000],  # Limit output length
                "error_message": step.error_message or "",
                "duration_seconds": step.duration_seconds
            }
            step_details.append(step_info)
        
        # Extract error patterns
        error_patterns = []
        for step in failed_steps:
            if step.error_message:
                error_patterns.append(step.error_message[:200])
            elif step.output:
                # Try to extract error from output
                output_lower = step.output.lower()
                if "error" in output_lower:
                    error_start = output_lower.find("error")
                    error_snippet = step.output[error_start:error_start+200]
                    error_patterns.append(error_snippet)
        
        return {
            "session_id": session.id,
            "session_status": session.status,
            "runbook_id": session.runbook_id,
            "total_steps": len(steps),
            "successful_steps": len(successful_steps),
            "failed_steps": len(failed_steps),
            "incomplete_steps": len(incomplete_steps),
            "success_rate": len(successful_steps) / len(steps) if steps else 0.0,
            "step_details": step_details,
            "error_patterns": error_patterns[:10],  # Limit to first 10 errors
            "ticket_title": ticket.title,
            "ticket_description": ticket.description or "",
            "ticket_severity": ticket.severity,
            "ticket_environment": ticket.environment,
            "ticket_service": ticket.service
        }
    
    async def _llm_analyze_execution(
        self,
        execution_context: Dict[str, Any],
        ticket: Ticket,
        tenant_id: int
    ) -> Dict[str, Any]:
        """Use LLM to analyze execution and determine remediation needs"""
        
        system_prompt = """You are an expert IT troubleshooting analyst. Your task is to analyze a failed runbook execution and determine if remediation is needed.

Analyze the execution context carefully:
1. Review all step outputs, especially failed steps
2. Identify root causes and error patterns
3. Determine if the issue can be remediated automatically
4. Recommend specific remediation actions if remediation is feasible

Respond with a JSON object containing:
- "remediation_needed": true/false (whether automatic remediation is recommended)
- "confidence": 0.0-1.0 (confidence in your assessment)
- "analysis": "detailed analysis of what went wrong and why"
- "recommended_actions": ["list of specific remediation steps to take"]
- "root_cause": "identified root cause of the failure"
- "error_patterns": ["list of key error patterns observed"]

Only recommend remediation if:
- The root cause is clear and addressable
- Remediation steps are specific and actionable
- Confidence is at least 0.6
- The issue is not a configuration problem requiring manual intervention
"""
        
        user_prompt = f"""Analyze this failed runbook execution:

**Original Issue:**
Title: {execution_context['ticket_title']}
Description: {execution_context['ticket_description']}
Severity: {execution_context['ticket_severity']}
Environment: {execution_context['ticket_environment']}
Service: {execution_context['ticket_service']}

**Execution Summary:**
- Total Steps: {execution_context['total_steps']}
- Successful: {execution_context['successful_steps']}
- Failed: {execution_context['failed_steps']}
- Incomplete: {execution_context['incomplete_steps']}
- Success Rate: {execution_context['success_rate']:.1%}

**Execution Steps:**
{json.dumps(execution_context['step_details'], indent=2)}

**Error Patterns:**
{json.dumps(execution_context['error_patterns'], indent=2)}

Provide your analysis as JSON with the structure specified above."""
        
        try:
            from app.services.llm_service import get_llm_service
            llm_service = get_llm_service()
            
            # Use LLM service to analyze
            if hasattr(llm_service, '_chat_once_with_system'):
                llm_response = await llm_service._chat_once_with_system(
                    system=system_prompt,
                    user=user_prompt,
                    tenant_id=tenant_id
                )
            elif hasattr(llm_service, '_chat_once'):
                full_prompt = f"{system_prompt}\n\n{user_prompt}"
                llm_response = await llm_service._chat_once(
                    full_prompt,
                    tenant_id=tenant_id
                )
            else:
                logger.warning("LLM service does not support chat methods")
                return self._fallback_analysis(execution_context)
            
            # Parse LLM response
            return self._parse_llm_analysis_response(llm_response, execution_context)
            
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}", exc_info=True)
            return self._fallback_analysis(execution_context)
    
    def _parse_llm_analysis_response(
        self,
        response: str,
        execution_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse LLM JSON response"""
        import re
        
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                parsed = json.loads(json_str)
                
                # Validate and normalize
                result = {
                    "remediation_needed": bool(parsed.get('remediation_needed', False)),
                    "confidence": float(parsed.get('confidence', 0.5)),
                    "analysis": str(parsed.get('analysis', 'Analysis completed')),
                    "recommended_actions": parsed.get('recommended_actions', []),
                    "root_cause": parsed.get('root_cause'),
                    "error_patterns": parsed.get('error_patterns', [])
                }
                
                # Clamp confidence to 0-1
                result['confidence'] = max(0.0, min(1.0, result['confidence']))
                
                # Only recommend remediation if confidence >= 0.6
                if result['confidence'] < 0.6:
                    result['remediation_needed'] = False
                
                return result
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}. Response: {response[:200]}")
        
        # Fallback: extract information from text
        return self._fallback_analysis(execution_context, response)
    
    def _fallback_analysis(
        self,
        execution_context: Dict[str, Any],
        llm_response: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fallback analysis when LLM parsing fails"""
        
        success_rate = execution_context.get('success_rate', 0.0)
        failed_steps = execution_context.get('failed_steps', 0)
        
        # Conservative approach: only recommend remediation if most steps succeeded
        remediation_needed = success_rate >= 0.7 and failed_steps <= 2
        
        return {
            "remediation_needed": remediation_needed,
            "confidence": 0.5,
            "analysis": f"Fallback analysis: Success rate {success_rate:.1%}, {failed_steps} failed steps. " + 
                       (llm_response[:200] if llm_response else "LLM analysis unavailable"),
            "recommended_actions": [],
            "root_cause": "Analysis incomplete - LLM response parsing failed",
            "error_patterns": execution_context.get('error_patterns', [])[:5]
        }


# Global instance
_post_execution_analysis_service: Optional[PostExecutionAnalysisService] = None


def get_post_execution_analysis_service() -> PostExecutionAnalysisService:
    """Get or create post-execution analysis service instance"""
    global _post_execution_analysis_service
    if _post_execution_analysis_service is None:
        _post_execution_analysis_service = PostExecutionAnalysisService()
    return _post_execution_analysis_service

