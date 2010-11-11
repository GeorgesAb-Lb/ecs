from django.utils.translation import ugettext_lazy as _

class Party(object):
    def __init__(self, organization=None, name=None, user=None, email=None, involvement=None):
        self.organization = organization
        self._name = name
        self._email = email
        self.user = user
        self.involvement = involvement
        
    @property
    def email(self):
        if self._email:
            return self._email
        if self.user:
            return self.user.email
        return None
    
    @property
    def name(self):
        if self._name:
            return self._name
        if self.user:
            return unicode(self.user)
        if self._email:
            return self._email
        return "anonymous"
        
def get_involved_parties(sf, include_workflow=True):
    yield Party(organization=sf.sponsor_name, name=sf.sponsor_contact.full_name, user=sf.sponsor, email=sf.sponsor_email, involvement=_("Sponsor"))
    if sf.invoice_name:
        yield Party(organization=sf.invoice_name, name=sf.invoice_contact.full_name, email=sf.invoice_email, involvement=_("Invoice"))
    yield Party(organization=sf.submitter_organisation, name=sf.submitter_contact.full_name, user=sf.submitter, involvement=_("Submitter"))
    # FIXME: yield Party(user=sf.presenter, involvement=_("Presenter")),

    for i in sf.investigators.filter(main=True):
        yield Party(organization=i.organisation, name=i.contact.full_name, user=i.user, email=i.email)

    if include_workflow:
        from ecs.tasks.models import Task
        for task in Task.objects.filter(workflow_token__in=sf.submission.workflow.tokens.filter(consumed_at__isnull=False).values('pk').query).select_related('task_type'):
            yield Party(user=task.assigned_to, involvement=task.task_type.name)


