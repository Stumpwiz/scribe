from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory
from datetime import datetime, timedelta
import os
from scribe.crew import crew
from scribe.utils import get_next_meeting_date

reminder_bp = Blueprint('reminder', __name__, template_folder='../templates')


@reminder_bp.route('/', methods=['GET', 'POST'])
def reminder():
    from datetime import date

    context = {
        "meeting_date": get_next_meeting_date().strftime("%Y-%m-%d"),
        "old_business": "",
        "new_business": "",
        "success": False,
        "error": None
    }

    if request.method == 'POST':
        try:
            meeting_date_str = request.form.get("meeting_date")
            old_business = request.form.get("old_business", "")
            new_business = request.form.get("new_business", "")

            meeting_date = datetime.strptime(meeting_date_str, "%Y-%m-%d").date()

            os.makedirs("src/scribe/input", exist_ok=True)
            with open("src/scribe/input/old_business.txt", "w", encoding="utf-8") as f:
                f.write(old_business.strip())
            with open("src/scribe/input/new_business.txt", "w", encoding="utf-8") as f:
                f.write(new_business.strip())
            submission_deadline = meeting_date - timedelta(days=5)
            results = crew.kickoff(inputs={
                "meeting_date": str(meeting_date),
                "submission_deadline": str(submission_deadline),
                "review_deadline": str(submission_deadline)  # Dummy placeholder
            })

            context.update({
                "success": True,
                "old_business": old_business,
                "new_business": new_business
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            context["error"] = str(e)

    return render_template("reminder.html", **context)
