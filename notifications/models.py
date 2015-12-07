# -*- coding: utf-8 -*-
from datetime import datetime

from django.conf import settings
from django.db import models
from django.utils.importlib import import_module
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext
from django.template import loader
from django.template.defaultfilters import slugify

import reversion
from reversion.models import Version

from ecs.documents.models import Document
from ecs.utils.viewutils import render_pdf_context
from ecs.notifications.constants import SAFETY_TYPE_CHOICES, NOTIFICATION_REVIEW_LANE_CHOICES
from ecs.notifications.managers import NotificationManager
from ecs.authorization.managers import AuthorizationManager


class NotificationType(models.Model):
    name = models.CharField(max_length=80, unique=True)
    form = models.CharField(max_length=80, default='ecs.notifications.forms.NotificationForm')
    default_response = models.TextField(blank=True)
    position = models.IntegerField(default=0)

    includes_diff = models.BooleanField(default=False)
    grants_vote_extension = models.BooleanField(default=False)
    finishes_study = models.BooleanField(default=False)
    is_rejectable = models.BooleanField(default=False)
    
    @property
    def form_cls(self):
        if not hasattr(self, '_form_cls'):
            module, cls_name = self.form.rsplit('.', 1)
            self._form_cls = getattr(import_module(module), cls_name)
        return self._form_cls
        
    def get_template(self, pattern):
        template_names = [pattern % name for name in (self.form_cls.__name__, 'base')]
        return loader.select_template(template_names)
    
    def __unicode__(self):
        return self.name


class DiffNotification(models.Model):
    old_submission_form = models.ForeignKey('core.SubmissionForm', related_name="old_for_notification")
    new_submission_form = models.ForeignKey('core.SubmissionForm', related_name="new_for_notification")
    
    class Meta:
        abstract = True
        
    def save(self, **kwargs):
        super(DiffNotification, self).save()
        self.submission_forms = [self.old_submission_form]
        self.new_submission_form.is_transient = False
        self.new_submission_form.save()
        
    def apply(self):
        new_sf = self.new_submission_form
        if not self.new_submission_form.is_current and self.old_submission_form.is_current:
            new_sf.is_acknowledged = True
            new_sf.save()
            new_sf.mark_current()
            return True
        else:
            return False

    def get_diff(self, plainhtml=False):
        from ecs.core.diff import diff_submission_forms
        return diff_submission_forms(self.old_submission_form, self.new_submission_form).html(plain=plainhtml)


class Notification(models.Model):
    type = models.ForeignKey(NotificationType, null=True, related_name='notifications')
    submission_forms = models.ManyToManyField('core.SubmissionForm', related_name='notifications')
    documents = models.ManyToManyField('documents.Document', related_name='notifications')
    pdf_document = models.OneToOneField(Document, related_name='_notification', null=True)

    comments = models.TextField()
    date_of_receipt = models.DateField(null=True, blank=True)
    timestamp = models.DateTimeField(default=datetime.now)
    user = models.ForeignKey('auth.User', null=True)
    
    review_lane = models.CharField(max_length=6, null=True, db_index=True, choices=NOTIFICATION_REVIEW_LANE_CHOICES)
    
    objects = NotificationManager()
    
    def __unicode__(self):
        return u"%s für %s" % (self.type, " + ".join(unicode(sf.submission) for sf in self.submission_forms.all()))
    
    @property
    def short_name(self):
        return unicode(self.type)
        
    @property
    def is_rejected(self):
        try:
            return self.answer.is_rejected
        except NotificationAnswer.DoesNotExist:
            return None

    def get_submission_form(self):
        if self.submission_forms.exists():
            return self.submission_forms.all()[0]
        return None

    def get_submission(self):
        sf = self.get_submission_form()
        if sf:
            return sf.submission
        return None
            
    def get_filename(self, suffix=".pdf"):
        ec_num = '_'.join(str(s['submission__ec_number']) for s in self.submission_forms.order_by('submission__ec_number').values('submission__ec_number').distinct())
        return "%s%s" % (slugify("%s-%s" % (ec_num, self.type.name)), suffix)
            
    def render_pdf(self):
        tpl = self.type.get_template('db/notifications/wkhtml2pdf/%s.html')
        submission_forms = self.submission_forms.select_related('submission').all()
        pdf = render_pdf_context(tpl, {
            'notification': self,
            'submission_forms': submission_forms,
            'documents': self.documents.select_related('doctype').order_by('doctype__name', 'version', 'date'),
        })
        now = datetime.now()

        self.pdf_document = Document.objects.create_from_buffer(pdf, 
            doctype='notification', parent_object=self, name=unicode(self),
            original_file_name=self.get_filename(), version=str(now), date=now
        )
        self.save()
        
        return self.pdf_document


class ReportNotification(Notification):
    study_started = models.BooleanField(default=True)
    reason_for_not_started = models.TextField(null=True, blank=True)
    recruited_subjects = models.IntegerField(null=True, blank=False)
    finished_subjects = models.IntegerField(null=True, blank=False)
    aborted_subjects = models.IntegerField(null=True, blank=False)
    SAE_count = models.PositiveIntegerField(default=0, blank=False)
    SUSAR_count = models.PositiveIntegerField(default=0, blank=False)
    
    class Meta:
        abstract = True
    

class CompletionReportNotification(ReportNotification):
    study_aborted = models.BooleanField()
    completion_date = models.DateField()


class ProgressReportNotification(ReportNotification):
    runs_till = models.DateField(null=True, blank=True)


class AmendmentNotification(DiffNotification, Notification):
    pass


class SafetyNotification(Notification):
    safety_type = models.CharField(max_length=6, db_index=True, choices=SAFETY_TYPE_CHOICES, verbose_name=_('Type'))
    is_acknowledged = models.BooleanField(default=False)
    reviewer = models.ForeignKey('auth.User', null=True)


class NotificationAnswer(models.Model):
    notification = models.OneToOneField(Notification, related_name="answer")
    text = models.TextField()
    is_valid = models.BooleanField(default=True)
    is_final_version = models.BooleanField(default=False, verbose_name=_('Proofread')) # informal
    is_rejected = models.BooleanField(default=False, verbose_name=_('rate negative'))
    pdf_document = models.OneToOneField(Document, related_name='_notification_answer', null=True)
    signed_at = models.DateTimeField(null=True)
    published_at = models.DateTimeField(null=True)
    
    objects = AuthorizationManager()

    @property
    def version_number(self):
        return Version.objects.get_for_object(self).count()

    @property
    def needs_further_review(self):
        return not self.is_valid

    def get_render_context(self):
        return {
            'notification': self.notification,
            'documents': self.notification.documents.exclude(status='deleted').select_related('doctype').order_by('doctype__name', '-date'),
            'answer': self,
        }

    def render_pdf(self):
        notification = self.notification
        tpl = notification.type.get_template('db/notifications/answers/wkhtml2pdf/%s.html')
        pdf = render_pdf_context(tpl, self.get_render_context())

        now = datetime.now()
        self.pdf_document = Document.objects.create_from_buffer(pdf, 
            doctype='notification_answer', parent_object=self,
            name=unicode(self), version=str(now), date=now,
            original_file_name=notification.get_filename('-answer.pdf')
        )
        self.save()
        return self.pdf_document
    
    def distribute(self):
        from ecs.core.models.submissions import Submission
        self.published_at = datetime.now()
        self.save()
        
        if not self.is_rejected and self.notification.type.includes_diff:
            try:
                notification = AmendmentNotification.objects.get(pk=self.notification.pk)
                notification.apply()
            except AmendmentNotification.DoesNotExist:
                assert False, "we should never get here"
        
        extend, finish = False, False
        if not self.is_rejected:
            if self.notification.type.grants_vote_extension:
                extend = True
            if self.notification.type.finishes_study:
                finish = True

        for submission in Submission.objects.filter(forms__in=self.notification.submission_forms.values('pk').query):
            if extend:
                for vote in submission.votes.positive().permanent():
                    vote.extend()
            if finish:
                submission.finish()
            presenting_parties = submission.current_submission_form.get_presenting_parties()
            cc_groups = settings.ECS_AMENDMENT_RECEIVER_GROUPS if self.notification.type.includes_diff else ()
            _ = ugettext
            presenting_parties.send_message(_('New Notification Answer'), 'notifications/answers/new_message.txt', context={
                'notification': self.notification,
                'answer': self,
                'ABSOLUTE_URL_PREFIX': settings.ABSOLUTE_URL_PREFIX,
            }, submission=submission, cc_groups=cc_groups)

reversion.register(NotificationAnswer, fields=('text',))


NOTIFICATION_MODELS = (
    Notification, CompletionReportNotification, ProgressReportNotification,
    AmendmentNotification, SafetyNotification
)
