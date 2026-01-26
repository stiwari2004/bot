"""
Schedule Calculator for calculating next run times
"""
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import Dict, Any
import pytz
from app.models.scheduled_report import ReportFrequency
from app.core.logging import get_logger

logger = get_logger(__name__)


class ScheduleCalculator:
    """Calculate next run times for scheduled reports"""
    
    @staticmethod
    def calculate_next_run_time(
        frequency: ReportFrequency,
        schedule_config: Dict[str, Any]
    ) -> datetime:
        """Calculate the next run time based on frequency and schedule config"""
        now = datetime.utcnow()
        timezone = pytz.timezone(schedule_config.get("timezone", "UTC"))
        now_tz = now.replace(tzinfo=pytz.UTC).astimezone(timezone)
        
        # Get scheduled time
        time_str = schedule_config.get("time", "09:00")
        hour, minute = map(int, time_str.split(":"))
        
        if frequency == ReportFrequency.DAILY:
            # Run daily at specified time
            next_run = now_tz.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now_tz:
                next_run += timedelta(days=1)
        
        elif frequency == ReportFrequency.WEEKLY:
            # Run weekly on specified day of week (0=Monday, 6=Sunday)
            day_of_week = schedule_config.get("day_of_week", 0)
            days_until_target = (day_of_week - now_tz.weekday()) % 7
            if days_until_target == 0 and now_tz.hour >= hour:
                days_until_target = 7
            next_run = now_tz.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=days_until_target)
        
        elif frequency == ReportFrequency.MONTHLY:
            # Run monthly on specified day of month
            day_of_month = schedule_config.get("day_of_month", 1)
            next_run = now_tz.replace(day=day_of_month, hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now_tz:
                next_run += relativedelta(months=1)
        
        else:  # CUSTOM
            # For custom, use next_run_at from config or default to tomorrow
            if "next_run_at" in schedule_config:
                next_run = datetime.fromisoformat(schedule_config["next_run_at"])
                if next_run.tzinfo is None:
                    next_run = timezone.localize(next_run)
            else:
                next_run = now_tz + timedelta(days=1)
        
        # Convert back to UTC
        return next_run.astimezone(pytz.UTC).replace(tzinfo=None)
