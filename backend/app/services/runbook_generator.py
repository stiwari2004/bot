"""
Runbook generation service using RAG pipeline
"""
import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.schemas.search import SearchResult
from app.schemas.runbook import RunbookCreate, RunbookResponse
from app.models.runbook import Runbook
from app.services.vector_store import VectorStoreService


class RunbookGeneratorService:
    """Service for generating runbooks from search results using RAG"""
    
    def __init__(self):
        self.vector_service = VectorStoreService()
    
    async def generate_runbook(
        self,
        issue_description: str,
        tenant_id: int,
        db: Session,
        top_k: int = 5,
        source_types: Optional[List[str]] = None
    ) -> RunbookResponse:
        """Generate a runbook from issue description using RAG"""
        
        # Step 1: Search for relevant knowledge
        search_results = await self.vector_service.search(
            query=issue_description,
            tenant_id=tenant_id,
            db=db,
            top_k=top_k,
            source_types=source_types
        )
        
        # Step 2: Generate runbook content using retrieved knowledge
        runbook_content = await self._generate_content(issue_description, search_results)
        
        # Step 3: Calculate confidence score
        confidence = self._calculate_confidence(search_results)
        
        # Step 4: Create runbook record
        runbook = Runbook(
            tenant_id=tenant_id,
            title=f"Runbook: {issue_description[:100]}...",
            body_md=runbook_content,
            meta_data=json.dumps({
                "issue_description": issue_description,
                "sources_used": len(search_results),
                "search_query": issue_description,
                "generated_by": "rag_pipeline"
            }),
            confidence=confidence,
            is_active="active"
        )
        
        db.add(runbook)
        db.commit()
        db.refresh(runbook)
        
        return RunbookResponse(
            id=runbook.id,
            title=runbook.title,
            body_md=runbook.body_md,
            confidence=runbook.confidence,
            meta_data=json.loads(runbook.meta_data) if runbook.meta_data else {},
            created_at=runbook.created_at,
            updated_at=runbook.updated_at
        )
    
    async def _generate_content(self, issue: str, search_results: List[SearchResult]) -> str:
        """Generate runbook content from search results"""
        
        if not search_results:
            return self._generate_fallback_content(issue)
        
        # Build context from search results
        context = self._build_context(search_results)
        
        # Generate structured runbook content
        runbook_content = f"""# Troubleshooting Runbook

## Issue Description
{issue}

## Root Cause Analysis
Based on similar incidents and knowledge base, this issue typically occurs due to:

{self._extract_root_causes(search_results)}

## Troubleshooting Steps

### Step 1: Initial Assessment
{self._generate_initial_assessment(search_results)}

### Step 2: Diagnostic Commands
```bash
{self._extract_diagnostic_commands(search_results)}
```

### Step 3: Resolution Steps
{self._generate_resolution_steps(search_results)}

### Step 4: Verification
{self._generate_verification_steps(search_results)}

## Prevention Measures
{self._generate_prevention_measures(search_results)}

## References
{self._generate_references(search_results)}

---
*This runbook was generated using AI and should be reviewed before implementation.*
"""
        
        return runbook_content
    
    def _build_context(self, search_results: List[SearchResult]) -> str:
        """Build context string from search results"""
        context_parts = []
        for i, result in enumerate(search_results, 1):
            context_parts.append(f"{i}. {result.text} (Source: {result.document_source}, Score: {result.score:.3f})")
        return "\n\n".join(context_parts)
    
    def _extract_root_causes(self, search_results: List[SearchResult]) -> str:
        """Extract potential root causes from search results"""
        causes = []
        for result in search_results[:3]:  # Top 3 results
            if "caused by" in result.text.lower() or "issue" in result.text.lower():
                # Extract the cause part
                text = result.text.lower()
                if "caused by" in text:
                    cause_part = text.split("caused by")[1].split(".")[0].strip()
                    causes.append(f"- {cause_part.capitalize()}")
                elif "common issues" in text:
                    cause_part = text.split("common issues")[1].split(".")[0].strip()
                    causes.append(f"- {cause_part.capitalize()}")
        
        if not causes:
            causes = ["- Configuration issues", "- Resource constraints", "- Network connectivity problems"]
        
        return "\n".join(causes[:3])
    
    def _generate_initial_assessment(self, search_results: List[SearchResult]) -> str:
        """Generate initial assessment steps"""
        assessment = []
        for result in search_results[:2]:
            if "check" in result.text.lower() or "verify" in result.text.lower():
                # Extract check/verify steps
                text = result.text
                sentences = text.split(".")
                for sentence in sentences:
                    if "check" in sentence.lower() or "verify" in sentence.lower():
                        assessment.append(f"- {sentence.strip()}")
                        break
        
        if not assessment:
            assessment = [
                "- Check system status and logs",
                "- Verify resource utilization",
                "- Confirm network connectivity"
            ]
        
        return "\n".join(assessment[:3])
    
    def _extract_diagnostic_commands(self, search_results: List[SearchResult]) -> str:
        """Extract diagnostic commands from search results"""
        commands = []
        for result in search_results:
            text = result.text.lower()
            if "ping" in text or "traceroute" in text or "top" in text or "htop" in text:
                if "ping" in text:
                    commands.append("ping -c 4 <target_host>")
                if "traceroute" in text:
                    commands.append("traceroute <target_host>")
                if "top" in text or "htop" in text:
                    commands.append("top")
                    commands.append("htop")
        
        if not commands:
            commands = [
                "ping -c 4 <target_host>",
                "traceroute <target_host>",
                "top",
                "df -h",
                "free -m"
            ]
        
        return "\n".join(commands[:5])
    
    def _generate_resolution_steps(self, search_results: List[SearchResult]) -> str:
        """Generate resolution steps from search results"""
        steps = []
        for result in search_results[:3]:
            text = result.text
            sentences = text.split(".")
            for sentence in sentences:
                if any(keyword in sentence.lower() for keyword in ["restart", "fix", "resolve", "update", "configure"]):
                    steps.append(f"- {sentence.strip()}")
                    break
        
        if not steps:
            steps = [
                "- Restart the affected service",
                "- Check and update configuration if needed",
                "- Verify all dependencies are running"
            ]
        
        return "\n".join(steps[:4])
    
    def _generate_verification_steps(self, search_results: List[SearchResult]) -> str:
        """Generate verification steps"""
        return """- Verify the issue is resolved
- Check system logs for any errors
- Monitor system performance for 15 minutes
- Confirm all services are running normally"""
    
    def _generate_prevention_measures(self, search_results: List[SearchResult]) -> str:
        """Generate prevention measures"""
        return """- Implement monitoring and alerting
- Regular system maintenance and updates
- Document configuration changes
- Set up automated backups"""
    
    def _generate_references(self, search_results: List[SearchResult]) -> str:
        """Generate reference links"""
        references = []
        for i, result in enumerate(search_results, 1):
            references.append(f"{i}. {result.document_title} (Score: {result.score:.3f})")
        return "\n".join(references)
    
    def _calculate_confidence(self, search_results: List[SearchResult]) -> float:
        """Calculate confidence score based on search results"""
        if not search_results:
            return 0.3  # Low confidence if no results
        
        # Base confidence on top result score
        top_score = search_results[0].score
        
        # Adjust based on number of results
        result_count_factor = min(len(search_results) / 5.0, 1.0)
        
        # Calculate final confidence
        confidence = (top_score * 0.7) + (result_count_factor * 0.3)
        
        return min(confidence, 0.95)  # Cap at 95%
    
    def _generate_fallback_content(self, issue: str) -> str:
        """Generate fallback content when no search results"""
        return f"""# Troubleshooting Runbook

## Issue Description
{issue}

## Root Cause Analysis
Unable to find specific information about this issue in the knowledge base.

## Troubleshooting Steps

### Step 1: Initial Assessment
- Check system status and logs
- Verify resource utilization
- Confirm network connectivity

### Step 2: Diagnostic Commands
```bash
ping -c 4 <target_host>
traceroute <target_host>
top
df -h
free -m
```

### Step 3: Resolution Steps
- Review system logs for error messages
- Check configuration files
- Restart affected services
- Verify all dependencies are running

### Step 4: Verification
- Verify the issue is resolved
- Check system logs for any errors
- Monitor system performance

## Prevention Measures
- Implement monitoring and alerting
- Regular system maintenance
- Document configuration changes

---
*This runbook was generated with limited knowledge base information. Manual review required.*
"""