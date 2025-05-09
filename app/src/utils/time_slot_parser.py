"""
Utility functions for parsing and formatting time slots.
"""

import re
import logging
import datetime
from typing import Optional, Tuple, List, Dict, Any
from .date_utils import format_next_day_with_time_slot, get_next_day_date

# Configure logging
logger = logging.getLogger(__name__)

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
        formatted_slot = format_company_time_slot(slot)
        if formatted_slot:
            formatted_slots.append(formatted_slot)
    
    return formatted_slots
