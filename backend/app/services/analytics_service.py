"""
Analytics service - backward compatibility shim
New code should import from app.services.analytics.analytics_core instead.
"""
# Import from new location for backward compatibility
from app.services.analytics.analytics_core import AnalyticsService

__all__ = ["AnalyticsService"]

