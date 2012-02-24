# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db.models.signals import post_save
from django.utils.translation import ugettext as _

from ecs.workflow import Activity, guard, register
from ecs.checklists.models import Checklist
from ecs.communication.utils import send_system_message_template
from ecs.tasks.signals import task_declined
from ecs.users.utils import get_current_user, sudo
from ecs.meetings.models import Meeting
from ecs.billing.models import Price

register(Checklist)

@guard(model=Checklist)
def is_external_review_checklist(wf):
    return wf.data.blueprint.slug == 'external_review'

@guard(model=Checklist)
def checklist_review_review_failed(wf):
    return wf.data.status == 'review_fail'

class ExternalReview(Activity):
    class Meta:
        model = Checklist

    def is_repeatable(self):
        return True

    def is_reentrant(self):
        return True

    def is_locked(self):
        checklist = self.workflow.data
        return not checklist.is_complete

    def get_url(self):
        checklist = self.workflow.data
        blueprint = checklist.blueprint
        submission_form = checklist.submission.current_submission_form
        return reverse('ecs.core.views.checklist_review', kwargs={'submission_form_pk': submission_form.pk, 'blueprint_pk': blueprint.pk})

    def receive_token(self, *args, **kwargs):
        c = self.workflow.data
        token = super(ExternalReview, self).receive_token(*args, **kwargs)
        token.task.accept(c.user)
        if c.status == 'new':
            with sudo():
                try:
                    meeting = Meeting.objects.filter(pk__in=c.submission.timetable_entries.values('meeting__pk').query, started__isnull=True).order_by('start')[0]
                except IndexError:
                    meeting = None
            price = Price.objects.get_review_price()
            send_system_message_template(c.user, _('Request for review'), 'checklists/external_reviewer_invitation.txt', {'task': token.task, 'meeting': meeting, 'price': price, 'ABSOLUTE_URL_PREFIX': settings.ABSOLUTE_URL_PREFIX}, submission=c.submission)
        return token

def unlock_external_review(sender, **kwargs):
    kwargs['instance'].workflow.unlock(ExternalReview)
post_save.connect(unlock_external_review, sender=Checklist)

# treat declined external review tasks as if the deadline was reached
def external_review_declined(sender, **kwargs):
    task = kwargs['task']
    task.node_controller.progress(task.workflow_token, deadline=True)
task_declined.connect(external_review_declined, sender=ExternalReview)

class ExternalReviewReview(Activity):
    class Meta:
        model = Checklist

    def get_url(self):
        checklist = self.workflow.data
        submission_form = checklist.submission.current_submission_form
        return reverse('ecs.core.views.show_checklist_review', kwargs={'submission_form_pk': submission_form.pk, 'checklist_pk': checklist.pk})

    def get_choices(self):
        return (
            ('review_ok', _('Publish')),
            ('review_fail', _('Send back to external Reviewer')),
            ('dropped', _('Drop')),
        )

    def pre_perform(self, choice):
        c = self.workflow.data
        c.status = choice
        c.save()
        if c.status == 'review_ok':
            c.render_pdf()
            presenting_parties = c.submission.current_submission_form.get_presenting_parties()
            presenting_parties.send_message(_('External Review'), 'checklists/external_review_publish.txt',
                {'checklist': c, 'ABSOLUTE_URL_PREFIX': settings.ABSOLUTE_URL_PREFIX},
                submission=c.submission)
        elif c.status == 'review_fail':
            send_system_message_template(c.user, _('Query regarding review'), 'checklists/external_review_declined.txt', None, submission=c.submission)
