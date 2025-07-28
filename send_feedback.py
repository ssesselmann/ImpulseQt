# send_feedback.py

import platform, webbrowser, datetime
import shared

def send_feedback_email(sentiment):
    start = shared.session_start
    end = shared.session_end
    duration = (end - start).total_seconds()

    body = f"""
    Hi Impulse developer, 

    My session today: {sentiment}

    My OS: {platform.system()} {platform.version()}
    My Version: {getattr(shared, 'version', 'unknown')}
    My Session duration: {duration:.1f} seconds

    Feel free to add a comment below to provide feedback to the developer.

    ...
    """

    subject_encoded = f"Impulse Feedback - {sentiment}".replace(' ', '%20')
    body_encoded = body.replace(' ', '%20').replace('\n', '%0A')

    mailto = f"mailto:impulse@gammaspectacular.com?subject={subject_encoded}&body={body_encoded}"
    webbrowser.open(mailto)