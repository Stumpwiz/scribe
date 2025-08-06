from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory
from datetime import datetime, timedelta
import os
import logging
from scribe.utils import get_next_meeting_date
from scribe.tools.meeting_notification_tool import MeetingNotificationTool, get_meeting_type_from_date

# Set up logging
logger = logging.getLogger(__name__)

reminder_bp = Blueprint('reminder', __name__, template_folder='../templates')


@reminder_bp.route('/', methods=['GET', 'POST'])
def reminder():
    from datetime import date

    # Get the next meeting date
    next_meeting_date = get_next_meeting_date()
    today_date = date.today()
    
    # Initialize default meeting type based on the next meeting date
    default_meeting_type = "unknown"
    try:
        default_meeting_type = get_meeting_type_from_date(next_meeting_date)
    except Exception:
        # Silently handle any errors when determining the default meeting type
        pass
    
    context = {
        "meeting_date": next_meeting_date.strftime("%Y-%m-%d"),
        "today_date": today_date.strftime("%Y-%m-%d"),  # For min attribute in date input
        "old_business": "",
        "new_business": "",
        "success": False,
        "error": None,
        "default_meeting_type": default_meeting_type
    }

    if request.method == 'POST':
        try:
            meeting_date_str = request.form.get("meeting_date")
            old_business = request.form.get("old_business", "").strip()
            new_business = request.form.get("new_business", "").strip()

            # Validate date format
            try:
                meeting_date = datetime.strptime(meeting_date_str, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError("Invalid date format. Please use YYYY-MM-DD format.")
            
            # Validate meeting date is not in the past
            today = date.today()
            if meeting_date < today:
                raise ValueError("Meeting date cannot be in the past. Please select a future date.")

            os.makedirs("src/scribe/input", exist_ok=True)
            with open("src/scribe/input/old_business.txt", "w", encoding="utf-8") as f:
                f.write(old_business)
            with open("src/scribe/input/new_business.txt", "w", encoding="utf-8") as f:
                f.write(new_business)
            
            # Determine meeting type based on the date
            try:
                meeting_type = get_meeting_type_from_date(meeting_date)
                logger.info(f"Meeting details: date={meeting_date}, type={meeting_type}")
            except TypeError as e:
                error_msg = f"Invalid meeting date format: {str(e)}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            except Exception as e:
                error_msg = f"Error determining meeting type: {str(e)}"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
            # Get recipients for the meeting
            notification_tool = MeetingNotificationTool()
            recipients = notification_tool.get_recipients(meeting_type)
            
            # Log recipient information
            logger.info(f"Recipients: count={len(recipients)}")
            
            # Note: We no longer need to check if recipients list is empty
            # as get_recipients() now has a fallback to geo@loyola.edu
                
            # Import crew here to avoid circular import issues
            # (crew imports email_service which transitively depends on reminder_routes)
            from scribe.crew import crew
            
            # Construct inputs dictionary as specified
            # Note: submission_deadline and review_deadline fields have been removed due to simplification
            inputs = {
                "meeting_date": str(meeting_date),
                "meeting_type": meeting_type,
                "old_business_items": old_business.split("\n") if old_business else [],
                "new_business_items": new_business.split("\n") if new_business else [],
                "email_recipients": recipients,  # Should be a list of valid email strings
            }
            
            # Create the kickoff context with agent, task, and inputs
            kickoff_context = {
                "agent": "ReminderAgent",
                "task": "send_meeting_notification",
                "inputs": inputs
            }
            
            # Log the inputs dictionary keys as required
            logger.info(f"Inputs dictionary keys: {list(kickoff_context['inputs'].keys())}")
            
            # Log ReminderAgent invocation details with full context
            logger.info(f"Kicking off ReminderAgent with context: {kickoff_context}")
            
            # Add more detailed debug logging
            logger.debug(f"Agent: {kickoff_context['agent']}")
            logger.debug(f"Task: {kickoff_context['task']}")
            logger.debug(f"Meeting date: {kickoff_context['inputs']['meeting_date']}")
            logger.debug(f"Meeting type: {kickoff_context['inputs']['meeting_type']}")
            logger.debug(f"Old business items: {kickoff_context['inputs']['old_business_items']}")
            logger.debug(f"New business items: {kickoff_context['inputs']['new_business_items']}")
            logger.debug(f"Email recipients: {kickoff_context['inputs']['email_recipients']}")
            
            results = crew.kickoff({
                "send_meeting_notification": kickoff_context["inputs"]
            })
            
            # Log results including file paths if available
            if results and isinstance(results, dict):
                # Check for LaTeX file path
                latex_path = results.get('latex_path')
                if latex_path:
                    logger.info(f"LaTeX file generated: path={latex_path}")
                
                # Check for PDF file path
                pdf_path = results.get('pdf_path')
                if pdf_path:
                    logger.info(f"Agenda PDF generated: path={pdf_path}")
                
                # Log any other relevant output
                if 'success' in results:
                    logger.info(f"ReminderAgent task completed: success={results['success']}")

            context.update({
                "success": True,
                "old_business": old_business,
                "new_business": new_business,
                "meeting_type": meeting_type,
                "meeting_date": meeting_date_str  # Preserve the selected date
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            # Update context with form values to preserve them
            context.update({
                "success": False,
                "error": str(e),
                "old_business": old_business if 'old_business' in locals() else "",
                "new_business": new_business if 'new_business' in locals() else "",
                "meeting_date": meeting_date_str if 'meeting_date_str' in locals() else context["meeting_date"]
            })

    return render_template("reminder.html", **context)
