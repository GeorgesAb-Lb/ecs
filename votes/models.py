# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _

import reversion
from reversion.models import Version

from ecs.votes.constants import (VOTE_RESULT_CHOICES, POSITIVE_VOTE_RESULTS, NEGATIVE_VOTE_RESULTS, FINAL_VOTE_RESULTS, PERMANENT_VOTE_RESULTS, RECESSED_VOTE_RESULTS)
from ecs.votes.managers import VoteManager
from ecs.votes.signals import on_vote_publication, on_vote_expiry, on_vote_extension


class Vote(models.Model):
    submission_form = models.ForeignKey('core.SubmissionForm', related_name='votes', null=True)
    top = models.OneToOneField('meetings.TimetableEntry', related_name='vote', null=True)
    upgrade_for = models.OneToOneField('self', null=True, related_name='previous')
    result = models.CharField(max_length=2, choices=VOTE_RESULT_CHOICES, null=True, verbose_name=_(u'vote'))
    executive_review_required = models.NullBooleanField(blank=True)
    insurance_review_required = models.NullBooleanField(blank=True)
    text = models.TextField(blank=True, verbose_name=_(u'comment'))
    is_draft = models.BooleanField(default=False)
    is_final_version = models.BooleanField(default=False)
    is_expired = models.BooleanField(default=False)
    signed_at = models.DateTimeField(null=True)
    published_at = models.DateTimeField(null=True)
    valid_until = models.DateTimeField(null=True)
    changed_after_voting = models.BooleanField(default=False)
    
    objects = VoteManager()

    class Meta:
        get_latest_by = 'published_at'

    def get_submission(self):
        if self.submission_form:
            return self.submission_form.submission
        else:
            return None
    
    @property
    def result_text(self):
        # FIXME: use get_result_display instead
        if self.result is None:
            return _('No Result')
        return dict(VOTE_RESULT_CHOICES)[self.result]

    def get_ec_number(self):
        if self.top and self.top.submission:
            return self.top.submission.get_ec_number_display()
        elif self.submission_form:
            return self.submission_form.submission.get_ec_number_display()
        return None
        
    def __unicode__(self):
        ec_number = self.get_ec_number()
        if ec_number:
            return 'Votum %s' % ec_number
        return 'Votum ID %s' % self.pk
        
    def save(self, **kwargs):
        if not self.submission_form_id and self.top_id:
            self.submission_form = self.top.submission.current_submission_form
        return super(Vote, self).save(**kwargs)

    def publish(self):
        assert self.signed_at is not None
        now = datetime.now()
        self.published_at = now
        self.valid_until = self.published_at + timedelta(days=365)
        self.save()
        if self.submission_form:
            Vote.objects.filter(pk__in=self.submission_form.submission.forms.values('current_published_vote__pk')).exclude(pk=self.pk).update(valid_until=now)
        on_vote_publication.send(sender=Vote, vote=self)

    def expire(self):
        assert not self.is_expired
        self.is_expired = True
        self.save()
        on_vote_expiry.send(Vote, vote=self)
    
    def extend(self):
        d = self.valid_until
        self.valid_until += timedelta(days=365)
        self.is_expired = False
        self.save()
        on_vote_extension.send(Vote, vote=self)

    @property
    def version_number(self):
        return Version.objects.get_for_object(self).count()
    
    @property
    def is_positive(self):
        return self.result in POSITIVE_VOTE_RESULTS
        
    @property
    def is_negative(self):
        return self.result in NEGATIVE_VOTE_RESULTS
        
    @property
    def is_final(self):
        return self.result in FINAL_VOTE_RESULTS
        
    @property
    def is_permanent(self):
        return self.result in PERMANENT_VOTE_RESULTS
        
    @property
    def is_recessed(self):
        return self.result in RECESSED_VOTE_RESULTS
        
    @property
    def activates(self):
        # XXX: is this used anywhere?
        return self.result == '1'
        
    @property
    def is_valid(self):
        # XXX: is this used anywhere?
        return self.valid_until < datetime.now()

    def get_render_context(self):
        past_votes = Vote.objects.filter(published_at__isnull=False, submission_form__submission=self.submission_form.submission).exclude(pk=self.pk).order_by('published_at')

        return {
            'vote': self,
            'submission': self.get_submission(),
            'form': self.submission_form,
            'documents': self.submission_form.documents.order_by('doctype__name', '-date'),
            'ABSOLUTE_URL_PREFIX': settings.ABSOLUTE_URL_PREFIX,
            'past_votes': past_votes,
        }

reversion.register(Vote, fields=('result', 'text'))


def _post_vote_save(sender, **kwargs):
    vote = kwargs['instance']
    submission_form = vote.submission_form
    if submission_form is None:
        return
    if (vote.published_at and submission_form.current_published_vote_id == vote.pk) or (not vote.published_at and submission_form.current_pending_vote_id == vote.pk):
        return
    if vote.published_at:
        if submission_form.current_pending_vote_id == vote.pk:
            submission_form.current_pending_vote = None
        submission_form.current_published_vote = vote
    else:
        # handle Vote.submission_form changes (happens on b2 upgrades)
        submission_form.submission.forms.filter(current_pending_vote=vote).exclude(pk=submission_form.pk).update(current_pending_vote=None)
        submission_form.current_pending_vote = vote
    submission_form.save(force_update=True)

post_save.connect(_post_vote_save, sender=Vote)
