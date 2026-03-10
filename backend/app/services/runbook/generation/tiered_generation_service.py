"""
Tiered runbook generation service.

Tier 0 (score >= 0.90): Return proven existing runbook directly — $0 LLM cost, 0 hallucination.
Tier 1 (0.70 <= score < 0.90): Adapt existing runbook for new issue via single focused LLM call.
Tier 2 (score < 0.70 or no match): Full generation (handled by caller).
"""
import json
import yaml
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.runbook import Runbook
from app.schemas.runbook import RunbookResponse

logger = get_logger(__name__)

TIER0_THRESHOLD = 0.90  # High enough confidence to reuse without changes
TIER1_THRESHOLD = 0.70  # Enough overlap to adapt rather than generate from scratch


class TieredGenerationService:
    """
    Checks whether an incident matches an existing runbook well enough to reuse (Tier 0)
    or adapt (Tier 1) rather than generating from scratch (Tier 2).
    """

    async def select_tier_and_execute(
        self,
        issue_description: str,
        tenant_id: int,
        db: Session,
        service: str,
        env: str,
        risk: str,
        os_type: Optional[str] = None,
    ) -> Optional[RunbookResponse]:
        """
        Try Tier 0 then Tier 1. Returns a RunbookResponse if a tier succeeds.
        Returns None if the caller should proceed with Tier 2 (full generation).
        """
        try:
            from app.services.runbook_search import RunbookSearchService
            search_svc = RunbookSearchService()
            matches = await search_svc.search_similar_runbooks(
                issue_description=issue_description,
                tenant_id=tenant_id,
                db=db,
                top_k=3,
                min_confidence=TIER1_THRESHOLD,
            )
        except Exception as e:
            logger.warning(f"Tier check search failed, falling through to Tier 2: {e}")
            return None

        if not matches:
            logger.info("Tiered generation: no match >= %.2f — proceeding to Tier 2", TIER1_THRESHOLD)
            return None

        best = matches[0]
        score = best.get("confidence_score", 0.0)
        runbook_id = best.get("id")

        if not runbook_id:
            return None

        if score >= TIER0_THRESHOLD:
            logger.info(
                "Tiered generation: Tier 0 REUSE — runbook_id=%s score=%.3f", runbook_id, score
            )
            return await self._execute_tier0(
                runbook_id=runbook_id,
                tenant_id=tenant_id,
                db=db,
                issue_description=issue_description,
                score=score,
            )
        else:
            logger.info(
                "Tiered generation: Tier 1 ADAPT — runbook_id=%s score=%.3f", runbook_id, score
            )
            return await self._execute_tier1(
                source_runbook_id=runbook_id,
                tenant_id=tenant_id,
                db=db,
                issue_description=issue_description,
                service=service,
                env=env,
                risk=risk,
                os_type=os_type,
                score=score,
            )

    # ------------------------------------------------------------------ #
    # Tier 0 — return the existing runbook as-is, update reuse stats      #
    # ------------------------------------------------------------------ #

    async def _execute_tier0(
        self,
        runbook_id: int,
        tenant_id: int,
        db: Session,
        issue_description: str,
        score: float,
    ) -> Optional[RunbookResponse]:
        """Return the matching runbook directly. Update reuse stats in meta_data."""
        try:
            runbook = db.query(Runbook).filter(
                Runbook.id == runbook_id,
                Runbook.tenant_id == tenant_id,
            ).first()

            if not runbook:
                logger.warning("Tier 0: runbook %s not found, falling through", runbook_id)
                return None

            # Update reuse tracking in meta_data
            meta: Dict[str, Any] = {}
            if runbook.meta_data:
                try:
                    meta = json.loads(runbook.meta_data) if isinstance(runbook.meta_data, str) else runbook.meta_data
                except Exception:
                    meta = {}

            meta["reuse_count"] = meta.get("reuse_count", 0) + 1
            meta["generation_mode"] = "tier0_reuse"
            meta["last_reuse_score"] = round(score, 4)
            meta["last_reuse_issue"] = issue_description[:200]
            runbook.meta_data = json.dumps(meta)
            db.commit()
            db.refresh(runbook)

            meta_parsed = json.loads(runbook.meta_data) if runbook.meta_data else {}
            return RunbookResponse(
                id=runbook.id,
                title=runbook.title,
                body_md=runbook.body_md,
                confidence=min(1.0, score + 0.05),  # Slightly boosted for proven match
                meta_data=meta_parsed,
                created_at=runbook.created_at,
                updated_at=runbook.updated_at,
            )
        except Exception as e:
            logger.warning("Tier 0 execution failed (%s), falling through to Tier 2", e)
            return None

    # ------------------------------------------------------------------ #
    # Tier 1 — adapt existing runbook for new issue via single LLM call  #
    # ------------------------------------------------------------------ #

    async def _execute_tier1(
        self,
        source_runbook_id: int,
        tenant_id: int,
        db: Session,
        issue_description: str,
        service: str,
        env: str,
        risk: str,
        os_type: Optional[str],
        score: float,
    ) -> Optional[RunbookResponse]:
        """
        Use the existing runbook YAML as a template. Ask LLM to make minimal
        adaptations for the new issue. Create and persist the adapted runbook.
        """
        try:
            source_runbook = db.query(Runbook).filter(
                Runbook.id == source_runbook_id,
                Runbook.tenant_id == tenant_id,
            ).first()

            if not source_runbook:
                logger.warning("Tier 1: source runbook %s not found, falling through", source_runbook_id)
                return None

            # Extract the existing YAML spec
            existing_yaml = self._extract_yaml_from_runbook(source_runbook)
            if not existing_yaml:
                logger.warning("Tier 1: could not extract YAML from runbook %s", source_runbook_id)
                return None

            # Call LLM to adapt
            adapted_yaml = await self._adapt_with_llm(
                existing_yaml=existing_yaml,
                issue_description=issue_description,
                service=service,
                env=env,
                risk=risk,
                os_type=os_type,
                tenant_id=tenant_id,
            )

            if not adapted_yaml or not adapted_yaml.strip():
                logger.warning("Tier 1: LLM returned empty adaptation, falling through to Tier 2")
                return None

            # Parse and validate
            try:
                spec = yaml.safe_load(adapted_yaml)
                if not isinstance(spec, dict) or "steps" not in spec:
                    raise ValueError("Adapted YAML missing required structure")
            except Exception as parse_err:
                logger.warning("Tier 1: adapted YAML parse failed (%s), falling through", parse_err)
                return None

            # Save as new runbook
            body_md = f"# Agent Runbook (YAML) — Adapted\n\n```yaml\n{adapted_yaml}\n```\n"
            new_runbook = Runbook(
                tenant_id=tenant_id,
                title=f"Runbook: {spec.get('title', issue_description[:80])}",
                body_md=body_md,
                meta_data=json.dumps({
                    "issue_description": issue_description,
                    "generated_by": "agent_yaml",
                    "generation_mode": "tier1_adapted",
                    "source_runbook_id": source_runbook_id,
                    "source_score": round(score, 4),
                    "service": service,
                    "env": env,
                    "risk": risk,
                    "runbook_spec": spec,
                }),
                confidence=round(score * 0.95, 4),  # Slightly lower than source — it's adapted
                is_active="active",
            )

            # Inherit environment from config
            try:
                from app.core.config import settings
                new_runbook.environment = "dev" if settings.ENVIRONMENT == "development" else "production"
            except Exception:
                pass

            db.add(new_runbook)
            db.commit()
            db.refresh(new_runbook)

            logger.info(
                "Tier 1: created adapted runbook id=%s from source id=%s (score=%.3f)",
                new_runbook.id, source_runbook_id, score,
            )

            meta_parsed = json.loads(new_runbook.meta_data) if new_runbook.meta_data else {}
            return RunbookResponse(
                id=new_runbook.id,
                title=new_runbook.title,
                body_md=new_runbook.body_md,
                confidence=new_runbook.confidence,
                meta_data=meta_parsed,
                created_at=new_runbook.created_at,
                updated_at=new_runbook.updated_at,
            )

        except Exception as e:
            logger.warning("Tier 1 execution failed (%s), falling through to Tier 2", e)
            return None

    def _extract_yaml_from_runbook(self, runbook: Runbook) -> Optional[str]:
        """Extract YAML string from a runbook — prefer spec from meta_data, fallback to body_md."""
        # Try to get clean YAML from stored spec in meta_data
        if runbook.meta_data:
            try:
                meta = json.loads(runbook.meta_data) if isinstance(runbook.meta_data, str) else runbook.meta_data
                spec = meta.get("runbook_spec")
                if spec and isinstance(spec, dict) and "steps" in spec:
                    from collections import OrderedDict
                    order = ["runbook_id", "version", "title", "service", "env", "risk",
                             "description", "inputs", "prechecks", "steps", "postchecks"]
                    ordered = OrderedDict()
                    for key in order:
                        if key in spec:
                            ordered[key] = spec[key]
                    for key, value in spec.items():
                        if key not in ordered:
                            ordered[key] = value
                    return yaml.safe_dump(dict(ordered), sort_keys=False, default_flow_style=False, width=120)
            except Exception:
                pass

        # Fallback: extract YAML from body_md code fence
        body = runbook.body_md or ""
        if "```yaml" in body:
            start = body.find("```yaml") + 7
            end = body.find("```", start)
            if end > start:
                return body[start:end].strip()
        if "```" in body:
            start = body.find("```") + 3
            end = body.find("```", start)
            if end > start:
                return body[start:end].strip()

        return None

    async def _adapt_with_llm(
        self,
        existing_yaml: str,
        issue_description: str,
        service: str,
        env: str,
        risk: str,
        os_type: Optional[str],
        tenant_id: int,
    ) -> Optional[str]:
        """Call LLM with a focused adaptation prompt. Much cheaper than full generation."""
        try:
            from app.services.prompt_store import render_prompt
            from app.services.llm_service import get_llm_service

            # Truncate existing YAML to avoid context overflow (keep first 3000 chars)
            yaml_excerpt = existing_yaml[:3000]
            if len(existing_yaml) > 3000:
                yaml_excerpt += "\n# ... (truncated for brevity)"

            variables = {
                "existing_yaml": yaml_excerpt,
                "issue_description": issue_description,
                "service": service,
                "env": env,
                "risk": risk,
                "os_type": os_type or "Linux",
            }

            try:
                rendered = render_prompt("runbook_yaml_adapt", variables)
            except Exception as prompt_err:
                logger.warning("Tier 1: adapt POML not found (%s), using inline prompt", prompt_err)
                rendered = self._inline_adapt_prompt(variables)

            system_msg = rendered.get("system", "You are a precise YAML generator.")
            user_msg = rendered.get("user", "")

            llm = get_llm_service()
            raw = await llm._chat_once_with_system(system_msg, user_msg, tenant_id=tenant_id)

            if not raw or not raw.strip():
                return None

            # Strip markdown fences if present
            if "```" in raw:
                lines = raw.strip().split("\n")
                start_idx, end_idx = 0, len(lines)
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    if stripped.startswith("```"):
                        if i == 0 or "yaml" in stripped.lower():
                            start_idx = i + 1
                        else:
                            end_idx = i
                            break
                raw = "\n".join(lines[start_idx:end_idx]).strip()

            return raw

        except Exception as e:
            logger.warning("Tier 1: LLM adaptation call failed: %s", e)
            return None

    def _inline_adapt_prompt(self, variables: Dict[str, Any]) -> Dict[str, str]:
        """Fallback inline prompt if POML file is not found."""
        system = (
            "You are an expert SRE runbook adapter. "
            "Given a proven existing runbook, adapt it minimally for a new but similar issue. "
            "Return only raw YAML — no markdown fences, no explanations."
        )
        user = (
            f"EXISTING PROVEN RUNBOOK:\n{variables['existing_yaml']}\n\n"
            f"NEW ISSUE: {variables['issue_description']}\n"
            f"SERVICE: {variables['service']}, ENV: {variables['env']}, RISK: {variables['risk']}\n"
            f"OS: {variables.get('os_type', 'Linux')}\n\n"
            "Adapt the runbook for the new issue. Keep structure and purpose markers. "
            "Change only what's necessary (commands, title, description, runbook_id). "
            "Return complete valid YAML."
        )
        return {"system": system, "user": user}
