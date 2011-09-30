# -*- coding: utf-8 -*-
import datetime
from django.db import models
from django.utils.importlib import import_module
from django.contrib.contenttypes.generic import GenericRelation
from django.utils.translation import ugettext as _

from ecs.documents.models import Document
from ecs.authorization.managers import AuthorizationManager
from ecs.core.parties import get_presenting_parties


class NotificationType(models.Model):
    name = models.CharField(max_length=80, unique=True)
    form = models.CharField(max_length=80, default='ecs.core.forms.NotificationForm')
    diff = models.BooleanField(default=False)
    default_response = models.TextField(blank=True)
    grants_vote_extension = models.BooleanField(default=False)
    finishes_study = models.BooleanField(default=False)
    rejectable = models.BooleanField(default=False)
    
    @property
    def form_cls(self):
        if not hasattr(self, '_form_cls'):
            module, cls_name = self.form.rsplit('.', 1)
            self._form_cls = getattr(import_module(module), cls_name)
        return self._form_cls
    
    def __unicode__(self):
        return self.name


class DiffNotification(models.Model):
    old_submission_form = models.ForeignKey('core.SubmissionForm', related_name="old_for_notification")
    new_submission_form = models.ForeignKey('core.SubmissionForm', related_name="new_for_notification")
    diff = models.TextField()
    
    class Meta:
        abstract = True
        
    def save(self, **kwargs):
        super(DiffNotification, self).save()
        self.submission_forms = [self.old_submission_form]
        self.new_submission_form.transient = False
        self.new_submission_form.save()


class Notification(models.Model):
    type = models.ForeignKey(NotificationType, null=True, related_name='notifications')
    submission_forms = models.ManyToManyField('core.SubmissionForm', related_name='notifications')
    documents = GenericRelation(Document)
    #documents = models.ManyToManyField(Document)

    comments = models.TextField(default="", blank=True)
    date_of_receipt = models.DateField(null=True, blank=True)
    timestamp = models.DateTimeField(default=datetime.datetime.now)
    user = models.ForeignKey('auth.User', null=True)

    needs_executive_review = models.BooleanField(default=False)
    
    objects = AuthorizationManager()
    
    def __unicode__(self):
        return u"%s für %s" % (self.type, " + ".join(unicode(sf.submission) for sf in self.submission_forms.all()))
        
    @property
    def rejected(self):
        try:
            return self.answer.rejected
        except NotificationAnswer.DoesNotExist:
            return None


class ReportNotification(Notification):
    reason_for_not_started = models.TextField(null=True, blank=True)
    recruited_subjects = models.IntegerField(null=True, blank=True)
    finished_subjects = models.IntegerField(null=True, blank=True)
    aborted_subjects = models.IntegerField(null=True, blank=True)
    SAE_count = models.PositiveIntegerField(default=0, blank=True)
    SUSAR_count = models.PositiveIntegerField(default=0, blank=True)
    
    class Meta:
        abstract = True
    

class CompletionReportNotification(ReportNotification):
    study_aborted = models.BooleanField()
    completion_date = models.DateField()



class ProgressReportNotification(ReportNotification):
    runs_till = models.DateField(null=True, blank=True)
    extension_of_vote_requested = models.BooleanField(default=False, blank=True)
    

class AmendmentNotification(DiffNotification, Notification):
    pass


class NotificationAnswer(models.Model):
    notification = models.OneToOneField(Notification, related_name="answer")
    valid = models.BooleanField(default=True) # if the notification has been accepted by the office
    review_count = models.PositiveIntegerField(default=0)
    text = models.TextField()
    rejected = models.BooleanField(default=False)
    
    @property
    def needs_further_review(self):
        # further review is required iff: the answer is not valid or has not been reviewed by a multiple of four eyes.
        return not self.valid or self.review_count == 0 or self.review_count % 2 != 0
    
    def distribute(self):
        from ecs.core.models.submissions import Submission
        from ecs.communication.utils import send_system_message_template
        
        extend, finish = False, False
        if not self.rejected:
            if self.notification.type.grants_vote_extension:
                try:
                    extend = ProgressReportNotification.objects.get(pk=self.notification.pk).extension_of_vote_requested
                except ProgressReportNotification.DoesNotExist:
                    pass
            if self.notification.type.finishes_study:
                finish = True
        interested_parties = set()

        for submission in Submission.objects.filter(forms__in=self.notification.submission_forms.values('pk').query):
            for party in get_presenting_parties(submission.current_submission_form):
                interested_parties.add(party)
            if extend:
                for vote in submission.votes.positive().permanent():
                    vote.extend()
            if finish:
                submission.finish()
            
        for party in interested_parties:
            if party.user: # FIXME: why don't have all parties shadow users?
                send_system_message_template(party.user, _('New Notification Answer'), 'notifications/answers/new_message.txt', context={
                    'notification': self.notification,
                    'answer': self,
                    'recipient': party,
                }, submission=submission)

    
