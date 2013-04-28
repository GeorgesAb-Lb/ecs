# -*- coding: utf-8 -*-

from django import forms
from django.utils.translation import ugettext_lazy as _

from ecs.notifications.models import NotificationAnswer
from ecs.core.models import SubmissionForm, Submission
from ecs.users.utils import get_current_user
from ecs.utils.formutils import ModelFormPickleMixin, require_fields
from ecs.notifications.models import Notification, CompletionReportNotification, ProgressReportNotification, AmendmentNotification, SafetyNotification
from ecs.core.forms.fields import DateField


class NotificationAnswerForm(forms.ModelForm):
    class Meta:
        model = NotificationAnswer
        fields = ('text', 'is_final_version',)


class RejectableNotificationAnswerForm(NotificationAnswerForm):
    is_rejected = NotificationAnswer._meta.get_field('is_rejected').formfield(required=False)

    class Meta:
        model = NotificationAnswer
        fields = ('is_rejected', 'is_final_version', 'text',)


def get_usable_submission_forms():
    submission_forms = (SubmissionForm.objects
        .with_any_vote(permanent=True, positive=True, published=True)
        .current())
    return submission_forms.order_by('submission__ec_number')


class NotificationForm(ModelFormPickleMixin, forms.ModelForm):
    class Meta:
        model = Notification
        exclude = ('type', 'documents', 'investigators', 'date_of_receipt', 'user', 'timestamp', 'pdf_document', 'review_lane')


class SafetyNotificationForm(NotificationForm):
    comments = forms.CharField(widget=forms.Textarea(), initial=_(u'Aus der Sicht des Sponsors ergeben sich derzeit keine Veränderungen des Nutzen/Risikoverhältnisses.'))

    def __init__(self, *args, **kwargs):
        super(SafetyNotificationForm, self).__init__(*args, **kwargs)
        self.fields['submission_forms'].queryset = get_usable_submission_forms().filter(submission__susar_presenter=get_current_user())
        
    class Meta:
        model = SafetyNotification
        exclude = NotificationForm._meta.exclude + ('reviewer',)


class SingleStudyNotificationForm(NotificationForm):
    submission_form = forms.ModelChoiceField(queryset=SubmissionForm.objects.all(), label=_('Study'))
    
    def __init__(self, *args, **kwargs):
        super(SingleStudyNotificationForm, self).__init__(*args, **kwargs)
        self.fields['submission_form'].queryset = get_usable_submission_forms().filter(submission__presenter=get_current_user(), submission__is_finished=False)

    class Meta:
        model = Notification
        exclude = NotificationForm._meta.exclude + ('submission_forms',)
        
    def get_submission_form(self):
        return self.cleaned_data['submission_form']
    
    def save(self, commit=True):
        obj = super(SingleStudyNotificationForm, self).save(commit=commit)
        if commit:
            obj.submission_forms = [self.get_submission_form()]
        else:
            old_save_m2m = self.save_m2m
            def _save_m2m():
                old_save_m2m()
                obj.submission_forms = [self.get_submission_form()]
            self.save_m2m = _save_m2m
        return obj


class ProgressReportNotificationForm(SingleStudyNotificationForm):
    runs_till = DateField(required=True)

    class Meta:
        model = ProgressReportNotification
        exclude = SingleStudyNotificationForm._meta.exclude

    def clean(self):
        cleaned_data = super(ProgressReportNotificationForm, self).clean()
        if not cleaned_data.get('study_started', False):
            require_fields(self, ('reason_for_not_started',))
        return cleaned_data


class CompletionReportNotificationForm(SingleStudyNotificationForm):
    completion_date = DateField(required=True)

    class Meta:
        model = CompletionReportNotification
        exclude = SingleStudyNotificationForm._meta.exclude


class AmendmentNotificationForm(NotificationForm):
    class Meta:
        model = AmendmentNotification
        exclude = NotificationForm._meta.exclude + ('submission_forms', 'old_submission_form', 'new_submission_form', 'diff')
