from ecs.communication.models import Thread
from ecs.users.utils import get_user

def send_submission_message(submission, subject, text, recipients, email='root@system.local'):
    for recipient in recipients:
        thread, created = Thread.objects.get_or_create(
            subject=subject,
            sender=get_user(email),
            receiver=recipient,
            submission=submission
        )
        message = thread.add_message(get_user(email), text=text)
