"""
Gemini Model Health Checker
Periodic worker that validates Gemini model availability
Runs weekly/monthly to detect retired models
"""
import os
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from google import genai
from google.genai import types
from app.core.logging import get_logger
from app.core.database import SessionLocal
from app.models.system_config import SystemConfig

logger = get_logger(__name__)


class GeminiModelHealthChecker:
    """Periodic health checker for Gemini models"""
    
    # Models to check (from model_selector priority + fallbacks)
    MODELS_TO_CHECK = [
        "gemini-2.5-flash",      # Primary stable model
        "gemini-2.5-pro",        # Complex stable model
        "gemini-2.0-flash-exp",  # Check experimental too
        "gemini-1.5-flash",      # Fallback options
        "gemini-1.5-pro",        # Fallback options
    ]
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required")
        self.client = genai.Client(api_key=self.api_key)
    
    async def validate_model(self, model_name: str) -> Dict[str, any]:
        """
        Validate if a model is available.
        
        Returns:
            {
                "model": str,
                "available": bool,
                "error": Optional[str],
                "checked_at": str
            }
        """
        result = {
            "model": model_name,
            "available": False,
            "error": None,
            "checked_at": datetime.utcnow().isoformat()
        }
        
        try:
            # Make minimal test call
            test_content = [
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text="test")]
                )
            ]
            
            response = self.client.models.generate_content(
                model=model_name,
                contents=test_content,
                config=types.GenerateContentConfig(
                    max_output_tokens=1,
                    temperature=0.1
                )
            )
            
            # If we get here, model is available
            result["available"] = True
            logger.info(f"✅ Model available: {model_name}")
            
        except Exception as e:
            error_msg = str(e).lower()
            result["error"] = str(e)
            
            # Check if model is retired/invalid
            if any(keyword in error_msg for keyword in ["not found", "invalid", "404", "does not exist", "retired"]):
                result["available"] = False
                logger.warning(f"❌ Model RETIRED/UNAVAILABLE: {model_name} - {e}")
            else:
                # Other errors (quota, rate limit) - assume model is still available
                result["available"] = True
                logger.warning(f"⚠️ Model check error (non-fatal): {model_name} - {e}")
        
        return result
    
    async def check_all_models(self) -> Dict[str, List[Dict[str, any]]]:
        """Check all models and return results"""
        results = {
            "available": [],
            "unavailable": [],
            "errors": []
        }
        
        logger.info(f"Starting model health check for {len(self.MODELS_TO_CHECK)} models...")
        
        for model in self.MODELS_TO_CHECK:
            result = await self.validate_model(model)
            
            if result["available"]:
                results["available"].append(result)
            else:
                results["unavailable"].append(result)
            
            # Small delay between checks to avoid rate limits
            await asyncio.sleep(0.5)
        
        logger.info(
            f"Model health check complete: "
            f"{len(results['available'])} available, "
            f"{len(results['unavailable'])} unavailable"
        )
        
        return results
    
    async def save_results_to_db(self, results: Dict[str, List[Dict[str, any]]]):
        """Save health check results to database for tracking"""
        db = SessionLocal()
        try:
            # Store results in system_config table
            config_key = "gemini_model_health_check"
            config_value = {
                "last_check": datetime.utcnow().isoformat(),
                "results": results,
                "summary": {
                    "total_checked": len(self.MODELS_TO_CHECK),
                    "available": len(results["available"]),
                    "unavailable": len(results["unavailable"])
                }
            }
            
            # Update or create config entry
            import json
            config = db.query(SystemConfig).filter(
                SystemConfig.config_key == config_key
            ).first()
            
            if config:
                config.config_value = json.dumps(config_value)
                config.updated_at = datetime.utcnow()
            else:
                config = SystemConfig(
                    config_key=config_key,
                    config_value=json.dumps(config_value),
                    tenant_id=1,  # Platform-level config
                    description="Gemini model health check results"
                )
                db.add(config)
            
            db.commit()
            logger.info("Model health check results saved to database")
            
        except Exception as e:
            logger.error(f"Failed to save health check results: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def run_health_check(self):
        """Run complete health check and save results"""
        try:
            results = await self.check_all_models()
            await self.save_results_to_db(results)
            
            # Log warnings for unavailable models
            if results["unavailable"]:
                unavailable_models = [r["model"] for r in results["unavailable"]]
                logger.warning(
                    f"⚠️ UNAVAILABLE MODELS DETECTED: {unavailable_models}. "
                    f"Consider updating GEMINI_MODEL_PRIORITY in .env file."
                )
            
            return results
            
        except Exception as e:
            logger.error(f"Model health check failed: {e}", exc_info=True)
            raise

