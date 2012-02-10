# -*- coding: utf-8 -*-
import re
from textwrap import dedent
from django import template
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse

from ecs.core import paper_forms
from ecs.core.models import Submission
from ecs.docstash.models import DocStash
from ecs.utils.browserutils import is_supported_browser as isb
from ecs.help.models import Page

register = template.Library()

def getitem(obj, name):
    try:
        return obj[name]
    except KeyError:
        return None

register.filter('getattr', lambda obj, name: getattr(obj, str(name)))
register.filter('getitem', getitem)
register.filter('type_name', lambda obj: type(obj).__name__)
register.filter('startwith', lambda obj, start: obj.startswith(substr))
register.filter('endswith', lambda obj, end: obj.endswith(end))
register.filter('contains', lambda obj, x: x in obj)
register.filter('not', lambda obj: not obj)
register.filter('multiply', lambda a, b: a * b)
register.filter('euro', lambda val: (u"€ %.2f" % float(val)).replace('.', ','))

@register.filter
def ec_number(submission):
    if submission:
        return submission.get_ec_number_display()
    return None

@register.filter
def repeat(s, n):
    return mark_safe(s*n)
repeat.is_safe = True

@register.filter
def get_field_info(formfield):
    if formfield and hasattr(formfield.form, '_meta'):
        return paper_forms.get_field_info(model=formfield.form._meta.model, name=formfield.name)
    else:
        return None

@register.filter
def id_for_label(field):
    widget = field.field.widget
    id_ = widget.attrs.get('id') or field.auto_id
    return widget.id_for_label(id_)

@register.filter
def form_value(form, fieldname):
    if form.data:
        return form._raw_value(fieldname)
    try:
        return form.initial[fieldname]
    except KeyError:
        return None
        
@register.filter
def simple_timedelta_format(td):
    if not td.seconds:
        return "0"
    minutes, seconds = divmod(td.seconds, 60)
    hours, minutes = divmod(minutes, 60)
    result = []
    if hours:
        result.append("%sh" % hours)
    if minutes:
        result.append("%smin" % minutes)
    if seconds:
        result.append("%ss" % seconds)
    return " ".join(result)
    
@register.filter
def smart_truncate(s, n):
    if not s:
        return u""
    if len(s) <= n:
        return s
    return u"%s …" % re.match(r'(.{,%s})\b' % (n - 2), s).group(0)
    

@register.filter
def class_for_field(field):
    return 'wide' if field.field.max_length > 50 else 'narrow'

@register.filter
def my_submissions_count(user):
    count = Submission.objects.mine(user).count()
    count += len([
        d for d in DocStash.objects.filter(group='ecs.core.views.submissions.create_submission_form', owner=user) if d.current_value
    ])
    return count

@register.filter
def assigned_submissions_count(user):
    return Submission.objects.reviewed_by_user(user).count()

@register.filter
def is_docstash(obj):
    return isinstance(obj, DocStash)

@register.filter
def paper_submission_review(submission, user):
    return submission.paper_submission_review_task_for(user)

@register.filter
def get_field(form, fname):
    return form[fname]

@register.filter
def yes_no_unknown(v):
    if v is True:
        return _('yes')
    elif v is False:
        return _('no')
    else:
        return _('Unknown')

@register.filter
def last_recessed_vote(top):
    if top.submission:
        return top.submission.get_last_recessed_vote(top)
    return None


@register.filter
def allows_amendments_by(sf, user):
    return sf.allows_amendments(user)
    
@register.filter
def allows_edits_by(sf, user):
    return sf.allows_edits(user)

@register.filter
def allows_export_by(sf, user):
    return sf.allows_export(user)

@register.filter
def is_presenting_party(user, sf):
    return user in sf.get_presenting_parties()

@register.filter
def is_supported_browser(request):
    return isb(request.META['HTTP_USER_AGENT'])

@register.tag(name='strip')
def do_strip(parser, token):
    nodelist = parser.parse(('endstrip',))
    parser.delete_first_token()
    return StripNode(nodelist)

class StripNode(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        return self.nodelist.render(context).strip()

@register.tag(name='dedent')
def do_dedent(parser, token):
    nodelist = parser.parse(('enddedent',))
    parser.delete_first_token()
    return DedentNode(nodelist)

class DedentNode(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        return dedent(self.nodelist.render(context))

@register.filter
def help_url(slug):
    try:
        page = Page.objects.get(slug=slug)
        return reverse('ecs.help.views.view_help_page', kwargs={'page_pk': page.pk})
    except Page.DoesNotExist:
        return reverse('ecs.help.views.index')
