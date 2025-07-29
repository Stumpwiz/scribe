from datetime import date, timedelta

def get_next_meeting_date(today: date = date.today()) -> date:
    """Returns the date of the next Residents Council meeting,
    which occurs on the first Thursday of each month."""
    year = today.year
    month = today.month

    # Move to next month if today is after first Thursday
    first_day = date(year, month, 1)
    weekday_of_first = first_day.weekday()  # Monday = 0
    days_until_thursday = (3 - weekday_of_first) % 7
    first_thursday = first_day + timedelta(days=days_until_thursday)

    if today >= first_thursday:
        # Move to next month
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
        first_day = date(year, month, 1)
        weekday_of_first = first_day.weekday()
        days_until_thursday = (3 - weekday_of_first) % 7
        first_thursday = first_day + timedelta(days=days_until_thursday)

    return first_thursday
