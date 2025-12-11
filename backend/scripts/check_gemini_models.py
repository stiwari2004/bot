#!/usr/bin/env python3
"""
Periodic Gemini Model Health Checker
Run this weekly/monthly via cron or scheduled task

Usage:
    python scripts/check_gemini_models.py

Schedule examples:
    - Weekly: 0 2 * * 1 (Every Monday at 2 AM)
    - Monthly: 0 2 1 * * (First day of month at 2 AM)
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.gemini_model_health_checker import GeminiModelHealthChecker
from app.core.logging import get_logger

logger = get_logger(__name__)


async def main():
    """Run model health check"""
    try:
        print("\n" + "="*60)
        print("Gemini Model Health Check")
        print("="*60)
        print("Checking model availability...\n")
        
        checker = GeminiModelHealthChecker()
        results = await checker.run_health_check()
        
        # Print summary
        print("\n" + "="*60)
        print("Health Check Summary")
        print("="*60)
        print(f"✅ Available Models: {len(results['available'])}")
        for r in results['available']:
            print(f"   - {r['model']}")
        
        if results['unavailable']:
            print(f"\n❌ Unavailable Models: {len(results['unavailable'])}")
            for r in results['unavailable']:
                error_msg = r.get('error', 'Unknown error')
                # Truncate long error messages
                if len(error_msg) > 80:
                    error_msg = error_msg[:77] + "..."
                print(f"   - {r['model']}: {error_msg}")
        else:
            print("\n✅ All models are available!")
        
        print("="*60)
        print(f"Results saved to database (system_config: gemini_model_health_check)")
        print("="*60 + "\n")
        
        # Exit with error code if any models are unavailable
        if results['unavailable']:
            sys.exit(1)
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        print(f"\n❌ Error: {e}")
        print("Make sure GEMINI_API_KEY is set in your environment.\n")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        print(f"\n❌ Health check failed: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())





