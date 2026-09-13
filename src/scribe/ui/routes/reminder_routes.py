from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory
from datetime import datetime, timedelta
import os
import logging
from scribe.utils import get_next_meeting_date
from scribe.tools.meeting_notification_tool import MeetingNotificationTool, get_meeting_type_from_date
from scribe.tools.meeting_agenda_generator_tool import MeetingAgendaGeneratorTool

# Set up logging
logger = logging.getLogger(__name__)

reminder_bp = Blueprint('reminder', __name__, template_folder='../templates')


@reminder_bp.route('/', methods=['GET', 'POST'])
def reminder():
    from datetime import date
    default_dry_run = os.getenv("DRY_RUN", "true").strip().lower() in ("1", "true", "yes", "y", "on")

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
        "default_meeting_type": default_meeting_type,
        "dry_run_checked": default_dry_run,
        "dry_run_result": False,
    }

    if request.method == 'POST':
        try:
            meeting_date_str = request.form.get("meeting_date")
            old_business = request.form.get("old_business", "").strip()
            new_business = request.form.get("new_business", "").strip()
            dry_run = bool(request.form.get("dry_run"))

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
            recipients = notification_tool.get_recipients(meeting_type, meeting_date=str(meeting_date))
            
            # Log recipient information
            logger.info(f"Recipients: count={len(recipients)}")
            
            # Note: We no longer need to check if recipients list is empty
            # as get_recipients() now has a safe fallback to DEFAULT_FALLBACK_EMAIL (or test@example.com)
                
            # For simple tasks like sending notifications, call the tool directly
            # rather than using CrewAI agents (which are unreliable at following instructions)

            # Parse business items
            old_business_items = old_business.split("\n") if old_business else []
            new_business_items = new_business.split("\n") if new_business else []

            # Log the inputs
            logger.info(f"Sending meeting notification:")
            logger.info(f"  Meeting date: {meeting_date}")
            logger.info(f"  Meeting type: {meeting_type}")
            logger.info(f"  Old business items: {old_business_items}")
            logger.info(f"  New business items: {new_business_items}")
            logger.info(f"  Recipients: {len(recipients)}")

            # Generate agenda PDF
            logger.info("Generating agenda PDF...")
            agenda_tool = MeetingAgendaGeneratorTool()

            # Calculate next meeting date (first Thursday of next month)
            next_month = meeting_date.month % 12 + 1
            next_year = meeting_date.year if next_month > meeting_date.month else meeting_date.year + 1
            from calendar import monthrange
            # Find first Thursday of next month
            first_day_of_month = datetime(next_year, next_month, 1).date()
            days_until_thursday = (3 - first_day_of_month.weekday()) % 7  # 3 = Thursday
            next_meeting = first_day_of_month + timedelta(days=days_until_thursday)

            # Determine venues
            if meeting_type == "open":
                this_venue = "Performing Arts Center (PAC)"
            else:
                this_venue = "McAuley Conference Room (MCR)"

            # Determine next meeting type and venue
            next_meeting_type = get_meeting_type_from_date(next_meeting)
            if next_meeting_type == "open":
                next_venue = "Performing Arts Center (PAC)"
            else:
                next_venue = "McAuley Conference Room (MCR)"

            meeting_info = {
                "date": str(meeting_date),  # ISO format for MeetingCalendarTool
                "meetingDate": meeting_date.strftime("%Y-%m-%d"),
                "cycle": meeting_date.strftime("%Y-%m"),
                "meetingTime": "2:00 PM",
                "nextMeetingDate": next_meeting.strftime("%B %d, %Y"),
                "thisVenue": this_venue,
                "mextVenue": next_venue,  # Keep the typo to match template
                "meetingType": meeting_type,
                "oldBusinessItems": old_business_items,
                "newBusinessItems": new_business_items
            }

            agenda_result = agenda_tool._run(meeting_info=meeting_info)

            if agenda_result.get("success"):
                logger.info(f"Agenda PDF generated successfully: {agenda_result.get('pdfPath')}")
            else:
                logger.warning(f"Agenda PDF generation failed: {agenda_result.get('log', 'Unknown error')}")
                # Continue anyway - we'll send without attachment

            # Call MeetingNotificationTool directly with the form data
            result = notification_tool._run(
                meeting_date=str(meeting_date),
                meeting_type=meeting_type,
                old_business_items=old_business_items,
                new_business_items=new_business_items,
                agenda_result=agenda_result,
                recipients=recipients,  # Pass the recipients list
                filename_hint=f"{meeting_type}_meeting_{meeting_date}",
                dry_run=dry_run,
            )

            logger.info(f"Meeting notification sent: {result}")
            results = result if isinstance(result, dict) else {"success": True, "message": result}

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

            # Use flash message and redirect to clear form
            if results.get("status") == "dry_run":
                context.update({
                    "success": True,
                    "dry_run_checked": True,
                    "dry_run_result": True,
                    "recipient_count": results.get("recipient_count", 0),
                    "attachment_path": results.get("attachment_path", ""),
                    "draft_path": results.get("draft_path", ""),
                    "old_business": old_business,
                    "new_business": new_business,
                    "meeting_date": meeting_date_str,
                })
                return render_template("reminder.html", **context)

            message_id = results.get("message_id", "")
            if message_id:
                flash(f"Reminder sent successfully. Message ID: {message_id}", "success")
            else:
                flash("The meeting reminder has been sent successfully.", "success")
            return redirect(url_for('reminder.reminder'))
        except Exception as e:
            import traceback
            traceback.print_exc()
            # Update context with form values to preserve them
            context.update({
                "success": False,
                "error": str(e),
                "old_business": old_business if 'old_business' in locals() else "",
                "new_business": new_business if 'new_business' in locals() else "",
                "meeting_date": meeting_date_str if 'meeting_date_str' in locals() else context["meeting_date"],
                "dry_run_checked": dry_run if 'dry_run' in locals() else default_dry_run,
                "dry_run_result": False,
            })

    return render_template("reminder.html", **context)
