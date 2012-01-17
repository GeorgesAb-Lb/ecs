from django.utils.translation import ugettext as _

from ecs.communication.utils import send_system_message_template
from ecs.core.workflow import InitialReview, InitialThesisReview
from ecs.core import signals
from ecs.core.models import Submission
from ecs.tasks.utils import get_obj_tasks
from ecs.users.utils import sudo, get_current_user
from ecs.utils import connect


def send_submission_message(submission, user, subject, template, **kwargs):
    send_system_message_template(user, subject.format(ec_number=submission.get_ec_number_display()), template, None, submission=submission, **kwargs)


@connect(signals.on_study_change)
def on_study_change(sender, **kwargs):
    submission = kwargs['submission']
    old_sf, new_sf = kwargs['old_form'], kwargs['new_form']
    
    if not old_sf: # first version of the submission
        involved_users = new_sf.get_involved_parties().get_users().difference([submission.presenter])
        for u in involved_users:
            send_submission_message(submission, u, _('Submission of study EC-Nr. {ec_number}'), 'submissions/creation_message.txt')
    else:
        with sudo():
            if not submission.votes.exists():
                try:
                    initial_review_task = get_obj_tasks((InitialReview, InitialThesisReview), submission).exclude(closed_at__isnull=True)[0]
                except IndexError:
                    pass
                else:
                    initial_review_task.reopen()
                    send_submission_message(submission, initial_review_task.assigned_to, _('Changes new study {ec_number}'), 'submissions/change_message.txt', reply_receiver=submission.presenter)
            else:
                involved_users = new_sf.get_reviewing_parties(active=True).get_users().difference([submission.presenter])
                for u in involved_users:
                    send_submission_message(submission, u, _('Changes B2 {ec_number}'), 'submissions/change_message.txt', reply_receiver=submission.presenter)


@connect(signals.on_study_submit)
def on_study_submit(sender, **kwargs):
    submission = kwargs['submission']
    submission_form = kwargs['form']
    user = kwargs['user']

    submission_form.render_pdf()
    
    resubmission_task = submission.resubmission_task_for(user)
    if resubmission_task:
        resubmission_task.done(user)

    b2_resubmission_task = submission.b2_resubmission_task_for(user)
    if b2_resubmission_task:
        b2_resubmission_task.done(user)


@connect(signals.on_presenter_change)
def on_presenter_change(sender, **kwargs):
    submission = kwargs['submission']
    user = kwargs['user']
    old_presenter, new_presenter = kwargs['old_presenter'], kwargs['new_presenter']
    
    send_submission_message(submission, new_presenter, _('Studie {ec_number}'), 'submissions/presenter_change_new.txt')
    if user != old_presenter:
        send_submission_message(submission, old_presenter, _('Studie {ec_number}'), 'submissions/presenter_change_previous.txt')


@connect(signals.on_susar_presenter_change)
def on_susar_presenter_change(sender, **kwargs):
    submission = kwargs['submission']
    user = kwargs['user']
    old_susar_presenter, new_susar_presenter = kwargs['old_susar_presenter'], kwargs['new_susar_presenter']

    send_submission_message(submission, new_susar_presenter, _('Studie {ec_number}'), 'submissions/susar_presenter_change_new.txt')
    if user != old_susar_presenter:
        send_submission_message(submission, old_susar_presenter, _('Studie {ec_number}'), 'submissions/susar_presenter_change_previous.txt')


@connect(signals.on_initial_review)
def on_initial_review(sender, **kwargs):
    submission, submission_form = kwargs['submission'], kwargs['form']
    review_user = get_current_user()
    if submission_form.is_acknowledged:
        send_submission_message(submission, submission.presenter, _('Acknowledgement of Receipt'), 'submissions/acknowledge_message.txt')
        if not submission.current_submission_form == submission_form:
            submission_form.mark_current()
            involved_users = submission_form.get_involved_parties().get_users().difference([submission_form.presenter])
            for u in involved_users:
                if u == review_user:
                    continue # don't send a message to the initial reviewer
                send_submission_message(submission, u, _('Changes to study EC-Nr. {ec_number}'), 'submissions/change_message.txt', reply_receiver=submission.presenter)
    else:
        send_submission_message(submission, submission.presenter, _('Submission not accepted'), 'submissions/decline_message.txt')


@connect(signals.on_initial_thesis_review)
def on_initial_thesis_review(sender, **kwargs):
    submission, submission_form = kwargs['submission'], kwargs['form']
    if submission_form.is_acknowledged:
        with sudo():
            meeting = submission.schedule_to_meeting()
            meeting.update_assigned_categories()


@connect(signals.on_categorization_review)
def on_categorization_review(sender, **kwargs):
    submission = kwargs['submission']
    meeting = submission.schedule_to_meeting()
    meeting.update_assigned_categories()


@connect(signals.on_b2_upgrade)
def on_b2_upgrade(sender, **kwargs):
    submission, vote = kwargs['submission'], kwargs['vote']
    vote.submission_form.is_acknowledged = True
    vote.submission_form.save()
    vote.submission_form.mark_current()

    if vote.result != '1':
        with sudo():
            meeting = submission.schedule_to_meeting()
            meeting.update_assigned_categories()

