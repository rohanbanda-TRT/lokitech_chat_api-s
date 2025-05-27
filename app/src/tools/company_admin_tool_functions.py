import json
import logging
from typing import Dict, Any

from ..models.company_admin_model import (
    CreateQuestionsInput,
    GetQuestionsInput,
    UpdateQuestionToolInput,
    DeleteQuestionToolInput,
    UpdateTimeSlotsToolInput,
    UpdateStructuredRecurrenceToolInput,
    UpdateContactInfoToolInput,
    DeleteRecurrenceTimeSlotsToolInput,
)
from .company_admin_tools import CompanyAdminTools
logger = logging.getLogger(__name__)

class CompanyAdminToolFunctions:
    def __init__(self):
        self.admin_tools = CompanyAdminTools()

    def create_questions_tool(self, data: CreateQuestionsInput) -> str:
        """Create or update company questions, time slots, and contact info"""
        input_data = {
            "dsp_code": data.dsp_code,
            "append": data.append
        }
        
        if data.questions is not None:
            input_data["questions"] = data.questions
        if data.time_slots is not None:
            input_data["time_slots"] = data.time_slots
        if data.contact_info is not None:
            if not all(key in data.contact_info for key in ["contact_person_name", "contact_number", "email_id"]):
                return "Error: Contact info must include contact_person_name, contact_number, and email_id fields"
            input_data["contact_info"] = data.contact_info
            
        return self.admin_tools.create_questions(json.dumps(input_data))

    def get_questions_tool(self, data: GetQuestionsInput) -> str:
        """Get company questions, time slots, and contact info"""
        return self.admin_tools.get_questions(data.dsp_code)

    # ...existing tool methods...
    # Copy all other tool methods here (update_question_to
    def update_question_tool(self,data: UpdateQuestionToolInput) -> str:
        """Update a specific question"""
        return self.admin_tools.update_question(json.dumps(data.model_dump()))
        
    def delete_question_tool(self,data: DeleteQuestionToolInput) -> str:
        """Delete a specific question"""
        return self.admin_tools.delete_question(json.dumps(data.model_dump()))
        
    def update_time_slots_tool(self,data: UpdateTimeSlotsToolInput) -> str:
        """Update time slots"""
        return self.admin_tools.update_time_slots(json.dumps(data.model_dump()))
        
    def update_structured_recurrence_tool(self,data: UpdateStructuredRecurrenceToolInput) -> str:
        """Update structured recurrence patterns"""
        # Prepare the data to send to the admin tools
        payload = {
            "dsp_code": data.dsp_code
        }
        
        # Use structured_recurrence_patterns if provided
        if data.structured_recurrence_patterns is not None:
            payload["structured_recurrence_patterns"] = data.structured_recurrence_patterns
        # Fall back to recurrence_patterns if structured_recurrence_patterns is not provided
        elif data.recurrence_patterns is not None:
            payload["recurrence_patterns"] = data.recurrence_patterns
            
        return self.admin_tools.update_time_slots(json.dumps(payload))
        
    def update_contact_info_tool(self,data: UpdateContactInfoToolInput) -> str:
        """Update contact info"""
        # Ensure contact_info has all required fields
        if not all(key in data.contact_info for key in ["contact_person_name", "contact_number", "email_id"]):
            return "Error: Contact info must include contact_person_name, contact_number, and email_id fields"
            
        # Convert to dict for the tool
        input_data = {
            "dsp_code": data.dsp_code,
            "contact_info": data.contact_info
        }
        return self.admin_tools.update_contact_info(json.dumps(input_data))

    def delete_recurrence_time_slots_tool(self,data: DeleteRecurrenceTimeSlotsToolInput) -> str:
        """Delete all recurring time slots for a company"""
        try:
            # Convert the data to a JSON string
            input_str = json.dumps({
                "dsp_code": data.dsp_code,
            })
            # Call the tool
            return self.admin_tools.delete_recurrence_time_slots(input_str)
        except Exception as e:
            logger.error(f"Error in delete_recurrence_time_slots_tool: {e}")
            return f"Error: {str(e)}"