"""
Utility functions for parsing and formatting time slots.
"""

import re
import logging
import datetime
import calendar
from typing import Optional, Tuple, List, Dict, Any, Union
from pydantic import BaseModel, Field
from .date_utils import format_next_day_with_time_slot, get_next_day_date

# Configure logging
logger = logging.getLogger(__name__)


class RecurrenceTimeSlot(BaseModel):
    """Model for a recurring time slot with advanced patterns"""
    
    pattern_type: str = Field(
        description="Type of recurrence pattern (daily, weekly, monthly, yearly)"
    )
    day_of_week: Optional[str] = Field(
        default=None, 
        description="Day of week for weekly patterns (Monday, Tuesday, etc.)"
    )
    week_of_month: Optional[Union[str, List[str]]] = Field(
        default=None,
        description="Week position(s) for monthly patterns (first, second, last, etc.). Can be a single string or a list of strings."
    )
    day_of_month: Optional[int] = Field(
        default=None,
        description="Day of month for monthly patterns (1-31)"
    )
    month: Optional[str] = Field(
        default=None,
        description="Month for yearly patterns (January, February, etc.)"
    )
    time: str = Field(
        description="Time of day in format 'HH:MM AM/PM'"
    )
    end_date: Optional[str] = Field(
        default=None,
        description="Optional end date for the recurrence (YYYY-MM-DD)"
    )

def parse_time_slot(time_slot: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse a time slot string to extract date and time.
    
    Args:
        time_slot: String containing date and time information
        
    Returns:
        Tuple of (date_str, time_str) where:
            - date_str is in YYYY-MM-DD format or None if not found
            - time_str is in HH:MM AM/PM format or None if not found
    """
    if not time_slot or time_slot == "Yes" or time_slot == "N/A":
        logger.info(f"Invalid time slot value: {time_slot}")
        return None, None
    
    scheduled_date = None
    scheduled_time = None
    
    try:
        # Look for date patterns like YYYY-MM-DD or Month DD, YYYY
        date_pattern = r'(\d{4}-\d{2}-\d{2})|([A-Za-z]+\s+\d{1,2},?\s+\d{4})'
        date_match = re.search(date_pattern, time_slot)
        
        # Look for time patterns like HH:MM AM/PM or H AM/PM to H AM/PM
        time_pattern = r'(\d{1,2}:\d{2}\s*[AP]M)|(\d{1,2}\s*[AP]M)'
        time_match = re.findall(time_pattern, time_slot)
        
        # Process date if found
        if date_match:
            date_str = date_match.group(0)
            # Convert to YYYY-MM-DD format if it's in Month DD, YYYY format
            if not re.match(r'\d{4}-\d{2}-\d{2}', date_str):
                try:
                    # Handle formats like "May 29, 2025"
                    from dateutil import parser
                    parsed_date = parser.parse(date_str)
                    scheduled_date = parsed_date.strftime("%Y-%m-%d")
                    logger.info(f"Parsed date: {scheduled_date}")
                except Exception as parse_error:
                    logger.error(f"Error parsing date: {parse_error}")
                    scheduled_date = None
            else:
                scheduled_date = date_str
        else:
            logger.warning(f"No date pattern found in time slot: {time_slot}")
        
        # Process time if found
        if time_match and len(time_match) > 0:
            # Take the first time if it's a range
            time_str = time_match[0][0] or time_match[0][1]
            logger.info(f"Extracted time string: {time_str}")
            # Convert to standard format HH:MM AM/PM
            if ":" not in time_str:
                # Convert "10 AM" to "10:00 AM"
                time_parts = time_str.strip().split()
                if len(time_parts) == 2:
                    hour = time_parts[0]
                    ampm = time_parts[1]
                    scheduled_time = f"{hour}:00 {ampm}"
            else:
                scheduled_time = time_str.strip()
            logger.info(f"Formatted time: {scheduled_time}")
        else:
            logger.warning(f"No time pattern found in time slot: {time_slot}")
            # Try to extract time from phrases like "from 12 PM to 2 PM"
            from_time_pattern = r'from\s+(\d{1,2})\s*([AP]M)'
            from_time_match = re.search(from_time_pattern, time_slot)
            if from_time_match:
                hour = from_time_match.group(1)
                ampm = from_time_match.group(2)
                scheduled_time = f"{hour}:00 {ampm}"
                logger.info(f"Extracted time from 'from X to Y' pattern: {scheduled_time}")
    
    except Exception as e:
        logger.error(f"Error parsing time slot: {e}")
        scheduled_date = None
        scheduled_time = None
    
    return scheduled_date, scheduled_time

def extract_time_slot_from_responses(responses: dict) -> Optional[str]:
    """
    Extract time slot information from responses dictionary.
    
    Args:
        responses: Dictionary of responses from the applicant
        
    Returns:
        Time slot string if found, None otherwise
    """
    if not responses or not isinstance(responses, dict):
        return None
    
    # First check for explicit selected_time_slot key
    if "selected_time_slot" in responses and isinstance(responses["selected_time_slot"], str) and responses["selected_time_slot"] != "Yes" and responses["selected_time_slot"] != "N/A":
        selected_time_slot = responses["selected_time_slot"]
        logger.info(f"Found explicit selected_time_slot in responses: {selected_time_slot}")
        return selected_time_slot
    
    # Look for keys that might contain time slot information
    for key, value in responses.items():
        if isinstance(value, str) and any(term in key.lower() for term in ["time", "slot", "schedule", "interview", "appointment"]) and value != "Yes" and value != "N/A":
            # Found a potential time slot
            selected_time_slot = value
            logger.info(f"Found selected time slot in responses: {selected_time_slot}")
            return selected_time_slot
    
    # Also look for time slot information in the values regardless of key names
    for key, value in responses.items():
        if isinstance(value, str) and ("AM" in value.upper() or "PM" in value.upper()) and any(term in value.lower() for term in ["time", "slot", "schedule", "interview", "appointment", "available"]):
            selected_time_slot = value
            logger.info(f"Found time slot in response value: {selected_time_slot}")
            return selected_time_slot
    
    return None

def format_company_time_slot(time_slot_text: str) -> Optional[str]:
    """
    Format a company time slot with tomorrow's date.
    
    Args:
        time_slot_text: Company time slot text (e.g., "Monday 9-11 AM")
        
    Returns:
        Formatted time slot with date and time or None if invalid
    """
    if not time_slot_text or not time_slot_text.strip():
        return None
    
    try:
        # Check if the time slot already has a date (e.g., "May 10, 2025 Monday 9-11 AM")
        if re.search(r'\b[A-Za-z]+\s+\d{1,2},\s+\d{4}\b', time_slot_text):
            # Already has a date, return as is
            return time_slot_text
            
        # Check if it's a recurring time slot (starts with a day name)
        day_pattern = r'^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b'
        day_match = re.search(day_pattern, time_slot_text, re.IGNORECASE)
        
        if day_match:
            # It's a recurring time slot, extract the day name and time
            day_name = day_match.group(1)
            # Extract time part (everything after the day name)
            time_parts = time_slot_text.split(maxsplit=1)
            if len(time_parts) > 1:
                time_str = time_parts[1].strip()
                # Use the date_utils function to format with the next occurrence date
                return format_next_day_with_time_slot(day_name, time_str)
        
        # If we get here, it's not a recognized format, use tomorrow's date as fallback
        today = datetime.datetime.now()
        tomorrow = today + datetime.timedelta(days=1)
        date_str = tomorrow.strftime("%B %d, %Y")
        return f"{date_str} {time_slot_text}"
    
    except Exception as e:
        logger.error(f"Error formatting company time slot: {e}")
        return None


def parse_recurrence_pattern(recurrence_text: str) -> Optional[RecurrenceTimeSlot]:
    """
    Parse a text description of a recurrence pattern into a structured RecurrenceTimeSlot.
    
    Args:
        recurrence_text: Text description of recurrence (e.g., "First Monday of every month at 1 PM")
        
    Returns:
        RecurrenceTimeSlot object or None if parsing fails
    """
    try:
        # Parse weekly patterns (e.g., "Every Monday at 9 AM")
        weekly_pattern = re.match(r'(?:Every\s+)?(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+at\s+(\d{1,2}(?::\d{2})?\s*[AP]M)', recurrence_text, re.IGNORECASE)
        if weekly_pattern:
            day_of_week = weekly_pattern.group(1)
            time = weekly_pattern.group(2)
            return RecurrenceTimeSlot(
                pattern_type="weekly",
                day_of_week=day_of_week,
                time=time
            )
        
        # Parse monthly patterns with multiple week positions (e.g., "First and third Monday of every month at 1 PM")
        multiple_week_pattern = re.match(r'((?:First|Second|Third|Fourth|Last)(?:\s+and\s+(?:First|Second|Third|Fourth|Last))*)\s+(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+of\s+every\s+month\s+at\s+(\d{1,2}(?::\d{2})?\s*[AP]M)', recurrence_text, re.IGNORECASE)
        if multiple_week_pattern:
            week_positions_text = multiple_week_pattern.group(1).lower()
            day_of_week = multiple_week_pattern.group(2)
            time = multiple_week_pattern.group(3)
            
            # Extract individual week positions
            week_positions = [pos.strip() for pos in re.split(r'\s+and\s+', week_positions_text)]
            
            return RecurrenceTimeSlot(
                pattern_type="monthly",
                week_of_month=week_positions if len(week_positions) > 1 else week_positions[0],
                day_of_week=day_of_week,
                time=time
            )
        
        # Parse monthly patterns with single week position (e.g., "First Monday of every month at 1 PM")
        monthly_week_pattern = re.match(r'(First|Second|Third|Fourth|Last)\s+(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+of\s+every\s+month\s+at\s+(\d{1,2}(?::\d{2})?\s*[AP]M)', recurrence_text, re.IGNORECASE)
        if monthly_week_pattern:
            week_position = monthly_week_pattern.group(1)
            day_of_week = monthly_week_pattern.group(2)
            time = monthly_week_pattern.group(3)
            return RecurrenceTimeSlot(
                pattern_type="monthly",
                week_of_month=week_position.lower(),
                day_of_week=day_of_week,
                time=time
            )
        
        # Parse monthly patterns with specific day (e.g., "15th of every month at 2 PM")
        monthly_day_pattern = re.match(r'(\d{1,2})(?:st|nd|rd|th)?\s+of\s+every\s+month\s+at\s+(\d{1,2}(?::\d{2})?\s*[AP]M)', recurrence_text, re.IGNORECASE)
        if monthly_day_pattern:
            day_of_month = int(monthly_day_pattern.group(1))
            time = monthly_day_pattern.group(2)
            return RecurrenceTimeSlot(
                pattern_type="monthly",
                day_of_month=day_of_month,
                time=time
            )
        
        # Parse yearly patterns (e.g., "January 15 every year at 3 PM")
        yearly_pattern = re.match(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})(?:st|nd|rd|th)?\s+(?:every\s+year\s+)?at\s+(\d{1,2}(?::\d{2})?\s*[AP]M)', recurrence_text, re.IGNORECASE)
        if yearly_pattern:
            month = yearly_pattern.group(1)
            day_of_month = int(yearly_pattern.group(2))
            time = yearly_pattern.group(3)
            return RecurrenceTimeSlot(
                pattern_type="yearly",
                month=month,
                day_of_month=day_of_month,
                time=time
            )
        
        # Parse daily patterns (e.g., "Every day at 9 AM")
        daily_pattern = re.match(r'Every\s+day\s+at\s+(\d{1,2}(?::\d{2})?\s*[AP]M)', recurrence_text, re.IGNORECASE)
        if daily_pattern:
            time = daily_pattern.group(1)
            return RecurrenceTimeSlot(
                pattern_type="daily",
                time=time
            )
        
        return None
    except Exception as e:
        logger.error(f"Error parsing recurrence pattern: {e}")
        return None


def calculate_week_position_date(from_date, week_position, day_of_week, hour, minute):
    """
    Calculate the date for patterns like "First Monday of the month"
    """
    # Convert day name to weekday number (0=Monday, 6=Sunday)
    day_index = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"].index(day_of_week.lower())
    
    # Start with the first day of the current month
    current_month = from_date.replace(day=1, hour=hour, minute=minute, second=0, microsecond=0)
    
    # If we've already passed this month's occurrence, move to next month
    if week_position.lower() != "last":
        # For "first", "second", etc.
        week_num = ["first", "second", "third", "fourth"].index(week_position.lower())
        
        # Find the first occurrence of the day in the month
        days_ahead = (day_index - current_month.weekday()) % 7
        first_occurrence = current_month + datetime.timedelta(days=days_ahead)
        
        # Add weeks as needed
        target_date = first_occurrence + datetime.timedelta(weeks=week_num)
        
        # If target date is in the next month, go back to the last occurrence in the current month
        if target_date.month != current_month.month:
            target_date = target_date - datetime.timedelta(weeks=1)
            
        # If we've already passed this month's occurrence, move to next month
        if target_date <= from_date:
            # Move to first day of next month
            if current_month.month == 12:
                next_month = current_month.replace(year=current_month.year + 1, month=1)
            else:
                next_month = current_month.replace(month=current_month.month + 1)
                
            # Recalculate for next month
            days_ahead = (day_index - next_month.weekday()) % 7
            first_occurrence = next_month + datetime.timedelta(days=days_ahead)
            target_date = first_occurrence + datetime.timedelta(weeks=week_num)
            
            # If target date is in the month after next, go back to the last occurrence in next month
            if target_date.month != next_month.month:
                target_date = target_date - datetime.timedelta(weeks=1)
    else:
        # For "last" day of the month
        # Get the first day of the next month
        if current_month.month == 12:
            next_month = current_month.replace(year=current_month.year + 1, month=1)
        else:
            next_month = current_month.replace(month=current_month.month + 1)
            
        # Go back one day to get the last day of the current month
        last_day = next_month - datetime.timedelta(days=1)
        
        # Find the last occurrence of the day in the month by working backwards
        days_back = (last_day.weekday() - day_index) % 7
        target_date = last_day - datetime.timedelta(days=days_back)
        
        # If we've already passed this month's occurrence, move to next month
        if target_date <= from_date:
            # Get the first day of the month after next
            if next_month.month == 12:
                month_after_next = next_month.replace(year=next_month.year + 1, month=1)
            else:
                month_after_next = next_month.replace(month=next_month.month + 1)
                
            # Go back one day to get the last day of the next month
            last_day = month_after_next - datetime.timedelta(days=1)
            
            # Find the last occurrence of the day in the next month
            days_back = (last_day.weekday() - day_index) % 7
            target_date = last_day - datetime.timedelta(days=days_back)
    
    return target_date


def get_next_occurrence(recurrence_slot: RecurrenceTimeSlot, from_date: Optional[datetime.datetime] = None) -> Optional[datetime.datetime]:
    """
    Calculate the next occurrence of a recurring time slot.
    
    Args:
        recurrence_slot: The recurrence pattern
        from_date: Optional date to calculate from (defaults to now)
        
    Returns:
        datetime object for the next occurrence or None if calculation fails
    """
    if not from_date:
        from_date = datetime.datetime.now()
    
    try:
        # Parse the time
        time_parts = re.match(r'(\d{1,2})(?::(\d{2}))?\s*([AP]M)', recurrence_slot.time, re.IGNORECASE)
        if not time_parts:
            return None
        
        hour = int(time_parts.group(1))
        minute = int(time_parts.group(2) or 0)
        ampm = time_parts.group(3).upper()
        
        # Convert to 24-hour format
        if ampm == 'PM' and hour < 12:
            hour += 12
        elif ampm == 'AM' and hour == 12:
            hour = 0
        
        # Handle different pattern types
        if recurrence_slot.pattern_type == "daily":
            # For daily patterns, just set the time for today or tomorrow
            result = from_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if result <= from_date:
                result += datetime.timedelta(days=1)
            return result
            
        elif recurrence_slot.pattern_type == "weekly" and recurrence_slot.day_of_week:
            # For weekly patterns, find the next occurrence of the day of week
            day_index = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"].index(recurrence_slot.day_of_week.lower())
            days_ahead = day_index - from_date.weekday()
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
            
            next_date = from_date + datetime.timedelta(days=days_ahead)
            return next_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
        elif recurrence_slot.pattern_type == "monthly":
            # For monthly patterns, handle both day-of-month and week-position formats
            if recurrence_slot.day_of_month:
                # Simple day of month (e.g., 15th of every month)
                next_date = from_date.replace(day=min(recurrence_slot.day_of_month, calendar.monthrange(from_date.year, from_date.month)[1]), 
                                             hour=hour, minute=minute, second=0, microsecond=0)
                if next_date <= from_date:
                    # Move to next month
                    if from_date.month == 12:
                        next_date = next_date.replace(year=from_date.year + 1, month=1)
                    else:
                        next_date = next_date.replace(month=from_date.month + 1)
                    # Adjust for month length
                    next_date = next_date.replace(day=min(recurrence_slot.day_of_month, calendar.monthrange(next_date.year, next_date.month)[1]))
                return next_date
                
            elif recurrence_slot.week_of_month and recurrence_slot.day_of_week:
                # Handle multiple week positions (e.g., First and third Monday of every month)
                if isinstance(recurrence_slot.week_of_month, list):
                    # Find the next occurrence for each week position
                    next_dates = []
                    for week_pos in recurrence_slot.week_of_month:
                        next_date = calculate_week_position_date(from_date, week_pos, recurrence_slot.day_of_week, hour, minute)
                        if next_date:
                            next_dates.append(next_date)
                    
                    # Return the earliest future date
                    if next_dates:
                        return min([d for d in next_dates if d > from_date]) if any(d > from_date for d in next_dates) else min(next_dates)
                    return None
                else:
                    # Single week position (e.g., First Monday of every month)
                    return calculate_week_position_date(from_date, recurrence_slot.week_of_month, recurrence_slot.day_of_week, hour, minute)
        
        elif recurrence_slot.pattern_type == "yearly" and recurrence_slot.month and recurrence_slot.day_of_month:
            # For yearly patterns (e.g., January 15 every year)
            month_index = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"].index(recurrence_slot.month.lower()) + 1
            
            next_date = datetime.datetime(from_date.year, month_index, min(recurrence_slot.day_of_month, calendar.monthrange(from_date.year, month_index)[1]), 
                                         hour, minute, 0, 0)
            
            if next_date <= from_date:
                # Move to next year
                next_date = datetime.datetime(from_date.year + 1, month_index, min(recurrence_slot.day_of_month, calendar.monthrange(from_date.year + 1, month_index)[1]), 
                                             hour, minute, 0, 0)
            return next_date
        
        return None
    except Exception as e:
        logger.error(f"Error calculating next occurrence: {e}")
        return None


def generate_time_slots_from_recurrence(recurrence_slots: List[RecurrenceTimeSlot], num_occurrences: int = 4) -> List[str]:
    """
    Generate a list of concrete time slots for the next N occurrences of each recurrence pattern.
    
    Args:
        recurrence_slots: List of recurrence patterns
        num_occurrences: Number of occurrences to generate for each pattern
        
    Returns:
        List of formatted time slots with dates
    """
    if not recurrence_slots:
        return []
    
    generated_slots = []
    now = datetime.datetime.now()
    
    for recurrence in recurrence_slots:
        current_date = now
        for _ in range(num_occurrences):
            next_date = get_next_occurrence(recurrence, current_date)
            if next_date:
                # Format as "Month Day, Year at Time"
                formatted_date = next_date.strftime("%B %d, %Y at %I:%M %p")
                generated_slots.append(formatted_date)
                # Move past this occurrence for the next iteration
                current_date = next_date + datetime.timedelta(minutes=1)
    
    return sorted(generated_slots, key=lambda x: datetime.datetime.strptime(x, "%B %d, %Y at %I:%M %p"))


def format_recurrence_time_slots(recurrence_time_slots: List[str]) -> List[str]:
    """
    Format a list of recurrence time slots with their next occurrence dates.
    
    Args:
        recurrence_time_slots: List of recurring time slots (e.g., ["Monday 9 AM - 5 PM"])
        
    Returns:
        List of formatted time slots with dates
    """
    if not recurrence_time_slots:
        return []
    
    formatted_slots = []
    
    for slot in recurrence_time_slots:
        # Try to parse as structured recurrence pattern first
        recurrence_slot = parse_recurrence_pattern(slot)
        if recurrence_slot:
            # Generate the next few occurrences
            occurrences = generate_time_slots_from_recurrence([recurrence_slot], num_occurrences=2)
            formatted_slots.extend(occurrences)
        else:
            # Fall back to legacy format
            formatted_slot = format_company_time_slot(slot)
            if formatted_slot:
                formatted_slots.append(formatted_slot)
    
    return formatted_slots
