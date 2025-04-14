from __future__ import annotations
from datetime import datetime, timedelta
from dateutil import parser, tz
from typing import Any, List, Dict, Optional, Type, TYPE_CHECKING
import uuid

from langchain.callbacks.manager import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain_community.tools.gmail.utils import (
    build_resource_service,
    get_gmail_credentials,
)
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool, tool

if TYPE_CHECKING:
    # This is for linting and IDE typehints
    from googleapiclient.discovery import Resource
else:
    try:
        # We do this so pydantic can resolve the types when instantiating
        from googleapiclient.discovery import Resource
    except ImportError:
        pass


class TimeZoneInput(BaseModel):
    timezone: str = Field(
        description="The timezone in TZ Database Name format, e.g. 'America/New_York'"
    )


@tool("get_current_time", args_schema=TimeZoneInput)
def get_current_time(timezone: str) -> str:
    """Look up the current time based on timezone, returns %Y-%m-%d %H:%M:%S format"""

    user_timezone = tz.gettz(timezone)
    # cannot use tz.tzlocal() on server
    now = datetime.now(tz=user_timezone)
    return now.strftime("%Y-%m-%d %H:%M:%S")


class GoogleCalendarBaseTool(BaseTool):
    """Base class for Google Calendar tools."""

    api_resource: Resource = Field(default_factory=build_resource_service)

    @classmethod
    def from_api_resource(cls, api_resource: Resource) -> "GoogleCalendarBaseTool":
        """Create a tool from an api resource.

        Args:
            api_resource: The api resource to use.

        Returns:
            A tool.
        """
        return cls(api_resource=api_resource)


# List events tool
class GetEventsSchema(BaseModel):
    # https://developers.google.com/calendar/api/v3/reference/events/list
    start_datetime: str = Field(
        # default=datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
        description=(
            " The start datetime for the event in the following format: "
            ' YYYY-MM-DDTHH:MM:SS, where "T" separates the date and time '
            " components, "
            ' For example: "2023-06-09T10:30:00" represents June 9th, '
            " 2023, at 10:30 AM"
            "Do not include timezone info as it will be automatically processed."
        )
    )
    end_datetime: str = Field(
        # default=(datetime.now() + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S"),
        description=(
            " The end datetime for the event in the following format: "
            ' YYYY-MM-DDTHH:MM:SS, where "T" separates the date and time '
            " components, "
            ' For example: "2023-06-09T10:30:00" represents June 9th, '
            " 2023, at 10:30 AM"
            "Do not include timezone info as it will be automatically processed."
        ),
    )
    max_results: int = Field(
        default=10,
        description="The maximum number of results to return.",
    )
    timezone: str = Field(
        default="America/Chicago",
        description="The timezone in TZ Database Name format, e.g. 'America/New_York'",
    )


class ListGoogleCalendarEvents(GoogleCalendarBaseTool):
    name: str = "list_google_calendar_events"
    description: str = (
        " Use this tool to search for the user's calendar events."
        " The input must be the start and end datetimes for the search query."
        " Start time is default to the current time. You can also specify the"
        " maximum number of results to return. The output is a JSON list of "
        " all the events in the user's calendar between the start and end times."
    )
    args_schema: Type[BaseModel] = GetEventsSchema

    def _parse_event(self, event, timezone):
        # convert to local timezone
        start = event["start"].get("dateTime", event["start"].get("date"))
        start = (
            parser.parse(start)
            .astimezone(tz.gettz(timezone))
            .strftime("%Y/%m/%d %H:%M:%S")
        )
        end = event["end"].get("dateTime", event["end"].get("date"))
        end = (
            parser.parse(end)
            .astimezone(tz.gettz(timezone))
            .strftime("%Y/%m/%d %H:%M:%S")
        )
        event_parsed = dict(start=start, end=end)
        for field in [
            "summary",
            "description",
            "location",
            "hangoutLink",
        ]:  # optional: attendees
            event_parsed[field] = event.get(field, None)
        return event_parsed

    def _get_calendars(self):
        calendars = []
        for cal in self.api_resource.calendarList().list().execute().get("items", []):
            if cal.get(
                "selected", None
            ):  # select relevant calendars in google calendar UI
                calendars.append(cal["id"])
        return calendars

    def _run(
        self,
        start_datetime: str,
        end_datetime: str,
        max_results: int = 10,  # max results per calendar
        timezone: str = "Asia/Kolkata",
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> List[Dict[str, Any]]:

        calendars = self._get_calendars()

        events = []
        start = datetime.strptime(start_datetime, "%Y-%m-%dT%H:%M:%S")
        start = start.replace(tzinfo=tz.gettz(timezone)).isoformat()
        end = datetime.strptime(end_datetime, "%Y-%m-%dT%H:%M:%S")
        end = end.replace(tzinfo=tz.gettz(timezone)).isoformat()
        for cal in calendars:
            events_result = (
                self.api_resource.events()
                .list(
                    calendarId=cal,
                    timeMin=start,
                    timeMax=end,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            cal_events = events_result.get("items", [])
            events.extend(cal_events)

        events = sorted(
            events, key=lambda x: x["start"].get("dateTime", x["start"].get("date"))
        )

        return [self._parse_event(e, timezone) for e in events]

    async def _arun(
        self,
        start_datetime: str,
        end_datetime: str,
        max_results: int = 10,  # max results per calendar
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> List[Dict[str, Any]]:

        raise NotImplementedError("Async version of this tool is not implemented.")


# Create event tool
class CreateEventSchema(BaseModel):
    # https://developers.google.com/calendar/api/v3/reference/events/insert

    # note: modifed the tz desc in the parameters, use local time automatically
    start_datetime: str = Field(
        description=(
            " The start datetime for the event in the following format: "
            ' YYYY-MM-DDTHH:MM:SS, where "T" separates the date and time '
            " components, "
            ' For example: "2023-06-09T10:30:00" represents June 9th, '
            " 2023, at 10:30 AM"
            "Do not include timezone info as it will be automatically processed."
        )
    )
    end_datetime: str = Field(
        description=(
            " The end datetime for the event in the following format: "
            ' YYYY-MM-DDTHH:MM:SS, where "T" separates the date and time '
            " components, "
            ' For example: "2023-06-09T10:30:00" represents June 9th, '
            " 2023, at 10:30 AM"
            "Do not include timezone info as it will be automatically processed."
        )
    )
    summary: str = Field(description="The title of the event.")
    location: Optional[str] = Field(
        default="", description="The location of the event."
    )
    description: Optional[str] = Field(
        default="", description="The description of the event. Optional."
    )
    timezone: str = Field(
        default="America/Chicago",
        description="The timezone in TZ Database Name format, e.g. 'America/New_York'",
    )
    guests: Optional[List[str]] = None
    add_google_meet: Optional[bool] = Field(
        default=True,
        description="Whether to add a Google Meet video conference to the event.",
    )


class CreateGoogleCalendarEvent(GoogleCalendarBaseTool):
    name: str = "create_google_calendar_event"
    description: str = (
        " Use this tool to create a new calendar event in user's primary calendar."
        " The input must be the start and end datetime for the event, and"
        " the title of the event. You can also specify the location, description, guests,"
        " and whether to add a Google Meet video conference link."
    )
    args_schema: Type[BaseModel] = CreateEventSchema

    def _run(
        self,
        start_datetime: str,
        end_datetime: str,
        summary: str,
        location: str = "",
        description: str = "",
        guests: list[str] = None,
        timezone: str = "Asia/Kolkata",
        add_google_meet: bool = True,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:

        # Convert to RFC3339 timestamp
        start = datetime.strptime(start_datetime, "%Y-%m-%dT%H:%M:%S")
        start = start.replace(tzinfo=tz.gettz(timezone)).isoformat()
        end = datetime.strptime(end_datetime, "%Y-%m-%dT%H:%M:%S")
        end = end.replace(tzinfo=tz.gettz(timezone)).isoformat()

        event = {
            "summary": summary,
            "location": location,
            "description": description,
            "start": {"dateTime": start},
            "end": {"dateTime": end},
        }

        if guests:
            event["attendees"] = [{"email": email} for email in guests]

        # Add Google Meet video conference if requested
        if add_google_meet:
            event["conferenceData"] = {
                "createRequest": {
                    "requestId": f"meet-{uuid.uuid4().hex}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            }

        # Create the event
        event = (
            self.api_resource.events()
            .insert(
                calendarId="primary",
                body=event,
                conferenceDataVersion=1 if add_google_meet else 0,
                sendUpdates="all" if guests else "none",
            )
            .execute()
        )

        # Format the response
        response = {
            "event_id": event.get("id"),
            "summary": event.get("summary"),
            "start": event.get("start", {}).get("dateTime"),
            "end": event.get("end", {}).get("dateTime"),
            "location": event.get("location"),
            "description": event.get("description"),
            "event_link": event.get("htmlLink"),
        }

        # Add meet link if available
        if add_google_meet and "conferenceData" in event:
            response["meet_link"] = (
                event.get("conferenceData", {})
                .get("entryPoints", [{}])[0]
                .get("uri", "")
            )

        return response

    async def _arun(
        self,
        start_datetime: str,
        end_datetime: str,
        summary: str,
        location: str = "",
        description: str = "",
        guests: list[str] = None,
        add_google_meet: bool = True,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:

        raise NotImplementedError("Async version of this tool is not implemented.")


if __name__ == "__main__":

    credentials = get_gmail_credentials(
        token_file="../token.json",
        scopes=["https://www.googleapis.com/auth/calendar"],
        client_secrets_file="credentials.json",
    )

    calendar_service = build_resource_service(
        credentials=credentials, service_name="calendar", service_version="v3"
    )

    geteventstool = ListGoogleCalendarEvents.from_api_resource(calendar_service)
    print(geteventstool.args)

    start = "2024-02-01T10:30:00"
    end = "2024-06-09T10:30:00"
    tool_res = geteventstool.run(
        tool_input={"start_datetime": start, "end_datetime": end, "max_results": 10}
    )
    for e in tool_res:
        print("Start: ", e["start"], "End: ", e["end"], "Summary:", e["summary"])
    print(tool_res)

    createeventtool = CreateGoogleCalendarEvent.from_api_resource(calendar_service)
    tool_res = createeventtool.run(
        guests=[""],
        tool_input={
            "start_datetime": "2024-08-21T10:30:00",
            "end_datetime": "2024-08-21T11:30:00",
            "summary": "Test event",
            "guests": ["@gmail.com"],
        },
    )
    print(tool_res)
