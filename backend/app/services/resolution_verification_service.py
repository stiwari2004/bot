"""
Resolution Verification Service — verify if ticket issue is resolved after runbook execution
"""
from sqlalchemy.orm import Session
from app.core.logging import get_logger
from app.models.ticket import Ticket
from app.models.execution_session import ExecutionSession, ExecutionStep
from app.services.ticket_status_service import get_ticket_status_service
from app.services.threshold_service import get_threshold_service
from app.services.ticketing_integration_service import get_ticketing_integration_service
from app.services.resolution_checker import ResolutionChecker
from app.services.llm_resolution_analyzer import LLMResolutionAnalyzer
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import json

logger = get_logger(__name__)


class ResolutionVerificationService:
    """Service for verifying if ticket issues are resolved after runbook execution"""

    def __init__(self):
        self.ticket_status_service = get_ticket_status_service()
        self.threshold_service = get_threshold_service()
        self.ticketing_integration_service = get_ticketing_integration_service()
        self._checker = ResolutionChecker(self.threshold_service)
        self._llm_analyzer = LLMResolutionAnalyzer()

    async def verify_resolution(
        self,
        db: Session,
        session_id: int,
        ticket_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        try:
            session = db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
            if not session:
                raise ValueError(f"Execution session {session_id} not found")

            if not ticket_id:
                ticket_id = session.ticket_id

            if not ticket_id:
                logger.warning(f"No ticket_id for session {session_id}, skipping resolution verification")
                return {"resolved": False, "confidence": 0.0, "reasoning": "No ticket associated with execution", "verification_method": "none"}

            ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
            if not ticket:
                logger.warning(f"Ticket {ticket_id} not found")
                return {"resolved": False, "confidence": 0.0, "reasoning": "Ticket not found", "verification_method": "none"}

            if session.status != "completed":
                return {
                    "resolved": False, "confidence": 0.0,
                    "reasoning": f"Execution not completed (status: {session.status})",
                    "verification_method": "execution_status",
                }

            all_steps = db.query(ExecutionStep).filter(ExecutionStep.session_id == session_id).all()
            if not all_steps:
                return {"resolved": False, "confidence": 0.0, "reasoning": "No execution steps found", "verification_method": "step_analysis"}

            successful_steps = [s for s in all_steps if s.completed and s.success]
            failed_steps = [s for s in all_steps if s.completed and s.success is False]
            success_rate = len(successful_steps) / len(all_steps) if all_steps else 0.0

            postchecks = [s for s in all_steps if s.step_type == "postcheck"]
            prechecks = [s for s in all_steps if s.step_type == "precheck"]

            if prechecks and postchecks:
                comparison_result = self._checker.compare_precheck_postcheck(
                    db=db, ticket_id=ticket_id, prechecks=prechecks, postchecks=postchecks
                )
                if comparison_result:
                    resolved = comparison_result["resolved"]
                    confidence = comparison_result["confidence"]
                    reasoning = comparison_result["reasoning"]
                    verification_method = "precheck_postcheck_comparison"
                else:
                    postcheck_success = all(s.success for s in postchecks if s.completed)
                    resolved = success_rate == 1.0 and postcheck_success
                    confidence = 0.7 if resolved else 0.5
                    reasoning = f"Postchecks passed: {postcheck_success}, but could not compare metrics"
                    verification_method = "step_analysis"
            else:
                postcheck_success = all(s.success for s in postchecks if s.completed) if postchecks else True
                if success_rate == 1.0 and postcheck_success:
                    resolved, confidence = True, 0.9
                    reasoning = "All execution steps completed successfully"
                elif success_rate >= 0.8:
                    resolved, confidence = True, 0.7
                    reasoning = f"Most steps succeeded ({len(successful_steps)}/{len(all_steps)})"
                elif success_rate >= 0.5:
                    resolved, confidence = False, 0.5
                    reasoning = f"Mixed results ({len(successful_steps)}/{len(all_steps)} steps succeeded)"
                else:
                    resolved, confidence = False, 0.9
                    reasoning = f"Most steps failed ({len(failed_steps)}/{len(all_steps)} steps failed)"
                verification_method = "step_analysis"

            llm_result = await self._llm_analyzer.analyze_resolution(
                ticket=ticket, session=session, all_steps=all_steps,
                initial_resolved=resolved, initial_confidence=confidence, initial_reasoning=reasoning,
            )
            if llm_result and llm_result.get("confidence", 0) > confidence:
                resolved = llm_result["resolved"]
                confidence = llm_result["confidence"]
                reasoning = llm_result["reasoning"]
                verification_method = "llm_analysis"
                logger.info(f"LLM analysis overrode initial verification: resolved={resolved}, confidence={confidence:.2f}")

            if resolved:
                self.ticket_status_service.update_ticket_on_execution_complete(db, ticket_id, "completed", issue_resolved=True)
                ticket.resolution_verified_at = datetime.now(timezone.utc)
                db.commit()
                db.refresh(ticket)
                if ticket.external_id:
                    try:
                        success = await self.ticketing_integration_service.resolve_ticket(db=db, ticket=ticket, resolution_notes=reasoning)
                        if success:
                            logger.info(f"Successfully updated external ticket {ticket.external_id} to resolved")
                        else:
                            logger.warning(f"Failed to update external ticket {ticket.external_id}")
                    except Exception as e:
                        logger.error(f"Error updating external ticket {ticket.external_id}: {e}", exc_info=True)
                else:
                    logger.warning(f"Ticket {ticket_id} has no external_id, skipping external update")
            else:
                if confidence < 0.7:
                    self.ticket_status_service.update_ticket_on_execution_complete(db, ticket_id, "completed", issue_resolved=None)
                    ticket.escalation_reason = f"Uncertain resolution: {reasoning}"
                    db.commit()
                    await self.ticketing_integration_service.mark_for_manual_review(
                        db=db, ticket=ticket, reason=f"Uncertain resolution: {reasoning}"
                    )
                else:
                    self.ticket_status_service.update_ticket_on_execution_complete(db, ticket_id, "completed", issue_resolved=False)
                    ticket.escalation_reason = f"Issue not resolved: {reasoning}"
                    db.commit()

                    execution_context = {
                        "success_rate": success_rate,
                        "total_steps": len(all_steps),
                        "successful_steps": len(successful_steps),
                        "failed_steps": len(failed_steps),
                        "failed_step_details": [
                            {"step_id": s.id, "step_name": s.step_name or f"Step {s.step_number}",
                             "error": s.error_message or "Unknown error", "output": s.output[:500] if s.output else None}
                            for s in failed_steps[:5]
                        ],
                        "verification_method": verification_method,
                        "confidence": confidence,
                        "reasoning": reasoning,
                    }

                    should_heal = await self._should_attempt_self_healing(db=db, session=session, ticket=ticket, confidence=confidence)
                    if should_heal:
                        logger.info(f"Attempting self-healing for ticket {ticket_id} after failed execution")
                        try:
                            remediation_id = await self._attempt_self_healing(
                                db=db, session=session, ticket=ticket, execution_context=execution_context
                            )
                            if remediation_id:
                                logger.info(f"Self-healing remediation session {remediation_id} created for ticket {ticket_id}")
                                return {
                                    "resolved": False, "confidence": confidence,
                                    "reasoning": f"Issue not resolved, attempting self-healing remediation (session {remediation_id})",
                                    "verification_method": verification_method,
                                    "success_rate": success_rate, "total_steps": len(all_steps),
                                    "successful_steps": len(successful_steps), "failed_steps": len(failed_steps),
                                    "remediation_session_id": remediation_id,
                                }
                        except Exception as e:
                            logger.error(f"Self-healing attempt failed: {e}", exc_info=True)

                    await self.ticketing_integration_service.escalate_ticket(
                        db=db, ticket=ticket,
                        escalation_reason=f"Issue not resolved: {reasoning}",
                        execution_context=execution_context,
                    )

            logger.info(
                f"Resolution verification for ticket {ticket_id}: "
                f"resolved={resolved}, confidence={confidence:.2f}, method={verification_method}"
            )
            return {
                "resolved": resolved, "confidence": confidence,
                "reasoning": reasoning, "verification_method": verification_method,
                "success_rate": success_rate, "total_steps": len(all_steps),
                "successful_steps": len(successful_steps), "failed_steps": len(failed_steps),
            }

        except Exception as e:
            logger.error(f"Error verifying resolution for session {session_id}: {e}")
            return {"resolved": False, "confidence": 0.0, "reasoning": f"Verification failed: {str(e)}", "verification_method": "error"}

    async def verify_resolution_with_llm(
        self,
        db: Session,
        session_id: int,
        ticket_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        try:
            session = db.query(ExecutionSession).filter(ExecutionSession.id == session_id).first()
            if not session:
                raise ValueError(f"Execution session {session_id} not found")

            if not ticket_id:
                ticket_id = session.ticket_id

            if not ticket_id or session.status != "completed":
                return await self.verify_resolution(db, session_id, ticket_id)

            ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
            if not ticket:
                return await self.verify_resolution(db, session_id, ticket_id)

            all_steps = db.query(ExecutionStep).filter(
                ExecutionStep.session_id == session_id
            ).order_by(ExecutionStep.step_number).all()

            if not all_steps:
                return await self.verify_resolution(db, session_id, ticket_id)

            base_result = await self.verify_resolution(db, session_id, ticket_id)

            try:
                from app.services.llm_service import get_llm_service
                llm_service = get_llm_service()

                step_outputs = [
                    {
                        "step_number": step.step_number,
                        "step_type": step.step_type,
                        "command": step.command or "",
                        "completed": step.completed,
                        "success": step.success,
                        "output": step.output or "",
                    }
                    for step in all_steps
                ]

                system_prompt = """You are an expert IT troubleshooting analyst. Your task is to analyze execution step outputs and determine if the reported issue has been resolved.

Analyze the step outputs carefully:
1. Check if remediation steps were executed successfully
2. Compare precheck and postcheck outputs to see if metrics improved
3. Look for error messages or warnings that indicate the issue persists
4. Consider the overall execution flow and whether it addressed the root cause

Respond with a JSON object containing:
- "resolved": true/false
- "confidence": 0.0-1.0
- "reasoning": "detailed explanation"
- "key_indicators": ["list of key indicators"]
"""
                user_prompt = f"""Analyze this execution session to determine if the issue is resolved:

**Original Issue:**
{ticket.issue_description or "Not specified"}

**Execution Steps:**
{json.dumps(step_outputs, indent=2)}

**Current Assessment (for reference):**
- Resolved: {base_result.get("resolved", False)}
- Confidence: {base_result.get("confidence", 0.0):.2f}
- Reasoning: {base_result.get("reasoning", "N/A")}

Provide your analysis as JSON with the structure specified above."""

                if hasattr(llm_service, "_chat_once_with_system"):
                    llm_response = await llm_service._chat_once_with_system(
                        system=system_prompt, user=user_prompt, tenant_id=ticket.tenant_id
                    )
                elif hasattr(llm_service, "_chat_once"):
                    llm_response = await llm_service._chat_once(
                        f"{system_prompt}\n\n{user_prompt}", tenant_id=ticket.tenant_id
                    )
                else:
                    logger.warning("LLM service does not support chat methods, falling back to base verification")
                    return base_result

                llm_result = self._llm_analyzer.parse_llm_response(llm_response, base_result)

                if llm_result.get("confidence", 0.0) > base_result.get("confidence", 0.0):
                    final_result = {
                        "resolved": llm_result.get("resolved", base_result.get("resolved", False)),
                        "confidence": llm_result.get("confidence", base_result.get("confidence", 0.0)),
                        "reasoning": llm_result.get("reasoning", base_result.get("reasoning", "")),
                        "verification_method": "llm_analysis",
                        "llm_analysis": llm_result,
                        "base_verification": base_result,
                        "success_rate": base_result.get("success_rate", 0.0),
                        "total_steps": base_result.get("total_steps", len(all_steps)),
                        "successful_steps": base_result.get("successful_steps", 0),
                        "failed_steps": base_result.get("failed_steps", 0),
                    }
                else:
                    final_result = {**base_result, "verification_method": "hybrid", "llm_analysis": llm_result}

                logger.info(
                    f"LLM resolution verification for ticket {ticket_id}: "
                    f"resolved={final_result.get('resolved')}, confidence={final_result.get('confidence'):.2f}"
                )

                if final_result.get("resolved"):
                    self.ticket_status_service.update_ticket_on_execution_complete(db, ticket_id, "completed", issue_resolved=True)
                    ticket.resolution_verified_at = datetime.now(timezone.utc)
                    db.commit()
                    db.refresh(ticket)
                    if ticket.external_id:
                        try:
                            await self.ticketing_integration_service.resolve_ticket(
                                db=db, ticket=ticket, resolution_notes=final_result.get("reasoning", "")
                            )
                        except Exception as e:
                            logger.error(f"Error updating external ticket: {e}", exc_info=True)
                else:
                    if final_result.get("confidence", 0.0) < 0.7:
                        self.ticket_status_service.update_ticket_on_execution_complete(db, ticket_id, "completed", issue_resolved=None)
                        await self.ticketing_integration_service.mark_for_manual_review(
                            db=db, ticket=ticket, reason=final_result.get("reasoning", "Uncertain resolution")
                        )
                    else:
                        self.ticket_status_service.update_ticket_on_execution_complete(db, ticket_id, "completed", issue_resolved=False)
                        await self.ticketing_integration_service.escalate_ticket(
                            db=db, ticket=ticket, escalation_reason=final_result.get("reasoning", "Issue not resolved")
                        )

                return final_result

            except Exception as llm_error:
                logger.error(f"LLM analysis failed, falling back to base verification: {llm_error}", exc_info=True)
                return base_result

        except Exception as e:
            logger.error(f"Error in LLM resolution verification for session {session_id}: {e}", exc_info=True)
            return await self.verify_resolution(db, session_id, ticket_id)

    async def _should_attempt_self_healing(
        self,
        db: Session,
        session: ExecutionSession,
        ticket: Ticket,
        confidence: float,
    ) -> bool:
        try:
            if confidence < 0.7:
                return False
            from app.services.self_healing.time_remaining_service import get_time_remaining_service
            time_service = get_time_remaining_service()
            has_time, reason = time_service.has_sufficient_time(db, ticket, session)
            if not has_time:
                logger.info(f"Self-healing skipped for ticket {ticket.id}: {reason}")
                return False
            return True
        except Exception as e:
            logger.error(f"Error checking self-healing eligibility: {e}", exc_info=True)
            return False

    async def _attempt_self_healing(
        self,
        db: Session,
        session: ExecutionSession,
        ticket: Ticket,
        execution_context: Dict[str, Any],
    ) -> Optional[int]:
        try:
            from app.services.self_healing.post_execution_analysis_service import get_post_execution_analysis_service
            from app.services.self_healing.dynamic_remediation_generator import get_dynamic_remediation_generator
            from app.models.execution_session import ExecutionSession as ExecutionSessionModel

            analysis_service = get_post_execution_analysis_service()
            analysis_result = await analysis_service.analyze_execution(db=db, session_id=session.id, ticket=ticket)

            if not analysis_result.get("remediation_needed", False):
                logger.info(f"Post-execution analysis does not recommend remediation for ticket {ticket.id}")
                return None

            if analysis_result.get("confidence", 0.0) < 0.6:
                logger.info(f"Remediation confidence too low for ticket {ticket.id}")
                return None

            remediation_generator = get_dynamic_remediation_generator()
            remediation_definition = await remediation_generator.generate_remediation_steps(
                db=db, analysis_result=analysis_result, ticket=ticket, original_runbook_id=session.runbook_id
            )

            if remediation_definition.get("validation_errors"):
                logger.warning(f"Remediation steps have validation errors: {remediation_definition['validation_errors']}")

            if not remediation_definition.get("steps"):
                logger.warning(f"No remediation steps generated for ticket {ticket.id}")
                return None

            remediation_session = ExecutionSessionModel(
                tenant_id=session.tenant_id,
                runbook_id=session.runbook_id,
                ticket_id=ticket.id,
                parent_session_id=session.id,
                issue_description=f"Self-healing remediation for ticket {ticket.id}",
                status="pending",
                user_id=session.user_id,
            )
            db.add(remediation_session)
            db.flush()

            logger.info(
                f"Created remediation session {remediation_session.id} for ticket {ticket.id} "
                f"with {len(remediation_definition['steps'])} steps"
            )
            return remediation_session.id

        except Exception as e:
            logger.error(f"Error attempting self-healing: {e}", exc_info=True)
            return None


# Global instance
_resolution_verification_service: Optional[ResolutionVerificationService] = None


def get_resolution_verification_service() -> ResolutionVerificationService:
    global _resolution_verification_service
    if _resolution_verification_service is None:
        _resolution_verification_service = ResolutionVerificationService()
    return _resolution_verification_service
