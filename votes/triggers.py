from django.utils.translation import ugettext as _
from django.conf import settings

from ecs.communication.utils import send_system_message_template
from ecs.utils import connect
from ecs.votes import signals
from ecs.votes.constants import PERMANENT_VOTE_RESULTS
from ecs.users.utils import sudo
from ecs.tasks.models import Task


@connect(signals.on_vote_creation)
def on_vote_creation(sender, **kwargs):
    vote = kwargs['vote']
    if vote.result in PERMANENT_VOTE_RESULTS:
        with sudo():
            Task.objects.for_data(vote.submission_form.submission).exclude(task_type__workflow_node__uid='b2_review').open().mark_deleted()

@connect(signals.on_vote_publication)
def on_vote_published(sender, **kwargs):
    vote = kwargs['vote']
    if vote.submission_form and not vote.submission_form.is_categorized_multicentric_and_local:
        parties = vote.submission_form.get_presenting_parties()
        parties.send_message(_('Vote {ec_number}').format(ec_number=vote.get_ec_number()), 'submissions/vote_publish.txt',
            {'vote': vote}, submission=vote.submission_form.submission, cc_groups=settings.ECS_VOTE_RECEIVER_GROUPS)

@connect(signals.on_vote_expiry)
def on_vote_expiry(sender, **kwargs):
    print "vote expired", kwargs
    submission = kwargs['submission']
    submission.finish(expired=True)
