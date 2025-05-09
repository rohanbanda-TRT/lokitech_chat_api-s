"""
Utility functions for date and time operations.
"""

import datetime
import logging
from typing import Optional, Dict

# Configure logging
logger = logging.getLogger(__name__)

# Map day names to weekday numbers (0 = Monday, 6 = Sunday)
DAY_NAME_TO_WEEKDAY = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6
}

def get_next_day_date(day_name: str, from_date: Optional[datetime.date] = None) -> Optional[datetime.date]:
    """
    Get the date of the next occurrence of a specific day.
    
    Args:
        day_name: Name of the day (e.g., "Monday", "Tuesday")
        from_date: Optional date to calculate from (defaults to today)
        
    Returns:
        Date of the next occurrence of the specified day or None if invalid day name
    """
    try:
        # Normalize day name to lowercase
        day_name_lower = day_name.lower()
        
        # Get the weekday number for the specified day
        if day_name_lower not in DAY_NAME_TO_WEEKDAY:
            logger.error(f"Invalid day name: {day_name}")
            return None
            
        target_weekday = DAY_NAME_TO_WEEKDAY[day_name_lower]
        
        # Use today's date if from_date is not provided
        current_date = from_date or datetime.date.today()
        current_weekday = current_date.weekday()
        
        # Calculate days until the next occurrence of the target day
        days_ahead = (target_weekday - current_weekday) % 7
        
        # If days_ahead is 0 and we're looking for today's day name,
        # we want the next week's occurrence (7 days ahead)
        if days_ahead == 0:
            days_ahead = 7
            
        # Calculate the next date
        next_date = current_date + datetime.timedelta(days=days_ahead)
        
        logger.info(f"Next {day_name} from {current_date} is {next_date}")
        return next_date
        
    except Exception as e:
        logger.error(f"Error calculating next day date: {e}")
        return None

def format_next_day_with_time_slot(day_name: str, time_slot: str) -> Optional[str]:
    """
    Format a recurring time slot with the next occurrence date.
    
    Args:
        day_name: Name of the day (e.g., "Monday", "Tuesday")
        time_slot: Time slot string (e.g., "9 AM - 5 PM")
        
    Returns:
        Formatted string with date and time (e.g., "May 12, 2025 Monday 9 AM - 5 PM")
    """
    try:
        # Get the next date for the specified day
        next_date = get_next_day_date(day_name)
        if not next_date:
            return None
            
        # Format the date as "Month DD, YYYY"
        formatted_date = next_date.strftime("%B %d, %Y")
        
        # Combine the formatted date, day name, and time slot
        formatted_time_slot = f"{formatted_date} {day_name.capitalize()} {time_slot}"
        
        logger.info(f"Formatted time slot: {formatted_time_slot}")
        return formatted_time_slot
        
    except Exception as e:
        logger.error(f"Error formatting next day with time slot: {e}")
        return None
