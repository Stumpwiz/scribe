"""
Calendar integration tool for the Scribe project.

This module provides the CalendarIntegration class for managing calendar events and tracking deadlines.
"""

from typing import List, Optional
from datetime import datetime, timedelta
from crewai.tools import BaseTool


class CalendarIntegration(BaseTool):
    """
    Tool for managing calendar events and tracking deadlines.
    
    This tool allows agents to schedule meetings, track meeting schedules,
    set reminders for deadlines, and check for scheduling conflicts.
    """
    
    name: str = "Calendar Integration"
    description: str = "Tool for managing calendar events and tracking deadlines"
    
    def _run(self, 
             action: str = "schedule", 
             event_title: Optional[str] = None,
             event_date: Optional[str] = None,
             event_time: Optional[str] = None,
             duration_minutes: int = 60,
             attendees: Optional[List[str]] = None,
             location: Optional[str] = None,
             description: Optional[str] = None,
             **kwargs) -> str:
        """
        Run the calendar integration.
        
        Args:
            action (str): The action to perform ("schedule", "check", "list", "remind", "cancel")
            event_title (Optional[str]): Title of the event
            event_date (Optional[str]): Date of the event (YYYY-MM-DD)
            event_time (Optional[str]): Time of the event (HH:MM)
            duration_minutes (int): Duration of the event in minutes
            attendees (Optional[List[str]]): List of attendee email addresses
            location (Optional[str]): Location of the event
            description (Optional[str]): Description of the event
            
        Returns:
            str: Result of the calendar operation
        """
        if action == "schedule":
            return self._schedule_event(event_title, event_date, event_time, duration_minutes, attendees, location, description)
        elif action == "check":
            date = kwargs.get("date", event_date)
            return self._check_availability(date)
        elif action == "list":
            start_date = kwargs.get("start_date", event_date)
            end_date = kwargs.get("end_date", None)
            return self._list_events(start_date, end_date)
        elif action == "remind":
            deadline = kwargs.get("deadline", event_date)
            reminder_days = kwargs.get("reminder_days", 1)
            return self._set_reminder(event_title, deadline, reminder_days)
        elif action == "cancel":
            return self._cancel_event(event_title, event_date)
        else:
            return f"Unknown action: {action}"
    
    @staticmethod
    def _schedule_event(self, 
                       event_title: Optional[str],
                       event_date: Optional[str],
                       event_time: Optional[str],
                       duration_minutes: int,
                       attendees: Optional[List[str]],
                       location: Optional[str],
                       description: Optional[str]) -> str:
        """
        Schedule a new event on the calendar.
        
        Args:
            event_title (Optional[str]): Title of the event
            event_date (Optional[str]): Date of the event (YYYY-MM-DD)
            event_time (Optional[str]): Time of the event (HH:MM)
            duration_minutes (int): Duration of the event in minutes
            attendees (Optional[List[str]]): List of attendee email addresses
            location (Optional[str]): Location of the event
            description (Optional[str]): Description of the event
            
        Returns:
            str: Result of the scheduling operation
        """
        # In a real implementation, this would connect to a calendar service
        # For now, we'll just return a placeholder message
        attendee_count = len(attendees) if attendees else 0
        end_time = "calculated end time would go here"
        
        return (f"Event scheduled: {event_title}\n"
                f"Date: {event_date}\n"
                f"Time: {event_time} - {end_time}\n"
                f"Location: {location}\n"
                f"Attendees: {attendee_count}\n"
                f"Calendar invitations sent to all attendees.")
    
    @staticmethod
    def _check_availability(self, date: Optional[str]) -> str:
        """
        Check availability for a specific date.
        
        Args:
            date (Optional[str]): Date to check (YYYY-MM-DD)
            
        Returns:
            str: Availability information
        """
        # In a real implementation, this would check a calendar service
        # For now, we'll just return a placeholder message
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
            
        return f"Availability for {date}: No events scheduled. The entire day is available."
    
    @staticmethod
    def _list_events(self, 
                    start_date: Optional[str],
                    end_date: Optional[str]) -> str:
        """
        List events between the specified dates.
        
        Args:
            start_date (Optional[str]): Start date (YYYY-MM-DD)
            end_date (Optional[str]): End date (YYYY-MM-DD)
            
        Returns:
            str: List of events
        """
        # In a real implementation, this would query a calendar service
        # For now, we'll just return a placeholder message
        if not start_date:
            start_date = datetime.now().strftime("%Y-%m-%d")
            
        if not end_date:
            # Default to one week from start date
            end_date_obj = datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=7)
            end_date = end_date_obj.strftime("%Y-%m-%d")
            
        return f"Events from {start_date} to {end_date}: No events found."
    
    @staticmethod
    def _set_reminder(self, 
                     event_title: Optional[str],
                     deadline: Optional[str],
                     reminder_days: int) -> str:
        """
        Set a reminder for a deadline.
        
        Args:
            event_title (Optional[str]): Title of the event or deadline
            deadline (Optional[str]): Deadline date (YYYY-MM-DD)
            reminder_days (int): Days before deadline to send reminder
            
        Returns:
            str: Result of the reminder operation
        """
        # In a real implementation, this would set up a reminder in a calendar service
        # For now, we'll just return a placeholder message
        if not deadline:
            deadline = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
            
        reminder_date = (datetime.strptime(deadline, "%Y-%m-%d") - timedelta(days=reminder_days)).strftime("%Y-%m-%d")
            
        return f"Reminder set for '{event_title}'. Reminder will be sent on {reminder_date}, {reminder_days} days before the deadline ({deadline})."
    
    @staticmethod
    def _cancel_event(self, 
                     event_title: Optional[str],
                     event_date: Optional[str]) -> str:
        """
        Cancel an event on the calendar.
        
        Args:
            event_title (Optional[str]): Title of the event to cancel
            event_date (Optional[str]): Date of the event (YYYY-MM-DD)
            
        Returns:
            str: Result of the cancellation operation
        """
        # In a real implementation, this would cancel an event in a calendar service
        # For now, we'll just return a placeholder message
        if not event_date:
            event_date = datetime.now().strftime("%Y-%m-%d")
            
        return f"Event '{event_title}' on {event_date} has been cancelled. Notifications sent to all attendees."
    
    def schedule_meeting(self,
                        meeting_type: str,
                        meeting_date: str,
                        meeting_time: str,
                        location: str,
                        attendees: List[str],
                        agenda: Optional[str] = None) -> str:
        """
        Schedule a council meeting.
        
        Args:
            meeting_type (str): Type of meeting (council, committee, etc.)
            meeting_date (str): Date of the meeting (YYYY-MM-DD)
            meeting_time (str): Time of the meeting (HH:MM)
            location (str): Location of the meeting
            attendees (List[str]): List of attendee email addresses
            agenda (Optional[str]): Meeting agenda
            
        Returns:
            str: Result of the scheduling operation
        """
        event_title = f"{meeting_type.title()} Meeting"
        description = f"Regular {meeting_type} meeting.\n\n"
        
        if agenda:
            description += f"Agenda:\n{agenda}"
            
        return self._schedule_event(event_title, meeting_date, meeting_time, 90, attendees, location, description)
    
    def track_deadline(self,
                      task_name: str,
                      deadline: str,
                      assignees: List[str],
                      reminder_days: List[int] = [1, 3, 7]) -> str:
        """
        Track a deadline for a task.
        
        Args:
            task_name (str): Name of the task
            deadline (str): Deadline date (YYYY-MM-DD)
            assignees (List[str]): List of people assigned to the task
            reminder_days (List[int]): Days before deadline to send reminders
            
        Returns:
            str: Result of the deadline tracking operation
        """
        event_title = f"Deadline: {task_name}"
        assignee_str = ", ".join(assignees)
        
        result = f"Deadline tracking set up for '{task_name}' due on {deadline}.\n"
        result += f"Assignees: {assignee_str}\n"
        result += "Reminders scheduled for:\n"
        
        for days in reminder_days:
            reminder_date = (datetime.strptime(deadline, "%Y-%m-%d") - timedelta(days=days)).strftime("%Y-%m-%d")
            result += f"- {reminder_date} ({days} days before deadline)\n"
            
        return result