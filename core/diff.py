# -*- coding: utf-8 -*-
import datetime
import types
import traceback
from ecs.utils.diff_match_patch import diff_match_patch

from django.utils.translation import ugettext as _
from django.utils.datastructures import SortedDict
from django.utils.encoding import force_unicode
from django.db import models
from django.db.models import Manager
from django.http import HttpRequest
from django.contrib.auth.models import User

from ecs.core.models import SubmissionForm, Investigator, EthicsCommission, \
    Measure, NonTestedUsedDrug, ForeignParticipatingCenter, InvestigatorEmployee
from ecs.documents.models import Document
from ecs.utils.viewutils import render_html
from ecs.core import paper_forms
from ecs.utils.countries.models import Country
from ecs.users.utils import get_full_name


DATETIME_FORMAT = '%d.%m.%Y %H:%M'
DATE_FORMAT = '%d.%m.%Y'


def word_diff(a, b):
    dmp = diff_match_patch()
    a, b, wordArray = dmp.diff_wordsToChars(a, b)
    diff = dmp.diff_main(a, b, checklines=False)
    dmp.diff_cleanupSemantic(diff)
    dmp.diff_charsToWords(diff, wordArray)
    return diff

class DiffNode(object):
    def __init__(self, old, new, identity=None, ignore_old=False, ignore_new=False):
        self.old = old
        self.new = new
        self.identity = identity
        self.ignore_old = ignore_old
        self.ignore_new = ignore_new

    def html(self):
        raise NotImplementedError

class TextDiffNode(DiffNode):
    def html(self):
        diff = word_diff(self.old, self.new)
        result = []
        for op, bit in diff:
            if op:
                result.append('<span class="%s">%s</span>' % ('inserted' if op > 0 else 'deleted', bit))
            else:
                result.append(bit)
        return "".join(result)


class AtomicDiffNode(DiffNode):
    def format(self, val):
        return unicode(val)

    def html(self):
        result = []
        if not self.ignore_old:
            result.append('<span class="deleted">- %s</span>' % force_unicode(self.old))
        if not self.ignore_new:
            result.append('<span class="inserted">+ %s</span>' % force_unicode(self.new))
        return '<span class="atomic">%s</span>' % ''.join(result)
        


class ModelDiffNode(DiffNode):
    def __init__(self, old, new, field_diffs, **kwargs):
        super(ModelDiffNode, self).__init__(old, new, **kwargs)
        self.field_diffs = field_diffs
        
    def __nonzero__(self):
        return bool(self.field_diffs)
        
    def __getitem__(self, label):
        return self.field_diffs[label]
    
    def html(self):
        try:
            result = []
            for label, node in self.field_diffs.iteritems():
                result.append('<div class="field">%s: %s</div>' % (label, node.html()))
            result = "\n".join(result)
            if self.identity:
                result = '<span class="title">%s</span>\n%s' % (self.identity, result)
            return result
        except Exception, e:
            traceback.print_exc()


class ListDiffNode(DiffNode):
    css_map = {
        '+': 'inserted',
        '-': 'deleted',
        '~': 'changed',
    }
    
    def __init__(self, old, new, **kwargs):
        super(ListDiffNode, self).__init__(old, new, **kwargs)
        self._prepare()
        
    def _prepare(self):
        diffs = []
        for old, new in zip(self.old, self.new):
            item_diff = diff_model_instances(old, new, ignore_old=self.ignore_old, ignore_new=self.ignore_new)
            if item_diff:
                diffs.append(('~', item_diff))
            
        common_len = min(len(self.old), len(self.new))
        diffs += [('-', diff_model_instances(old, None, ignore_new=True)) for old in self.old[common_len:]]
        diffs += [('+', diff_model_instances(None, new, ignore_old=True)) for new in self.new[common_len:]]
        
        diffs.sort(key=lambda d: d[1].identity)
        self.diffs = diffs
        
    def __nonzero__(self):
        return bool(self.diffs)
    
    def html(self):
        result = []
        for op, diff in self.diffs:
            result.append('<div class="item %s">%s %s</div>' % (self.css_map[op], op, diff.html()))
        return "\n".join(result)


class DocumentListDiffNode(ListDiffNode):
    def _prepare(self):
        self.diffs = []
        old_docs = {}
        for doc in self.old:
            old_docs[doc.uuid] = doc
        added_docs = []
        for doc in self.new:
            if doc.uuid in old_docs:
                del old_docs[doc.uuid]
            else:
                self.diffs.append(('+', diff_model_instances(None, doc, ignore_old=True)))
        for doc in old_docs.values():
            self.diffs.append(('-', diff_model_instances(doc, None, ignore_new=True)))

    def html(self):
        return "\n".join(d.html() for op, d in self.diffs)

def _render_value(val):
    if val is None:
        return _('No Information')
    elif val is True:
        return _('Yes')
    elif val is False:
        return _('No')
    elif isinstance(val, types.IntType):
        return unicode(val)
    elif isinstance(val, datetime.date):
        return val.strftime(DATE_FORMAT)
    elif isinstance(val, datetime.date):
        return val.strftime(DATETIME_FORMAT)
    return unicode(val)


class ModelDiffer(object):
    exclude = ()
    fields = ()
    follow = ()
    identify = None
    label_map = {}

    def __init__(self, model=None, exclude=None, fields=None, follow=None, identify=None, label_map=None, node_map=None):
        if model:
            self.model = model
        if exclude:
            self.exclude = exclude
        if fields:
            self.fields = fields
        if follow:
            self.follow = follow
        if identify:
            self.identify = identify
        if label_map:
            self.label_map = label_map
        self.node_map = node_map or {}

    def get_field_names(self):
        names = paper_forms.get_field_names_for_model(self.model)
        for f in self.model._meta.fields:
            if not f.name in names:
                names.append(f.name)
        if self.fields:
            names = [n for n in names if n in self.fields]
        if self.follow:
            names += self.follow
        if self.exclude:
            names = [n for n in names if not n in self.exclude]
        return names

    def diff_field(self, name, old, new, **kwargs):
        old_val = getattr(old, name, None)
        new_val = getattr(new, name, None)
        
        if old_val == new_val:
            return None
        
        try:
            field = self.model._meta.get_field(name)
        except models.FieldDoesNotExist:
            field = None
        
        if isinstance(field, models.ForeignKey):
            return diff_model_instances(old_val, new_val, model=field.rel.to, **kwargs)
        elif isinstance(new_val, Manager) or isinstance(old_val, Manager):
            old_val = list(old_val.all().order_by('pk')) if old else []
            new_val = list(new_val.all().order_by('pk')) if new else []
            if not old_val and not new_val:
                return None
            return self.node_map.get(name, ListDiffNode)(old_val, new_val, **kwargs)
        elif field is not None and field.choices:
            old_val = unicode(dict(field.choices)[old_val]) if old_val else _('No Information')
            new_val = unicode(dict(field.choices)[new_val]) if new_val else _('No Information')
            return AtomicDiffNode(old_val, new_val, **kwargs)
        elif isinstance(field, (models.CharField, models.TextField)) and old_val and new_val:
            return TextDiffNode(old_val, new_val, **kwargs)
        else:
            return AtomicDiffNode(_render_value(old_val), _render_value(new_val), **kwargs)
            
    def diff(self, old, new, **kwargs):
        d = []
        for name in self.get_field_names():
            field_info = paper_forms.get_field_info(self.model, name, None)

            if field_info is not None:
                label = force_unicode(field_info.label)
                if field_info.number:
                    label = "%s %s" % (field_info.number, label)
            elif name in self.label_map:
                label = self.label_map[name]
            else:
                label = name
            field_diff = self.diff_field(name, old, new, **kwargs)
            if field_diff:
                d.append((label, field_diff))
        identity = None
        if self.identify:
            identity = getattr(new or old, self.identify)
        return ModelDiffNode(old, new, SortedDict(d), identity=identity)


class AtomicModelDiffer(ModelDiffer):
    def format(self, obj):
        return unicode(obj)

    def diff(self, old, new, **kwargs):
        if old == new:
            return
        old = self.format(old) if old is not None else _('No Information')
        new = self.format(new) if new is not None else _('No Information')
        return AtomicDiffNode(old, new, **kwargs)


class DocumentDiffer(AtomicModelDiffer):
    model = Document

    def format(self, doc):
        return render_html(HttpRequest(), 'submissions/diff/document.inc', {'doc': doc})


class CountryDiffer(AtomicModelDiffer):
    model = ForeignParticipatingCenter
    
    def format(self, country):
        return country.printable_name


class UserDiffer(AtomicModelDiffer):
    model = User

    def format(self, user):
        return u'{0} <{1}>'.format(get_full_name(user), user.email)


_differs = {
    SubmissionForm: ModelDiffer(SubmissionForm,
        exclude=('id', 'submission', 'current_for', 'primary_investigator', 'current_for_submission', 
            'pdf_document', 'current_pending_vote', 'current_published_vote', 'is_acknowledged',
            'created_at', 'presenter', 'sponsor', 'submitter', 'is_transient',
            'is_notification_update',),
        follow=('foreignparticipatingcenter_set','investigators','measures','nontesteduseddrug_set',
            'documents', 'substance_registered_in_countries', 'substance_p_c_t_countries'),
        node_map={
            'documents': DocumentListDiffNode,
        },
        label_map=dict([
            ('foreignparticipatingcenter_set', _(u'Auslandszentren')),
            ('investigators', _(u'Zentren')),
            ('measures', _(u'Studienbezogen/Routinemäßig durchzuführende Therapie und Diagnostik')),
            ('nontesteduseddrug_set',
                _(u'Im Rahmen der Studie verabreichte Medikamente, deren Wirksamkeit und/oder Sicherheit nicht Gegenstand der Prüfung sind')),
            ('documents', _(u'Dokumente')),
        ]),
    ),
    Investigator: ModelDiffer(Investigator,
        exclude=('id', 'submission_form',),
        follow=('employees',),
        identify='organisation',
        label_map={
            'employees': _(u'Mitarbeiter'),
        }
    ),
    InvestigatorEmployee: ModelDiffer(InvestigatorEmployee,
        exclude=('id', 'investigator'), 
        identify='full_name',
    ),
    Measure: ModelDiffer(Measure, 
        exclude=('id', 'submission_form'), 
        identify='type',
    ),
    NonTestedUsedDrug: ModelDiffer(NonTestedUsedDrug,
        exclude=('id', 'submission_form'),
        identify='generic_name',
    ),
    ForeignParticipatingCenter: ModelDiffer(ForeignParticipatingCenter,
        exclude=('id', 'submission_form',),
        identify='name',
    ),
    EthicsCommission: AtomicModelDiffer(),
    Country: AtomicModelDiffer(),
    Document: DocumentDiffer(),
    User: UserDiffer(),
}

def diff_model_instances(old, new, model=None, ignore_old=False, ignore_new=False):
    if not model:
        if old:
            model = old.__class__
        elif new:
            model = new.__class__
        else:
            return []
    return _differs[model].diff(old, new, ignore_old=ignore_old, ignore_new=ignore_new)
    

def diff_submission_forms(old_submission_form, new_submission_form):
    assert(old_submission_form.submission == new_submission_form.submission)
    return diff_model_instances(old_submission_form, new_submission_form)
